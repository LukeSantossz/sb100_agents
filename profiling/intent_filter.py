"""Intent filter for agricultural domain classification."""


def is_agricultural_intent(question: str) -> bool:
    """
    Check if the question is within the agricultural domain.

    Args:
        question: The user's question.

    Returns:
        True if the question is agricultural, False otherwise.

    Note:
        This is a placeholder implementation. The full implementation
        should use an LLM or classifier to determine domain relevance.
    """
    # Placeholder: always returns True for MVP
    # TODO: Implement domain classification (T-xxx)
    return True
