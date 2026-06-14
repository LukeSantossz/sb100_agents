"""Tests for the Gradio UI.

Covers the per-session authentication and state functions (login, bearer-token
attachment, no-token guard, 401 token clearing, independent session state) plus
the pure helpers — score classification, user-facing messages, and the retry
with backoff. Does not start the Gradio server (`gr.Blocks.launch`).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from ui.chat_ui import (
    _classify_score,
    _is_transient_error,
    _user_facing_http_error,
    login,
    new_session_state,
    post_chat,
    respond,
    send_with_retry,
)


def _authenticated_state() -> dict:
    """A session state that already holds a token."""
    return {"token": "tok-123", "session_id": "sid-abc", "api_url": "http://test"}


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    """Build an HTTPStatusError whose response exposes ``status_code``."""
    return httpx.HTTPStatusError(
        str(status_code), request=Mock(), response=Mock(status_code=status_code)
    )


# ============================================================================
# new_session_state — per-connection isolation (#96)
# ============================================================================


class TestNewSessionState:
    def test_starts_without_token(self) -> None:
        state = new_session_state("http://test")
        assert state["token"] is None
        assert state["api_url"] == "http://test"
        assert state["session_id"]

    def test_each_session_state_is_independent(self) -> None:
        first = new_session_state("http://test")
        second = new_session_state("http://test")
        # Distinct session_ids and independent (both unset) tokens — no shared
        # module-level ChatSession.
        assert first["session_id"] != second["session_id"]
        assert first["token"] is None and second["token"] is None

    def test_api_url_trailing_slash_stripped(self) -> None:
        assert new_session_state("http://test/")["api_url"] == "http://test"


# ============================================================================
# login — exchange credentials for a JWT (#89)
# ============================================================================


class TestLogin:
    def test_login_exchanges_credentials_for_token(self) -> None:
        state = new_session_state("http://test")
        response = Mock()
        response.json.return_value = {"access_token": "JWT-XYZ", "token_type": "bearer"}
        response.raise_for_status = Mock()

        with patch("ui.chat_ui._client.post", return_value=response) as mock_post:
            new_state, _ = login(state, "alice", "s3cret-pass")

        assert new_state["token"] == "JWT-XYZ"
        url = mock_post.call_args[0][0]
        assert url == "http://test/auth/token"
        # OAuth2 password flow uses a form body, not JSON.
        assert mock_post.call_args[1]["data"] == {
            "username": "alice",
            "password": "s3cret-pass",
        }

    def test_login_failure_surfaces_friendly_message(self) -> None:
        state = new_session_state("http://test")
        response = Mock()
        response.raise_for_status.side_effect = _http_status_error(401)

        with patch("ui.chat_ui._client.post", return_value=response):
            new_state, message = login(state, "alice", "wrong")

        assert new_state["token"] is None
        assert "http" not in message.lower()
        assert message  # non-empty friendly message

    def test_missing_credentials_does_not_call_api(self) -> None:
        state = new_session_state("http://test")
        with patch("ui.chat_ui._client.post") as mock_post:
            new_state, message = login(state, "", "")
        mock_post.assert_not_called()
        assert new_state["token"] is None
        assert message


# ============================================================================
# post_chat — bearer-token attachment (#89)
# ============================================================================


class TestPostChat:
    def test_send_message_attaches_bearer_token(self) -> None:
        state = _authenticated_state()
        response = Mock()
        response.json.return_value = {"answer": "ok", "hallucination_score": 0.1}
        response.raise_for_status = Mock()

        with patch("ui.chat_ui._client.post", return_value=response) as mock_post:
            answer, score = post_chat(state, "question?", "user", "expert")

        assert (answer, score) == ("ok", 0.1)
        assert mock_post.call_args[0][0] == "http://test/chat"
        assert mock_post.call_args[1]["headers"]["Authorization"] == "Bearer tok-123"
        # Targets the session's own session_id (#96).
        assert mock_post.call_args[1]["json"]["session_id"] == "sid-abc"


# ============================================================================
# respond — no-token guard (#89) and 401 token clearing (#89)
# ============================================================================


class TestRespond:
    def test_send_message_without_token_does_not_call_chat(self) -> None:
        state = new_session_state("http://test")  # token is None
        with patch("ui.chat_ui.send_with_retry") as mock_send:
            outputs = list(respond(state, "question?", [], "user", "expert"))

        mock_send.assert_not_called()
        final_state, history, _score_html, _msg = outputs[-1]
        assert final_state["token"] is None
        assert "log in" in history[-1]["content"].lower()

    def test_http_401_clears_token_state(self) -> None:
        state = _authenticated_state()
        with patch("ui.chat_ui.send_with_retry", side_effect=_http_status_error(401)):
            outputs = list(respond(state, "question?", [], "user", "expert"))

        final_state = outputs[-1][0]
        assert final_state["token"] is None

    def test_successful_answer_keeps_token_and_appends_history(self) -> None:
        state = _authenticated_state()
        with patch("ui.chat_ui.send_with_retry", return_value=("the answer", 0.2)):
            outputs = list(respond(state, "question?", [], "user", "expert"))

        final_state, history, _score_html, msg_input = outputs[-1]
        assert final_state["token"] == "tok-123"
        assert history[-1]["content"] == "the answer"
        assert msg_input == ""  # input cleared on success

    def test_blank_message_makes_no_request(self) -> None:
        state = _authenticated_state()
        with patch("ui.chat_ui.send_with_retry") as mock_send:
            outputs = list(respond(state, "   ", [], "user", "expert"))
        mock_send.assert_not_called()
        assert outputs[-1][0]["token"] == "tok-123"


# ============================================================================
# _classify_score — bands aligned with the threshold
# ============================================================================


class TestClassifyScore:
    def test_low_band_returns_green(self) -> None:
        text, color = _classify_score(0.1, 0.5)
        assert color == "#22c55e"
        assert "Low risk" in text

    def test_mid_band_returns_yellow(self) -> None:
        text, color = _classify_score(0.4, 0.5)
        assert color == "#eab308"
        assert "Moderate risk" in text

    def test_high_band_returns_red(self) -> None:
        text, color = _classify_score(0.8, 0.5)
        assert color == "#ef4444"
        assert "High risk" in text

    def test_boundary_low_high(self) -> None:
        # threshold=0.5: low_band=0.3, high_band=0.6
        # Exactly 0.3 falls in mid (>=); 0.6 falls in high (>=)
        assert _classify_score(0.30, 0.5)[1] == "#eab308"
        assert _classify_score(0.60, 0.5)[1] == "#ef4444"
        assert _classify_score(0.2999, 0.5)[1] == "#22c55e"

    def test_alignment_with_threshold(self) -> None:
        # Custom threshold 0.8 → bands 0.48 / 0.96
        assert _classify_score(0.4, 0.8)[1] == "#22c55e"  # < 0.48
        assert _classify_score(0.7, 0.8)[1] == "#eab308"  # 0.48-0.96
        assert _classify_score(0.97, 0.8)[1] == "#ef4444"  # >= 0.96

    def test_threshold_zero_collapses_to_red(self) -> None:
        # Edge: threshold=0 ⇒ all bands at 0 ⇒ any positive score is red
        assert _classify_score(0.01, 0.0)[1] == "#ef4444"

    def test_score_formatted_two_decimals(self) -> None:
        text, _ = _classify_score(0.125, 0.5)
        assert "0.12" in text or "0.13" in text


# ============================================================================
# _user_facing_http_error — no URL leak
# ============================================================================


class TestUserFacingHttpError:
    @pytest.mark.parametrize("status", [503, 504, 401, 429, 400, 404, 500])
    def test_no_url_in_message(self, status: int) -> None:
        msg = _user_facing_http_error(status)
        assert "http" not in msg.lower()
        assert "://" not in msg

    def test_503_mentions_backend(self) -> None:
        assert "unavailable" in _user_facing_http_error(503).lower()

    def test_504_mentions_timeout(self) -> None:
        assert "timed out" in _user_facing_http_error(504).lower()

    def test_401_session_expired(self) -> None:
        assert "session" in _user_facing_http_error(401).lower()

    def test_429_rate_limit(self) -> None:
        assert "limit" in _user_facing_http_error(429).lower()

    def test_4xx_fallback(self) -> None:
        msg = _user_facing_http_error(418)
        assert "418" in msg

    def test_5xx_fallback(self) -> None:
        msg = _user_facing_http_error(500)
        # Generic message without exposing the status
        assert msg


# ============================================================================
# _is_transient_error — retry policy
# ============================================================================


class TestIsTransientError:
    def test_timeout_is_transient(self) -> None:
        assert _is_transient_error(httpx.TimeoutException("slow")) is True

    def test_503_is_transient(self) -> None:
        response = Mock(status_code=503)
        exc = httpx.HTTPStatusError("503", request=Mock(), response=response)
        assert _is_transient_error(exc) is True

    def test_504_is_transient(self) -> None:
        response = Mock(status_code=504)
        exc = httpx.HTTPStatusError("504", request=Mock(), response=response)
        assert _is_transient_error(exc) is True

    def test_500_is_not_transient(self) -> None:
        response = Mock(status_code=500)
        exc = httpx.HTTPStatusError("500", request=Mock(), response=response)
        assert _is_transient_error(exc) is False

    def test_401_is_not_transient(self) -> None:
        response = Mock(status_code=401)
        exc = httpx.HTTPStatusError("401", request=Mock(), response=response)
        assert _is_transient_error(exc) is False

    def test_generic_request_error_not_transient(self) -> None:
        # A ConnectError that is not a timeout must not trigger retry
        assert _is_transient_error(httpx.ConnectError("refused")) is False


# ============================================================================
# send_with_retry — backoff and propagation (threaded through session state)
# ============================================================================


class TestSendWithRetry:
    STATE = {"token": "t", "session_id": "s", "api_url": "http://test"}

    def test_first_attempt_success(self) -> None:
        with patch("ui.chat_ui.post_chat", return_value=("answer", 0.2)) as mock_post:
            result = send_with_retry(self.STATE, "q?", "u", "expert")
        assert result == ("answer", 0.2)
        assert mock_post.call_count == 1

    def test_eventual_success_after_503(self) -> None:
        transient = _http_status_error(503)
        with (
            patch("ui.chat_ui.post_chat", side_effect=[transient, ("answer", 0.1)]) as mock_post,
            patch("ui.chat_ui.time.sleep") as mock_sleep,
        ):
            result = send_with_retry(self.STATE, "q?", "u", "expert", attempts=2)

        assert result == ("answer", 0.1)
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # backoff = 1 * 2**0 = 1

    def test_exhausts_retries_then_raises(self) -> None:
        with (
            patch("ui.chat_ui.post_chat", side_effect=httpx.TimeoutException("slow")) as mock_post,
            patch("ui.chat_ui.time.sleep"),
            pytest.raises(httpx.TimeoutException),
        ):
            send_with_retry(self.STATE, "q?", "u", "expert", attempts=2)
        # 1 + 2 retries = 3 attempts
        assert mock_post.call_count == 3

    def test_non_transient_does_not_retry(self) -> None:
        with (
            patch("ui.chat_ui.post_chat", side_effect=_http_status_error(400)) as mock_post,
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.HTTPStatusError),
        ):
            send_with_retry(self.STATE, "q?", "u", "expert", attempts=2)

        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()

    def test_exponential_backoff_progression(self) -> None:
        with (
            patch("ui.chat_ui.post_chat", side_effect=httpx.TimeoutException("slow")),
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.TimeoutException),
        ):
            send_with_retry(self.STATE, "q?", "u", "expert", attempts=3)
        # 3 retries → sleeps 1, 2, 4 (2**0, 2**1, 2**2)
        assert [c.args[0] for c in mock_sleep.call_args_list] == [1.0, 2.0, 4.0]

    def test_connection_error_not_retried(self) -> None:
        with (
            patch("ui.chat_ui.post_chat", side_effect=httpx.ConnectError("refused")) as mock_post,
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.ConnectError),
        ):
            send_with_retry(self.STATE, "q?", "u", "expert", attempts=2)
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()
