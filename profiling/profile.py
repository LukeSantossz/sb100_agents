"""Profile-based response adaptation."""

from core.schemas import ExpertiseLevel


def adapt_response_for_profile(
    response: str,
    expertise: ExpertiseLevel,
) -> str:
    """
    Adapt a response based on the user's expertise level.

    Args:
        response: The raw LLM response.
        expertise: The user's expertise level.

    Returns:
        The adapted response.

    Note:
        This is a placeholder implementation. Currently, adaptation
        is done at the prompt level in generation/llm.py.
    """
    # Placeholder: returns response unchanged
    # Adaptation is currently handled at prompt generation time
    return response
