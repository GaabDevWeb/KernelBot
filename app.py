import os
import re
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import httpx

# ---------------------------------------------------------------------------
# Logging — formato com separador visual para facilitar leitura no terminal
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("acl")

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY ausente no .env — impossível iniciar.")

CONTENT_DIR = Path(__file__).parent / "content"
CONTENT_DIR.mkdir(exist_ok=True)

BM25_SCORE_THRESHOLD = 0.7
OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "arcee-ai/trinity-large-preview:free",
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

SYSTEM_PROMPT_GERAL = (
    "Você é o ACL (Agente de Contexto Local), um assistente técnico direto e preciso. "
    "Responda em português (PT-BR). Evite enrolação."
)

OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "ACL - Agente de Contexto Local",
}

# ---------------------------------------------------------------------------
# Índice BM25 — singleton em memória
# ---------------------------------------------------------------------------
class BM25Index:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.chunks: list[dict] = []
        self.bm25: BM25Okapi | None = None
        self.rebuild()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    @staticmethod
    def _chunk_markdown(path: Path) -> list[dict]:
        """Divide arquivo .md em chunks por headers (H1/H2/H3)."""
        text = path.read_text(encoding="utf-8", errors="replace")
        sections: list[dict] = []
        current_header = path.stem
        current_lines: list[str] = []

        for line in text.splitlines():
            if re.match(r"^#{1,3}\s", line):
                if current_lines:
                    sections.append({
                        "text": f"{current_header}\n" + "\n".join(current_lines).strip(),
                        "source": path.name,
                    })
                current_header = line.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append({
                "text": f"{current_header}\n" + "\n".join(current_lines).strip(),
                "source": path.name,
            })

        return [s for s in sections if s["text"].strip()]

    def rebuild(self) -> None:
        t0 = time.perf_counter()
        md_files = sorted(CONTENT_DIR.glob("*.md"))

        if not md_files:
            logger.warning("⚠  Pasta /content está vazia — BM25 desativado. Modo assistente geral ativo.")
            with self._lock:
                self.chunks = []
                self.bm25 = None
            return

        logger.info(f"🔄 Iniciando rebuild do índice BM25 — {len(md_files)} arquivo(s) encontrado(s)...")
        all_chunks: list[dict] = []

        for md_file in md_files:
            try:
                before = len(all_chunks)
                all_chunks.extend(self._chunk_markdown(md_file))
                added = len(all_chunks) - before
                logger.info(f"   📄 {md_file.name} → {added} chunk(s) extraído(s)")
            except Exception:
                logger.exception(f"   ❌ Falha ao processar {md_file.name} — arquivo ignorado")

        with self._lock:
            self.chunks = all_chunks
            tokenized = [self._tokenize(c["text"]) for c in all_chunks]
            self.bm25 = BM25Okapi(tokenized)

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"✅ Índice BM25 pronto — {len(all_chunks)} chunk(s) total | "
            f"{len(md_files)} arquivo(s) | rebuild em {elapsed:.1f}ms"
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        with self._lock:
            if not self.bm25 or not self.chunks:
                return []
            tokens = self._tokenize(query)
            scores = self.bm25.get_scores(tokens)
            max_score = float(scores.max()) if len(scores) else 0.0
            if max_score == 0:
                return []
            norm = scores / max_score
            ranked = sorted(enumerate(norm), key=lambda x: x[1], reverse=True)
            return [
                {**self.chunks[i], "score": float(s)}
                for i, s in ranked[:top_k]
                if s >= BM25_SCORE_THRESHOLD
            ]


bm25_index = BM25Index()


# ---------------------------------------------------------------------------
# Watchdog — monitora /content em background
# ---------------------------------------------------------------------------
class ContentWatcher(FileSystemEventHandler):
    def __init__(self, index: BM25Index) -> None:
        super().__init__()
        self._index = index
        self._timer: threading.Timer | None = None

    def _debounced_rebuild(self) -> None:
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
            logger.debug("   ↩  Rebuild anterior cancelado (debounce)")
        self._timer = threading.Timer(1.5, self._index.rebuild)
        self._timer.start()

    def on_modified(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            logger.info(f"👁  Watchdog: modificação em '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()

    def on_created(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            logger.info(f"👁  Watchdog: novo arquivo detectado '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()

    def on_deleted(self, event) -> None:
        if not event.is_directory and str(event.src_path).endswith(".md"):
            filename = Path(event.src_path).name
            logger.info(f"👁  Watchdog: arquivo removido '{filename}' — rebuild agendado em 1.5s")
            self._debounced_rebuild()


observer = Observer()
observer.schedule(ContentWatcher(bm25_index), str(CONTENT_DIR), recursive=False)
observer.start()
logger.info(f"👁  Watchdog ativo — monitorando: {CONTENT_DIR}")


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 ACL iniciado e pronto para receber requisições.")
    yield
    observer.stop()
    observer.join()
    logger.info("🛑 Watchdog encerrado. Servidor finalizado.")

app = FastAPI(title="ACL — Agente de Contexto Local", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    client_ip = request.client.host if request.client else "desconhecido"
    logger.info(f"🌐 Interface carregada — cliente: {client_ip}")
    return templates.TemplateResponse(request=request, name="index.html")


# ---------------------------------------------------------------------------
# Roteamento de contexto
# ---------------------------------------------------------------------------
def _build_messages(user_message: str) -> list[dict]:
    force_rag = user_message.startswith("/content")
    query = user_message.removeprefix("/content").strip() if force_rag else user_message

    logger.info(f"💬 Mensagem recebida [{len(user_message)} chars] | force_rag={force_rag} | query='{query[:80]}{'...' if len(query) > 80 else ''}'")

    hits = bm25_index.search(query)

    if force_rag or hits:
        if hits:
            for h in hits:
                logger.info(f"   🎯 BM25 hit → '{h['source']}' | score={h['score']:.3f} | chunk='{h['text'][:60].strip()}...'")
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {h['source']} | Score: {h['score']:.2f}]\n{h['text']}"
                for h in hits
            )
            ctx_chars = sum(len(h["text"]) for h in hits)
            logger.info(f"   📦 Contexto RAG montado: {len(hits)} chunk(s) | ~{ctx_chars} chars injetados no system prompt")
        else:
            logger.info("   ⚡ /content forçado mas BM25 sem hits — injetando top-5 chunks do índice")
            ctx = "\n\n---\n\n".join(
                f"[Fonte: {c['source']}]\n{c['text']}"
                for c in bm25_index.chunks[:5]
            )

        system_content = (
            f"{SYSTEM_PROMPT_GERAL}\n\n"
            "Você possui acesso à seguinte base de conhecimento local. "
            "Use-a como referência primária para responder:\n\n"
            f"{ctx}"
        )
        logger.info(f"   🔑 Modo: RAG | system prompt total ~{len(system_content)} chars")
    else:
        system_content = SYSTEM_PROMPT_GERAL
        logger.info("   🤖 Modo: assistente geral (nenhum chunk BM25 ≥ threshold)")

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query},
    ]


# ---------------------------------------------------------------------------
# Streaming SSE via httpx — com fallback entre modelos
# ---------------------------------------------------------------------------
async def _stream_response(messages: list[dict]) -> AsyncGenerator[str, None]:
    payload_base = {
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt, model in enumerate(MODELS, start=1):
            try:
                logger.info(f"🤖 Tentativa {attempt}/{len(MODELS)} — modelo: {model}")
                t_start = time.perf_counter()
                token_count = 0

                async with client.stream(
                    "POST",
                    OPENROUTER_BASE,
                    headers=OPENROUTER_HEADERS,
                    json={**payload_base, "model": model},
                ) as response:

                    if response.status_code == 429:
                        logger.warning(f"   ⏳ Rate limit (429) em '{model}' — acionando fallback...")
                        continue

                    if response.status_code >= 400:
                        body = await response.aread()
                        logger.error(
                            f"   ❌ HTTP {response.status_code} em '{model}' — "
                            f"resposta: {body[:300].decode('utf-8', errors='replace')}"
                        )
                        continue

                    logger.info(f"   ✅ Conexão estabelecida com '{model}' — iniciando stream...")

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw.strip() == "[DONE]":
                            elapsed = (time.perf_counter() - t_start) * 1000
                            logger.info(
                                f"   🏁 Stream finalizado — modelo: '{model}' | "
                                f"{token_count} token(s) | {elapsed:.0f}ms"
                            )
                            yield "data: [DONE]\n\n"
                            return

                        try:
                            chunk = json.loads(raw)
                            token: str = chunk["choices"][0].get("delta", {}).get("content") or ""
                            if token:
                                token_count += 1
                                safe = token.replace("\n", "\\n")
                                yield f"data: {safe}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

                    elapsed = (time.perf_counter() - t_start) * 1000
                    logger.info(
                        f"   🏁 Stream finalizado (EOF) — modelo: '{model}' | "
                        f"{token_count} token(s) | {elapsed:.0f}ms"
                    )
                    yield "data: [DONE]\n\n"
                    return

            except httpx.TimeoutException:
                logger.warning(f"   ⏰ Timeout (60s) em '{model}' — acionando próximo fallback...")
                continue
            except Exception as e:
                logger.exception(f"   💥 Erro inesperado em '{model}': {type(e).__name__}: {e}")
                continue

    msg = "Todos os modelos de fallback falharam. Tente novamente mais tarde."
    logger.error(f"🚨 {msg} | Modelos tentados: {', '.join(MODELS)}")
    yield f"data: [ERROR] {msg}\n\n"


@app.post("/chat")
async def chat(request: Request) -> StreamingResponse:
    client_ip = request.client.host if request.client else "desconhecido"

    try:
        data = await request.json()
    except Exception:
        logger.warning(f"⚠  Requisição inválida de {client_ip} — corpo não é JSON válido")
        raise HTTPException(status_code=400, detail="JSON inválido no corpo da requisição.")

    user_message: str = (data.get("message") or "").strip()
    if not user_message:
        logger.warning(f"⚠  Requisição de {client_ip} com campo 'message' ausente ou vazio")
        raise HTTPException(status_code=400, detail="Campo 'message' ausente ou vazio.")

    messages = _build_messages(user_message)

    return StreamingResponse(
        _stream_response(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 60)
    logger.info("  ACL — Agente de Contexto Local")
    logger.info(f"  Content dir : {CONTENT_DIR}")
    logger.info(f"  BM25 threshold: {BM25_SCORE_THRESHOLD}")
    logger.info(f"  Modelos ({len(MODELS)}): {', '.join(MODELS)}")
    logger.info("=" * 60)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)