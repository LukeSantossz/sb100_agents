"""Schemas Pydantic do contrato público da API (request/response compartilhados)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ExpertiseLevel(StrEnum):
    """Nível de familiaridade do usuário com o domínio agrícola.
    Valores: ``beginner`` (iniciante), ``intermediate`` (intermediário), ``expert`` (avançado).
    """

    beginner = "beginner"
    intermediate = "intermediate"
    expert = "expert"


class UserProfile(BaseModel):
    """Perfil do usuário utilizado para contextualizar respostas."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Hilário Silva",
                    "expertise": "intermediate",
                }
            ]
        }
    )

    name: str = Field(..., description="Nome de exibição ou identificação do usuário.")
    expertise: ExpertiseLevel = Field(
        ...,
        description="Grau de experiência do usuário no domínio (beginner, intermediate ou expert).",
    )


class ChatRequest(BaseModel):
    """Requisição de mensagem em uma sessão de chat."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "question": "Qual é a época ideal de plantio da soja na região Centro-Oeste?",
                    "profile": {
                        "name": "Hilário Silva",
                        "expertise": "intermediate",
                    },
                }
            ]
        }
    )

    session_id: str = Field(..., description="Identificador da sessão de conversa.")
    question: str = Field(..., description="Texto da pergunta enviada pelo usuário.")
    profile: UserProfile = Field(
        ...,
        description="Perfil associado ao usuário para ajuste de tom e profundidade da resposta.",
    )


class ChatResponse(BaseModel):
    """Resposta do assistente após processar a pergunta."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": "Com base na documentação indexada, a janela de plantio recomendada é...",
                    "hallucination_score": 0.18,
                }
            ]
        }
    )

    answer: str = Field(..., description="Conteúdo textual da resposta ao usuário.")
    hallucination_score: float = Field(
        ...,
        description="Métrica numérica associada ao risco estimado de alucinação na resposta.",
    )
