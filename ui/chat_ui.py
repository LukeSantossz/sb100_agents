"""Gradio chat interface for the SmartB100 agent.

Interactive web interface that consumes the FastAPI POST /chat endpoint
behind JWT authentication, supporting:

- A login row exchanging credentials for a JWT via POST /auth/token.
- Per-browser session state (``gr.State``) holding the token, a unique
  conversation_id, and the API URL — two browsers are fully independent.
- Natural-language questions sent with ``Authorization: Bearer <token>``.
- hallucination_score display per answer (colors aligned with
  ``settings.hallucination_threshold``).
- Session management with reset option (per-session only).
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

# Shared HTTP client. httpx.Client is safe to reuse across requests; the
# per-user identity lives in the session state's token, not in the client.
# settings.chat_timeout: configurable via env CHAT_TIMEOUT (default 600s)
_client = httpx.Client(timeout=settings.chat_timeout)


# ============================================================================
# Per-session state
# ============================================================================
#
# The session is a plain dict carried in a per-browser ``gr.State``:
#   {"token": str | None, "conversation_id": int | None, "api_url": str}
# isolates every browser connection.


def new_session_state(api_url: str) -> dict:
    """Create a fresh, unauthenticated session state for one browser.

    Args:
        api_url: Base URL of the SmartB100 API.

    Returns:
        A state dict with no token and a unset conversation_id.
    """
    return {
        "token": None,
        "conversation_id": None,
        "api_url": api_url.rstrip("/"),
    }


def get_session_info(state: dict) -> str:
    """Human-readable label with the conversation_id."""
    cid = state.get("conversation_id")
    if cid is None:
        return "Nova Conversa (Sem ID)"
    return f"Conversa ID: {cid}"


def login(state: dict, username: str, password: str) -> tuple[dict, str]:
    """Exchange username/password for a JWT and store it in the session state.

    Posts the OAuth2 password form to ``/auth/token``. On success the returned
    ``access_token`` is stored in a new state; on failure the token stays unset
    and a friendly message is returned (no technical detail leaks to the user).

    Args:
        state: Current session state.
        username: Username typed in the UI.
        password: Password typed in the UI.

    Returns:
        Tuple of (updated state, status message for display).
    """
    if not username or not password:
        return {**state, "token": None}, "Enter your username and password to log in."

    try:
        response = _client.post(
            f"{state['api_url']}/auth/token",
            data={"username": username, "password": password},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            logger.info("ui.login.invalid_credentials")
            return {**state, "token": None}, "Login failed: incorrect username or password."
        logger.error("ui.login.http_error status=%d", exc.response.status_code)
        return {**state, "token": None}, "Login failed. Please try again."
    except httpx.RequestError:
        logger.exception("ui.login.connection_error url=%s", state["api_url"])
        return (
            {**state, "token": None},
            "Could not reach the API to log in. Check the server and try again.",
        )

    token = response.json()["access_token"]
    logger.info("ui.login.success")
    return {**state, "token": token}, "Logged in. You can ask your question now."


def post_chat(state: dict, message: str) -> tuple[str, float, int]:
    """Send one authenticated question to POST /chat.

    Attaches ``Authorization: Bearer <token>`` and targets the state's own
    conversation_id. The caller guarantees a token is present.

    Args:
        state: Authenticated session state.
        message: The user's question.

    Returns:
        Tuple of (answer, hallucination_score, conversation_id).

    Raises:
        httpx.HTTPStatusError: If the API returns an HTTP error (401 included).
        httpx.RequestError: If a connection error occurs.
    """
    payload = {
        "conversation_id": state.get("conversation_id"),
        "question": message,
    }
    response = _client.post(
        f"{state['api_url']}/chat",
        json=payload,
        headers={"Authorization": f"Bearer {state['token']}"},
    )
    response.raise_for_status()
    data = response.json()
    return data["answer"], data["hallucination_score"], data["conversation_id"]


def _is_transient_error(exc: Exception) -> bool:
    """Identifies transient failures eligible for retry."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (503, 504)
    return False


def send_with_retry(
    state: dict,
    message: str,
    attempts: int = RETRY_ATTEMPTS,
) -> tuple[str, float, int]:
    """Send a message with exponential retry for transient errors.

    Args:
        state: Authenticated session state.
        message: The user's question.
        attempts: Number of additional retries (total = 1 + attempts).

    Returns:
        Tuple of (answer, hallucination_score, conversation_id).

    Raises:
        httpx.HTTPStatusError | httpx.RequestError: If all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return post_chat(state, message)
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

    assert last_exc is not None
    raise last_exc


def _classify_score(score: float, threshold: float) -> tuple[str, str]:
    """Maps a numeric score to a risk band and display color."""
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
    """Friendly message for an HTTP error (no URL or body exposed)."""
    if status_code == 503:
        return (
            "Service temporarily unavailable. The backend may be starting "
            "(Ollama or Qdrant). Try again in a few moments."
        )
    if status_code == 504:
        return "The gateway timed out. The model is taking longer than expected. Try again."
    if status_code == 401:
        return "Session expired. Log in again."
    if status_code == 429:
        return "Request limit exceeded. Wait a few seconds."
    if 400 <= status_code < 500:
        return f"Your request was rejected (code {status_code}). Review the data and try again."
    return "The server ran into a problem. Try again shortly."


def _error_html(user_msg: str) -> str:
    """Renders the red error badge for the verification panel."""
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


def respond(
    state: dict,
    message: str,
    history: list[dict[str, str]],
) -> Generator[tuple[dict, list[dict[str, str]], str, str], None, None]:
    """Process a message and update history, threaded through the session state.

    Yields a ``(state, history, score_html, msg_input_value)`` tuple.
    """
    if not message.strip():
        yield state, history, "", message
        return

    if not state.get("token"):
        msg = "Please log in before sending a question."
        yield state, _history_with_error(history, message, msg), _error_html(msg), message
        return

    # Yield #1: immediate placeholder so the user sees activity
    preview = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "..."},
    ]
    yield state, preview, _processing_html(), message

    try:
        answer, score, conversation_id = send_with_retry(state, message)

        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ]
        new_state = {**state, "conversation_id": conversation_id}
        # Yield #2 success: final history + colored score + empty input
        yield new_state, new_history, _score_html(score, settings.hallucination_threshold), ""

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            logger.warning("chat.unauthorized")
            user_msg = _user_facing_http_error(401)
            cleared = {**state, "token": None}
            yield (
                cleared,
                _history_with_error(history, message, user_msg),
                _error_html(user_msg),
                message,
            )
            return
        logger.error(
            "chat.http_error status=%d url=%s body=%s",
            exc.response.status_code,
            exc.request.url,
            exc.response.text[:200],
        )
        user_msg = _user_facing_http_error(exc.response.status_code)
        yield state, _history_with_error(history, message, user_msg), _error_html(user_msg), message

    except httpx.TimeoutException:
        logger.exception("chat.timeout url=%s", state["api_url"])
        user_msg = (
            "Timed out waiting for the API. In CPU-only environments Ollama "
            "can take several minutes per answer. Try again shortly."
        )
        yield state, _history_with_error(history, message, user_msg), _error_html(user_msg), message

    except httpx.RequestError:
        logger.exception("chat.connection_error url=%s", state["api_url"])
        user_msg = "Could not connect to the API. Check that the server is running and try again."
        yield state, _history_with_error(history, message, user_msg), _error_html(user_msg), message


def reset_session(state: dict) -> tuple[dict, list[dict[str, str]], str, str]:
    """Start a new conversation for this browser only (keeps the login)."""
    new_state = {**state, "conversation_id": None}
    return new_state, [], get_session_info(new_state), ""


def create_interface(api_url: str) -> gr.Blocks:
    """Creates the full Gradio interface."""

    def init_session() -> tuple[dict, str]:
        """Per-connection initialiser wired to ``interface.load``."""
        state = new_session_state(api_url)
        return state, get_session_info(state)

    with gr.Blocks(
        title="SmartB100 - Agricultural Assistant",
    ) as interface:
        session_state = gr.State()

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
                gr.Markdown("### Login")
                username_input = gr.Textbox(
                    label="Username",
                    placeholder="your username",
                )
                password_input = gr.Textbox(
                    label="Password",
                    placeholder="your password",
                    type="password",
                )
                login_btn = gr.Button("Log in", variant="primary")
                login_status = gr.Markdown("")

                gr.Markdown("### Session")
                session_info = gr.Textbox(
                    label="Current Session",
                    value="",
                    interactive=False,
                )
                reset_btn = gr.Button("New Session", variant="secondary")

                gr.Markdown("### Verification")
                gr.Markdown("**Last Verification**")
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

        # Initialise per-browser state and session label on connection.
        interface.load(init_session, outputs=[session_state, session_info])

        # Login exchanges credentials for a token stored in the session state.
        login_btn.click(
            fn=login,
            inputs=[session_state, username_input, password_input],
            outputs=[session_state, login_status],
        )

        submit_btn.click(
            fn=respond,
            inputs=[session_state, msg_input, chatbot],
            outputs=[session_state, chatbot, score_display, msg_input],
        )

        msg_input.submit(
            fn=respond,
            inputs=[session_state, msg_input, chatbot],
            outputs=[session_state, chatbot, score_display, msg_input],
        )

        reset_btn.click(
            fn=reset_session,
            inputs=[session_state],
            outputs=[session_state, chatbot, session_info, score_display],
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
