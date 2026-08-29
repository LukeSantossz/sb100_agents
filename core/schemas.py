"""Pydantic schemas for the public API contract (shared request/response)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpertiseLevel(StrEnum):
    """User's familiarity level with the agricultural domain.
    Values: ``beginner``, ``intermediate``, ``expert``.
    """

    beginner = "beginner"
    intermediate = "intermediate"
    expert = "expert"


class UserProfile(BaseModel):
    """User profile used to contextualize answers."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "John Silva",
                    "expertise": "intermediate",
                }
            ]
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User display name or identifier (1 to 255 characters).",
    )
    expertise: ExpertiseLevel = Field(
        ...,
        description="User's experience level in the domain (beginner, intermediate or expert).",
    )


class ChatRequest(BaseModel):
    """Message request within a chat session."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "question": "What is the ideal soybean planting window in the Midwest region?",
                    "profile": {
                        "name": "John Silva",
                        "expertise": "intermediate",
                    },
                }
            ]
        }
    )

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Conversation session identifier (1 to 255 characters).",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Text of the question sent by the user (1 to 2000 characters).",
    )
    profile: UserProfile = Field(
        ...,
        description="User profile used to adjust the answer's tone and depth.",
    )

    @field_validator("question")
    @classmethod
    def _strip_and_require_content(cls, value: str) -> str:
        """Reject a whitespace-only question here, before the pipeline is spent.

        ``min_length=1`` counts characters and pydantic does not strip, so ``"   "``
        used to pass validation, run embedding, search and generation, and only then
        fail with a 500 when the conversation buffer refused to store it (#95).
        Rejecting at the boundary that already claims the field is non-empty turns
        that into a 422 before anything is embedded.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must contain more than whitespace")
        return stripped


class ChatResponse(BaseModel):
    """Assistant answer after processing the question."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": "Based on the indexed documentation, the recommended window is...",
                    "hallucination_score": 0.18,
                }
            ]
        }
    )

    answer: str = Field(..., description="Text content of the answer to the user.")
    hallucination_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated hallucination risk (0.0 grounded — 1.0 likely hallucinated).",
    )
