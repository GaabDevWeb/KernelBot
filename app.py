import os
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    logger.error("Váriavel de ambiente OPENROUTER_API_KEY não encontrada no arquivo .env")
    raise ValueError("Missing OPENROUTER_API_KEY")

app = FastAPI(title="ChatBot API", description="API de Alta Performance para Chat")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/chat")
async def chat(data: dict) -> Dict[str, Any]:
    user_message = data.get("message")
    
    if not user_message or not isinstance(user_message, str):
        logger.warning(f"Tentativa de envio de mensagem inválida: {user_message}")
        raise HTTPException(status_code=400, detail="Mensagem vazia ou em formato inválido")

    try:
        async with httpx.AsyncClient() as client:
            modelos_disponiveis = [
                "arcee-ai/trinity-large-preview:free",
                "google/gemini-2.5-flash:free",
                "meta-llama/llama-3.3-70b-instruct:free"
            ]
            
            for modelo in modelos_disponiveis:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "ChatBotTest"
                    },
                    json={
                        "model": modelo,
                        "messages": [
                            {"role": "system", "content": "Você é um assistente direto e útil."},
                            {"role": "user", "content": user_message}
                        ]
                    },
                    timeout=15.0
                )
                
                if response.status_code == 429:
                    logger.warning(f"Provedor rate-limited (429) no modelo {modelo}. Acionando fallback...")
                    continue
                
                response.raise_for_status()
                
                result = response.json()
                reply = result["choices"][0]["message"]["content"]
                
                logger.info(f"Requisição resolvida com sucesso usando o modelo: {modelo}")
                return {"reply": reply}

            logger.error("Todos os provedores de fallback da camada gratuita falharam por Rate Limit.")
            raise HTTPException(status_code=503, detail="Cota gratuita esgotada globalmente no OpenRouter. Tente novamente mais tarde.")

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro na API OpenRouter [Status {e.response.status_code}]: {e.response.text}")
        raise HTTPException(status_code=502, detail="Falha na comunicação com o provedor de IA")
    except Exception as e:
        logger.exception("Erro interno inesperado durante o processamento da mensagem.")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando servidor de desenvolvimento Uvicorn...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)