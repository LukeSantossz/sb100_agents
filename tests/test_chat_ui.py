"""Testes para a Gradio UI (TASK-T72).

Cobre helpers puros — classificação de score, mensagens user-facing e o
retry com backoff. Não levanta o servidor Gradio (`gr.Blocks.launch`).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import httpx
import pytest

from ui.chat_ui import (
    ChatSession,
    _classify_score,
    _is_transient_error,
    _user_facing_http_error,
    send_with_retry,
)

# ============================================================================
# _classify_score — bandas alinhadas ao threshold
# ============================================================================


class TestClassifyScore:
    def test_low_band_returns_green(self) -> None:
        text, color = _classify_score(0.1, 0.5)
        assert color == "#22c55e"
        assert "Baixo risco" in text

    def test_mid_band_returns_yellow(self) -> None:
        text, color = _classify_score(0.4, 0.5)
        assert color == "#eab308"
        assert "moderado" in text

    def test_high_band_returns_red(self) -> None:
        text, color = _classify_score(0.8, 0.5)
        assert color == "#ef4444"
        assert "Alto risco" in text

    def test_boundary_low_high(self) -> None:
        # threshold=0.5: low_band=0.3, high_band=0.6
        # Exatamente 0.3 cai em mid (>=); 0.6 cai em high (>=)
        assert _classify_score(0.30, 0.5)[1] == "#eab308"
        assert _classify_score(0.60, 0.5)[1] == "#ef4444"
        assert _classify_score(0.2999, 0.5)[1] == "#22c55e"

    def test_alignment_with_threshold(self) -> None:
        # Threshold custom 0.8 → bandas 0.48 / 0.96
        assert _classify_score(0.4, 0.8)[1] == "#22c55e"  # < 0.48
        assert _classify_score(0.7, 0.8)[1] == "#eab308"  # 0.48-0.96
        assert _classify_score(0.97, 0.8)[1] == "#ef4444"  # >= 0.96

    def test_threshold_zero_collapses_to_red(self) -> None:
        # Edge: threshold=0 ⇒ todas as bandas em 0 ⇒ qualquer score positivo é vermelho
        assert _classify_score(0.01, 0.0)[1] == "#ef4444"

    def test_score_formatted_two_decimals(self) -> None:
        text, _ = _classify_score(0.125, 0.5)
        assert "0.12" in text or "0.13" in text


# ============================================================================
# _user_facing_http_error — sem leak de URL
# ============================================================================


class TestUserFacingHttpError:
    @pytest.mark.parametrize("status", [503, 504, 401, 429, 400, 404, 500])
    def test_no_url_in_message(self, status: int) -> None:
        msg = _user_facing_http_error(status)
        assert "http" not in msg.lower()
        assert "://" not in msg

    def test_503_mentions_backend(self) -> None:
        assert "indispon" in _user_facing_http_error(503).lower()

    def test_504_mentions_timeout(self) -> None:
        assert "tempo" in _user_facing_http_error(504).lower()

    def test_401_session_expired(self) -> None:
        assert "sess" in _user_facing_http_error(401).lower()

    def test_429_rate_limit(self) -> None:
        assert "limite" in _user_facing_http_error(429).lower()

    def test_4xx_fallback(self) -> None:
        msg = _user_facing_http_error(418)
        assert "418" in msg

    def test_5xx_fallback(self) -> None:
        msg = _user_facing_http_error(500)
        # Mensagem genérica sem expor status
        assert msg


# ============================================================================
# _is_transient_error — política de retry
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
        # ConnectError sem ser timeout não deve causar retry
        assert _is_transient_error(httpx.ConnectError("refused")) is False


# ============================================================================
# send_with_retry — backoff e propagação
# ============================================================================


class TestSendWithRetry:
    @pytest.fixture
    def session(self) -> Mock:
        sess = Mock(spec=ChatSession)
        sess.api_url = "http://test"
        return sess

    def test_first_attempt_success(self, session: Mock) -> None:
        session.send_message.return_value = ("answer", 0.2)
        result = send_with_retry(session, "q?", "u", "expert")
        assert result == ("answer", 0.2)
        assert session.send_message.call_count == 1

    def test_eventual_success_after_503(self, session: Mock) -> None:
        response = Mock(status_code=503)
        transient = httpx.HTTPStatusError("503", request=Mock(), response=response)
        session.send_message.side_effect = [transient, ("answer", 0.1)]

        with patch("ui.chat_ui.time.sleep") as mock_sleep:
            result = send_with_retry(session, "q?", "u", "expert", attempts=2)

        assert result == ("answer", 0.1)
        assert session.send_message.call_count == 2
        mock_sleep.assert_called_once_with(1.0)  # backoff = 1 * 2**0 = 1

    def test_exhausts_retries_then_raises(self, session: Mock) -> None:
        session.send_message.side_effect = httpx.TimeoutException("slow")
        with patch("ui.chat_ui.time.sleep"), pytest.raises(httpx.TimeoutException):
            send_with_retry(session, "q?", "u", "expert", attempts=2)
        # 1 + 2 retries = 3 tentativas
        assert session.send_message.call_count == 3

    def test_non_transient_does_not_retry(self, session: Mock) -> None:
        response = Mock(status_code=400)
        non_transient = httpx.HTTPStatusError("400", request=Mock(), response=response)
        session.send_message.side_effect = non_transient

        with (
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.HTTPStatusError),
        ):
            send_with_retry(session, "q?", "u", "expert", attempts=2)

        assert session.send_message.call_count == 1
        mock_sleep.assert_not_called()

    def test_exponential_backoff_progression(self, session: Mock) -> None:
        session.send_message.side_effect = httpx.TimeoutException("slow")
        with (
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.TimeoutException),
        ):
            send_with_retry(session, "q?", "u", "expert", attempts=3)
        # 3 retries → sleeps 1, 2, 4 (2**0, 2**1, 2**2)
        assert [c.args[0] for c in mock_sleep.call_args_list] == [1.0, 2.0, 4.0]

    def test_connection_error_not_retried(self, session: Mock) -> None:
        # ConnectError não é transitório por política — falha imediato
        session.send_message.side_effect = httpx.ConnectError("refused")
        with (
            patch("ui.chat_ui.time.sleep") as mock_sleep,
            pytest.raises(httpx.ConnectError),
        ):
            send_with_retry(session, "q?", "u", "expert", attempts=2)
        assert session.send_message.call_count == 1
        mock_sleep.assert_not_called()
