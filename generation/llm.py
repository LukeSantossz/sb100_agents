"""Geração de respostas multi-turno com LLM."""

import ollama

from core.config import settings
from core.schemas import ExpertiseLevel, UserProfile

SYSTEM_PROMPTS = {
    ExpertiseLevel.beginner: """Você é um assistente especializado em agronomia e agricultura.
Responda de forma clara e didática, usando linguagem simples e acessível.
Evite termos técnicos; quando necessário, explique-os de forma fácil de entender.
Use exemplos práticos do dia a dia para ilustrar conceitos.
Se o contexto não contiver informação suficiente, indique isso ao usuário.""",
    ExpertiseLevel.intermediate: """Você é um assistente especializado em agronomia e agricultura.
Responda de forma clara e objetiva, usando termos técnicos com explicações breves quando necessário.
Assuma que o usuário tem conhecimento básico de práticas agrícolas.
Forneça detalhes técnicos relevantes sem ser excessivamente simplista.
Se o contexto não contiver informação suficiente, indique isso ao usuário.""",
    ExpertiseLevel.expert: """Você é um assistente especializado em agronomia e agricultura.
Responda com precisão técnica e terminologia avançada.
Assuma que o usuário é um profissional com conhecimento aprofundado do domínio.
Inclua dados quantitativos, referências a pesquisas e detalhes técnicos quando disponíveis.
Se o contexto não contiver informação suficiente, indique isso ao usuário.""",
}


def build_system_prompt(profile: UserProfile) -> str:
    """Retorna o system prompt adequado ao nível de expertise do usuário."""
    return SYSTEM_PROMPTS.get(profile.expertise, SYSTEM_PROMPTS[ExpertiseLevel.intermediate])


def generate(
    question: str,
    context: str,
    history: list[dict[str, str]],
    profile: UserProfile,
) -> str:
    """Gera resposta do LLM considerando contexto RAG, histórico e perfil do usuário.

    Args:
        question: Pergunta atual do usuário.
        context: Texto de contexto recuperado via RAG (chunks concatenados).
        history: Lista de mensagens anteriores no formato [{"role": "user"|"assistant", "content": "..."}].
        profile: Perfil do usuário com nome e nível de expertise.

    Returns:
        Texto da resposta gerada pelo LLM.
    """
    messages: list[dict[str, str]] = []

    # System prompt baseado no perfil
    messages.append({"role": "system", "content": build_system_prompt(profile)})

    # Histórico de conversa
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Pergunta atual com contexto RAG injetado
    user_content = (
        f"Contexto:\n{context}\n\nPergunta: {question}" if context else f"Pergunta: {question}"
    )
    messages.append({"role": "user", "content": user_content})

    response = ollama.chat(model=settings.chat_model, messages=messages)

    return str(response["message"]["content"])
