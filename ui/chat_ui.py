"""Gradio chat interface for the SmartB100 agent.

Interactive web interface that consumes the FastAPI POST /chat
endpoint, supporting:

- Natural-language questions.
- User profile configuration (name and expertise).
- hallucination_score display per answer (colors aligned with
  ``settings.hallucination_threshold``).
- Session management with reset option.
- Loading state via generator pattern (placeholder in <1s).
- Automatic retry with backoff for transient failures (503/504/timeout).
- API URLs and technical details are logged internally; the user only
  sees friendly messages.

Usage:
    python ui/chat_ui.py [--api-url URL] [--port PORT]

    Example:
        python ui/chat_ui.py --api-url http://localhost:8000 --port 7860
"""

import argparse
import html
import logging
import sys
import time
import uuid
from collections.abc import Generator
from pathlib import Path

import gradio as gr
import httpx

# Allows importing core.config when ui/ runs standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PORT = 7860

# Transient retry: 2 retries (3 attempts total) with 1s, 2s backoff
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_BASE = 1.0  # seconds; multiplied by 2**attempt


class ChatSession:
    """Manages chat session state."""

    def __init__(self, api_url: str) -> None:
        """Initializes the chat session.

        Args:
            api_url: Base URL of the SmartB100 API.
        """
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        # settings.chat_timeout: configurable via env CHAT_TIMEOUT (default 600s)
        self.client = httpx.Client(timeout=settings.chat_timeout)

    def reset(self) -> str:
        """Resets the session by generating a new session_id.

        Returns:
            The new session_id.
        """
        self.session_id = str(uuid.uuid4())
        return self.session_id

    def send_message(
        self,
        message: str,
        name: str,
        expertise: str,
    ) -> tuple[str, float]:
        """Sends a message to the API and returns the answer.

        Args:
            message: The user's question.
            name: User name for the profile.
            expertise: Expertise level (beginner, intermediate, expert).

        Returns:
            Tuple of (answer, hallucination_score).

        Raises:
            httpx.HTTPStatusError: If the API returns an HTTP error.
            httpx.RequestError: If a connection error occurs.
        """
        payload = {
            "session_id": self.session_id,
            "question": message,
            "profile": {
                "name": name,
                "expertise": expertise,
            },
        }

        response = self.client.post(
            f"{self.api_url}/chat",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        return data["answer"], data["hallucination_score"]


def _is_transient_error(exc: Exception) -> bool:
    """Identifies transient failures eligible for retry.

    Retry applies to:
    - ``httpx.TimeoutException``: total request timeout.
    - ``httpx.HTTPStatusError`` with status 503/504: backend unavailable or
      gateway timeout (typical of slow Ollama or Qdrant in recovery).
    """
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (503, 504)
    return False


def send_with_retry(
    session: ChatSession,
    message: str,
    name: str,
    expertise: str,
    attempts: int = RETRY_ATTEMPTS,
) -> tuple[str, float]:
    """Sends a message with exponential retry for transient errors.

    Args:
        session: Active chat session.
        message: The user's question.
        name: User name.
        expertise: User expertise.
        attempts: Number of additional retries (total = 1 + attempts).

    Returns:
        Tuple of (answer, hallucination_score).

    Raises:
        httpx.HTTPStatusError | httpx.RequestError: If all attempts fail
        or the error is not transient.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return session.send_message(message, name, expertise)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_exc = exc
            if attempt >= attempts or not _is_transient_error(exc):
                raise
            backoff = RETRY_BACKOFF_BASE * (2**attempt)
            logger.warning(
                "chat.retry attempt=%d/%d backoff=%.1fs reason=%s",
                attempt + 1,
                attempts,
                backoff,
                type(exc).__name__,
            )
            time.sleep(backoff)

    # Defensive — the loop always returns or raises; this path is unreachable.
    assert last_exc is not None
    raise last_exc


def _classify_score(score: float, threshold: float) -> tuple[str, str]:
    """Maps a numeric score to a risk band and display color.

    Bands derive from ``threshold`` (default 0.5) so future changes to
    ``HALLUCINATION_THRESHOLD`` shift all bands consistently:

    - **Green** (low): score < threshold x 0.6.
    - **Yellow** (moderate): threshold x 0.6 ≤ score < threshold x 1.2.
    - **Red** (high): score ≥ threshold x 1.2.

    With the default threshold=0.5: green <0.3, yellow 0.3-0.6, red ≥0.6.

    Args:
        score: hallucination_score (0.0-1.0).
        threshold: Base threshold configured in Settings.

    Returns:
        Tuple of (descriptive text, CSS hex color).
    """
    low_band = threshold * 0.6
    high_band = threshold * 1.2

    if score < low_band:
        return (
            f"Score {score:.2f} — Low risk of hallucination. Reliable answer.",
            "#22c55e",
        )
    if score < high_band:
        return (
            f"Score {score:.2f} — Moderate risk. Validate critical points.",
            "#eab308",
        )
    return (
        f"Score {score:.2f} — High risk of hallucination. Human verification recommended.",
        "#ef4444",
    )


def _score_html(score: float, threshold: float) -> str:
    """Renders the colored HTML badge for the score."""
    text, color = _classify_score(score, threshold)
    # `text` is generated internally (no external input), but we escape it as
    # defense in depth: if the content ever includes dynamic data, the escape
    # is already in place.
    return (
        f'<div style="padding: 8px 12px; border-radius: 6px; '
        f"background: {color}1a; border-left: 4px solid {color}; "
        f'color: {color}; font-weight: 500;">{html.escape(text)}</div>'
    )


def _processing_html() -> str:
    """Visual placeholder shown while the API is processing."""
    return (
        '<div style="padding: 8px 12px; border-radius: 6px; '
        "background: #6b72801a; border-left: 4px solid #6b7280; "
        'color: #6b7280; font-weight: 500;">Processing — waiting for the API response...</div>'
    )


def _user_facing_http_error(status_code: int) -> str:
    """Friendly message for an HTTP error (no URL or body exposed).

    Technical details go to the logger; the user only gets actionable
    information (retry, report to the operator).
    """
    if status_code == 503:
        return (
            "Service temporarily unavailable. The backend may be starting "
            "(Ollama or Qdrant). Try again in a few moments."
        )
    if status_code == 504:
        return (
            "The gateway timed out. The model is taking longer than expected. Try again."
        )
    if status_code == 401:
        return "Session expired. Log in again."
    if status_code == 429:
        return "Request limit exceeded. Wait a few seconds."
    if 400 <= status_code < 500:
        return f"Your request was rejected (code {status_code}). Review the data and try again."
    return "The server ran into a problem. Try again shortly."


def _error_html(user_msg: str) -> str:
    """Renders the red error badge for the verification panel.

    `user_msg` is escaped as defense in depth — it currently comes from
    `_user_facing_http_error` (static strings), but the escape guards
    against future regressions that include dynamic content.
    """
    return (
        '<div style="padding: 8px 12px; border-radius: 6px; '
        "background: #ef44441a; border-left: 4px solid #ef4444; "
        f'color: #ef4444; font-weight: 500;">{html.escape(user_msg)}</div>'
    )


def _history_with_error(
    history: list[dict[str, str]],
    user_message: str,
    error_text: str,
) -> list[dict[str, str]]:
    """Appends an error turn to the history without losing the user's question."""
    return history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": f"⚠ {error_text}"},
    ]


def create_interface(api_url: str) -> gr.Blocks:
    """Creates the full Gradio interface.

    Args:
        api_url: Base URL of the SmartB100 API.

    Returns:
        Configured Gradio application.
    """
    session = ChatSession(api_url)

    def respond(
        message: str,
        history: list[dict[str, str]],
        name: str,
        expertise: str,
    ) -> Generator[tuple[list[dict[str, str]], str, str], None, None]:
        """Processes a message and updates the history.

        Yields a ``(history, score_html, msg_input_value)`` triple:
        - First yield: processing placeholder (<1s) preserving the input.
        - Second yield: final result (success or error). On success the
          input is cleared; on error it is preserved so the user can retry
          without retyping.

        Args:
            message: The user's message.
            history: Message history in Gradio format.
            name: User name.
            expertise: Expertise level.

        Yields:
            Tuple of (updated history, score HTML badge, input value).
        """
        if not message.strip():
            yield history, "", message
            return

        user_name = name.strip() or "User"
        user_expertise = expertise or "intermediate"

        # Yield #1: immediate placeholder so the user sees activity
        preview = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "..."},
        ]
        yield preview, _processing_html(), message

        try:
            answer, score = send_with_retry(session, message, user_name, user_expertise)

            new_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]
            # Yield #2 success: final history + colored score + empty input
            yield new_history, _score_html(score, settings.hallucination_threshold), ""

        except httpx.HTTPStatusError as exc:
            logger.error(
                "chat.http_error status=%d url=%s body=%s",
                exc.response.status_code,
                exc.request.url,
                exc.response.text[:200],
            )
            user_msg = _user_facing_http_error(exc.response.status_code)
            yield _history_with_error(history, message, user_msg), _error_html(user_msg), message

        except httpx.TimeoutException:
            logger.exception("chat.timeout url=%s", api_url)
            user_msg = (
                "Timed out waiting for the API. In CPU-only environments Ollama "
                "can take several minutes per answer. Try again shortly."
            )
            yield _history_with_error(history, message, user_msg), _error_html(user_msg), message

        except httpx.RequestError:
            logger.exception("chat.connection_error url=%s", api_url)
            user_msg = (
                "Could not connect to the API. Check that the server is "
                "running and try again."
            )
            yield _history_with_error(history, message, user_msg), _error_html(user_msg), message

    def reset_session() -> tuple[list[dict[str, str]], str, str]:
        """Resets the session and clears the history.

        Returns:
            Tuple of (empty history, new session_id, empty score).
        """
        new_session_id = session.reset()
        return [], f"Session ID: {new_session_id[:8]}...", ""

    def get_session_info() -> str:
        """Returns information about the current session.

        Returns:
            String with the truncated session_id.
        """
        return f"Session ID: {session.session_id[:8]}..."

    with gr.Blocks(
        title="SmartB100 - Agricultural Assistant",
    ) as interface:
        gr.Markdown(
            """
            # SmartB100 - Intelligent Agricultural Assistant

            Ask questions about agricultural practices, crop management, and technical
            recommendations. The system uses RAG (Retrieval-Augmented Generation) to
            search for relevant information in indexed technical documents.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Profile Settings")
                name_input = gr.Textbox(
                    label="Name",
                    placeholder="Your name",
                    value="Farmer",
                )
                expertise_input = gr.Dropdown(
                    label="Expertise Level",
                    choices=[
                        ("Beginner", "beginner"),
                        ("Intermediate", "intermediate"),
                        ("Expert", "expert"),
                    ],
                    value="intermediate",
                )

                gr.Markdown("### Session")
                session_info = gr.Textbox(
                    label="Current Session",
                    value=get_session_info(),
                    interactive=False,
                )
                reset_btn = gr.Button("New Session", variant="secondary")

                gr.Markdown("### Verification")
                # `label` via Markdown — gr.HTML does not support `label=` like
                # Textbox, so the title is kept above the badge.
                gr.Markdown("**Last Verification**")
                # gr.HTML accepts colored markup; replaces the plain textbox to
                # allow visual feedback aligned with hallucination_threshold.
                score_display = gr.HTML(value="")

            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=500,
                )
                msg_input = gr.Textbox(
                    label="Your Question",
                    placeholder="Type your question about agriculture...",
                    lines=2,
                )
                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat")

        # `respond` returns 3 outputs: (history, score_html, input_value).
        # On success the input becomes ""; on error it keeps the original text
        # so the user can retry without retyping.
        submit_btn.click(
            fn=respond,
            inputs=[msg_input, chatbot, name_input, expertise_input],
            outputs=[chatbot, score_display, msg_input],
        )

        msg_input.submit(
            fn=respond,
            inputs=[msg_input, chatbot, name_input, expertise_input],
            outputs=[chatbot, score_display, msg_input],
        )

        reset_btn.click(
            fn=reset_session,
            outputs=[chatbot, session_info, score_display],
        )

        clear_btn.click(
            fn=lambda: [],
            outputs=chatbot,
        )

    return interface


def main() -> None:
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Gradio interface for SmartB100",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"SmartB100 API URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Gradio server port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a temporary public link",
    )

    args = parser.parse_args()

    interface = create_interface(args.api_url)
    interface.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
