"""Group Profile dinâmico e Memória Social do Grupo.

Responsável por:
- Extrair e manter o perfil cultural/social do grupo (estilo de comunicação, tópicos, dúvidas frequentes).
- Registrar a evolução temporal da percepção dos alunos (ex.: períodos 2026-08 vs 2026-09).
- Garantir a barreira ética: Opinião da turma ≠ Fato oficial.
- Execução em background/batch para não onerar o tempo de resposta do usuário.
- Degradação suave: se falhar, o bot continua respondendo normalmente.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("kernelbots.memory.group_profile")

# Tópicos comuns monitorados
_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "Python": ("python", "def", "lambda", "list comprehension", "pandas", "numpy", "django", "flask"),
    "Banco de Dados": ("sql", "banco", "database", "mysql", "postgres", "join", "query", "tabela", "select"),
    "Estrutura de Dados": ("árvore", "arvore", "grafo", "lista ligada", "pilha", "fila", "recursividade"),
    "Java / C#": ("java", "c#", "csharp", "spring", ".net", "dotnet", "orientação a objetos", "classe"),
    "Provas e Avaliações": ("prova", "avaliação", "avaliacao", "nota", "gabarito", "at", "tp", "exame"),
    "Trabalhos e Projetos": ("trabalho", "projeto", "entrega", "deadline", "grupo", "dupla"),
}

_QUESTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "Datas de avaliações": ("quando é a prova", "data da prova", "dia da prova", "quando entrega", "prazo"),
    "Conteúdo das provas": ("cai na prova", "conteúdo da prova", "conteudo da prova", "o que vai cair"),
    "Critérios de avaliação": ("como vai ser avaliado", "vale ponto", "quanto vale"),
    "Material de estudo": ("onde está o slide", "tem pdf", "link da aula", "gravação da aula"),
}

_SENTIMENT_POSITIVE_WORDS = (
    "bom", "ótimo", "otimo", "excelente", "manda bem", "explica bem", "gostei",
    "ajudou", "didático", "didatico", "gente boa", "tranquilo", "fera", "top"
)
_SENTIMENT_NEGATIVE_WORDS = (
    "ruim", "péssimo", "pessimo", "difícil", "dificil", "complicado", "pesado",
    "não explica", "nao explica", "confuso", "chato", "puxado", "tenso", "fumo"
)


@dataclass
class SocialPerception:
    sentiment: str  # "positive" | "negative" | "mixed" | "neutral"
    confidence: float
    evidence_count: int
    themes: list[str] = field(default_factory=list)


@dataclass
class SentimentPeriod:
    period: str  # "YYYY-MM"
    target: str  # ex: "Professor X"
    sentiment: str
    confidence: float
    evidence_count: int


@dataclass
class GroupProfile:
    platform: str
    channel_id: str
    updated_at: str
    communication_style: str = "informal"
    common_topics: list[str] = field(default_factory=list)
    recurring_questions: list[str] = field(default_factory=list)
    social_context: dict[str, dict[str, Any]] = field(default_factory=dict)
    sentiment_history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def group_id(self) -> str:
        return f"{self.platform}:{self.channel_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroupProfile:
        return cls(
            platform=str(data.get("platform") or "whatsapp"),
            channel_id=str(data.get("channel_id") or ""),
            updated_at=str(data.get("updated_at") or ""),
            communication_style=str(data.get("communication_style") or "informal"),
            common_topics=list(data.get("common_topics") or []),
            recurring_questions=list(data.get("recurring_questions") or []),
            social_context=dict(data.get("social_context") or {}),
            sentiment_history=list(data.get("sentiment_history") or []),
        )

    def prompt_block(self) -> str:
        """Formata o bloco de contexto para o Context Builder com barreira ética."""
        if not self.common_topics and not self.social_context and not self.recurring_questions:
            return ""

        parts = ["## Contexto social e dinâmico da turma (Group Profile)"]

        if self.communication_style:
            parts.append(f"- Estilo de comunicação observado no grupo: {self.communication_style}")

        if self.common_topics:
            parts.append(f"- Tópicos mais discutidos: {', '.join(self.common_topics)}")

        if self.recurring_questions:
            parts.append(f"- Dúvidas e preocupações recorrentes: {', '.join(self.recurring_questions)}")

        if self.social_context:
            parts.append("- Percepções sociais observadas no grupo:")
            for target, data in self.social_context.items():
                sent = data.get("sentiment", "neutral")
                conf = float(data.get("confidence", 0.5))
                ev = int(data.get("evidence_count", 0))
                themes = data.get("themes") or []
                themes_str = f" (aspectos: {', '.join(themes)})" if themes else ""

                if sent == "positive":
                    sent_pt = "predominantemente positiva"
                elif sent == "negative":
                    sent_pt = "predominantemente desafiadora/negativa"
                elif sent == "mixed":
                    sent_pt = "mista com divergências"
                else:
                    sent_pt = "neutra"

                parts.append(
                    f"  * {target}: percepção {sent_pt} [confiança: {conf:.2f}, {ev} mensagens]{themes_str}"
                )

        parts.append(
            "\nIMPORTANTE — HIERARQUIA DE VERDADE:\n"
            "As informações acima representam exclusivamente a percepção social e opiniões "
            "dos membros da turma. Elas NÃO são fatos institucionais nem verdades objetivas. "
            "Nunca afirme opiniões de alunos sobre professores ou matérias como fato consumado "
            "e jamais contradiga fontes oficiais com base em percepções do grupo."
        )

        return "\n".join(parts)


class GroupProfileAnalyzer:
    """Extrai padrões e gera o Group Profile a partir de mensagens históricas."""

    @staticmethod
    def extract_profile(
        platform: str,
        channel_id: str,
        messages: list[Any],  # list of GroupMessage or dict
        existing_profile: GroupProfile | None = None,
    ) -> GroupProfile:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        if not messages:
            return existing_profile or GroupProfile(
                platform=platform,
                channel_id=channel_id,
                updated_at=now_iso,
            )

        topic_counts: dict[str, int] = {}
        question_counts: dict[str, int] = {}
        target_sentiments: dict[str, dict[str, int]] = {}
        target_themes: dict[str, set[str]] = {}
        period_data: dict[str, dict[str, dict[str, int]]] = {}

        total_msgs = len(messages)
        informal_markers = 0

        for msg in messages:
            text = (getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "") or "").lower()
            ts_str = getattr(msg, "timestamp", None) or (msg.get("timestamp") if isinstance(msg, dict) else "") or ""
            period = ts_str[:7] if len(ts_str) >= 7 else "current"

            if any(w in text for w in ("kkk", "haha", "mano", "cara", "vc", "vcs", "oq", "pra", "blz", "valeu")):
                informal_markers += 1

            for topic, keywords in _TOPIC_PATTERNS.items():
                if any(kw in text for kw in keywords):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1

            for q_cat, keywords in _QUESTION_PATTERNS.items():
                if any(kw in text for kw in keywords):
                    question_counts[q_cat] = question_counts.get(q_cat, 0) + 1

            # Análise de sentimento simples e determinística
            pos = sum(1 for w in _SENTIMENT_POSITIVE_WORDS if w in text)
            neg = sum(1 for w in _SENTIMENT_NEGATIVE_WORDS if w in text)

            # Heurística para identificar menções a professores/disciplinas
            m_prof = re.findall(r"\bprof(?:essor|a)?\s+([A-Za-zÀ-ÿ]+)", text, re.IGNORECASE)
            for prof_name in m_prof:
                target = f"Professor {prof_name.title()}"
                if target not in target_sentiments:
                    target_sentiments[target] = {"pos": 0, "neg": 0, "total": 0}
                    target_themes[target] = set()
                target_sentiments[target]["total"] += 1
                if pos > neg:
                    target_sentiments[target]["pos"] += 1
                elif neg > pos:
                    target_sentiments[target]["neg"] += 1

                if "prova" in text:
                    target_themes[target].add("provas")
                if "trabalho" in text:
                    target_themes[target].add("trabalhos")
                if "explica" in text:
                    target_themes[target].add("didática")

                # Agrupamento temporal
                if period not in period_data:
                    period_data[period] = {}
                if target not in period_data[period]:
                    period_data[period][target] = {"pos": 0, "neg": 0, "total": 0}
                period_data[period][target]["total"] += 1
                if pos > neg:
                    period_data[period][target]["pos"] += 1
                elif neg > pos:
                    period_data[period][target]["neg"] += 1

        # Estilo de comunicação
        style = "informal" if (informal_markers / max(1, total_msgs)) > 0.15 else "equilibrado"

        # Principais tópicos (top 4 com pelo menos 2 ocorrências)
        sorted_topics = [t for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True) if c >= 2]
        common_topics = sorted_topics[:4] if sorted_topics else ["Geral"]

        # Principais dúvidas (top 3)
        sorted_questions = [q for q, c in sorted(question_counts.items(), key=lambda x: x[1], reverse=True) if c >= 1]
        recurring_questions = sorted_questions[:3]

        # Contexto social consolidado
        social_context: dict[str, dict[str, Any]] = {}
        for target, counts in target_sentiments.items():
            tot = counts["total"]
            if tot < 2:
                continue
            pos_c = counts["pos"]
            neg_c = counts["neg"]
            if pos_c > neg_c * 1.5:
                sent = "positive"
                conf = min(0.95, 0.5 + (pos_c / tot) * 0.45)
            elif neg_c > pos_c * 1.5:
                sent = "negative"
                conf = min(0.95, 0.5 + (neg_c / tot) * 0.45)
            elif pos_c > 0 and neg_c > 0:
                sent = "mixed"
                conf = 0.65
            else:
                sent = "neutral"
                conf = 0.5

            social_context[target] = {
                "sentiment": sent,
                "confidence": round(conf, 2),
                "evidence_count": tot,
                "themes": sorted(target_themes.get(target, set())),
            }

        # Histórico temporal de sentimento
        sentiment_history: list[dict[str, Any]] = []
        for per in sorted(period_data.keys()):
            for target, counts in period_data[per].items():
                tot = counts["total"]
                if tot < 2:
                    continue
                pos_c = counts["pos"]
                neg_c = counts["neg"]
                sent = "positive" if pos_c > neg_c else ("negative" if neg_c > pos_c else "neutral")
                conf = min(0.95, 0.5 + (max(pos_c, neg_c) / tot) * 0.4)
                sentiment_history.append(
                    {
                        "period": per,
                        "target": target,
                        "sentiment": sent,
                        "confidence": round(conf, 2),
                        "evidence_count": tot,
                    }
                )

        return GroupProfile(
            platform=platform,
            channel_id=channel_id,
            updated_at=now_iso,
            communication_style=style,
            common_topics=common_topics,
            recurring_questions=recurring_questions,
            social_context=social_context,
            sentiment_history=sentiment_history,
        )
