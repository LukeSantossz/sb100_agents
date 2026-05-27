"""Interface Gradio para chat com o agente SmartB100.

Este módulo implementa uma interface web interativa que consome
o endpoint POST /chat da API FastAPI, permitindo:

- Envio de perguntas em linguagem natural.
- Configuração do perfil do usuário (nome e expertise).
- Visualização do hallucination_score em cada resposta (cores alinhadas
  com ``settings.hallucination_threshold``).
- Gerenciamento de sessão com opção de reset.
- Loading state via generator pattern (placeholder em <1s).
- Retry automático com backoff para falhas transitórias (503/504/timeout).
- URLs e detalhes técnicos da API são logados internamente; usuário recebe
  apenas mensagens amigáveis.

Uso:
    python ui/chat_ui.py [--api-url URL] [--port PORT]

    Exemplo:
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

# Permite import de core.config quando ui/ é executado standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PORT = 7860

# Retry transitório: 2 retries (3 tentativas total) com backoff 1s, 2s
RETRY_ATTEMPTS = 2
RETRY_BACKOFF_BASE = 1.0  # segundos; multiplicado por 2**attempt


class ChatSession:
    """Gerencia estado da sessão de chat."""

    def __init__(self, api_url: str) -> None:
        """Inicializa sessão de chat.

        Args:
            api_url: URL base da API SmartB100.
        """
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        # settings.chat_timeout: configurável via env CHAT_TIMEOUT (default 600s)
        self.client = httpx.Client(timeout=settings.chat_timeout)

    def reset(self) -> str:
        """Reseta sessão gerando novo session_id.

        Returns:
            Novo session_id gerado.
        """
        self.session_id = str(uuid.uuid4())
        return self.session_id

    def send_message(
        self,
        message: str,
        name: str,
        expertise: str,
    ) -> tuple[str, float]:
        """Envia mensagem para a API e retorna resposta.

        Args:
            message: Pergunta do usuário.
            name: Nome do usuário para o perfil.
            expertise: Nível de expertise (beginner, intermediate, expert).

        Returns:
            Tupla com (resposta, hallucination_score).

        Raises:
            httpx.HTTPStatusError: Se a API retornar erro HTTP.
            httpx.RequestError: Se houver erro de conexão.
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
    """Identifica falhas transitórias passíveis de retry.

    Retry aplica-se a:
    - ``httpx.TimeoutException``: timeout total da request.
    - ``httpx.HTTPStatusError`` com status 503/504: backend indisponível ou
      gateway timeout (típico de Ollama lento ou Qdrant em recovery).
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
    """Envia mensagem com retry exponencial para erros transitórios.

    Args:
        session: Sessão de chat ativa.
        message: Pergunta do usuário.
        name: Nome do usuário.
        expertise: Expertise do usuário.
        attempts: Número de retries adicionais (total = 1 + attempts).

    Returns:
        Tupla (resposta, hallucination_score).

    Raises:
        httpx.HTTPStatusError | httpx.RequestError: Se todas as tentativas
        falharem ou se o erro não for transitório.
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

    # Defensivo — loop sempre retorna ou raise; este path é inalcançável.
    assert last_exc is not None
    raise last_exc


def _classify_score(score: float, threshold: float) -> tuple[str, str]:
    """Mapeia score numérico para faixa de risco e cor visual.

    Bandas derivam de ``threshold`` (default 0.5) para que ajustes futuros
    de ``HALLUCINATION_THRESHOLD`` movam todas as faixas coerentemente:

    - **Verde** (baixo): score < threshold × 0.6.
    - **Amarelo** (moderado): threshold × 0.6 ≤ score < threshold × 1.2.
    - **Vermelho** (alto): score ≥ threshold × 1.2.

    Com threshold=0.5 default: verde <0.3, amarelo 0.3-0.6, vermelho ≥0.6.

    Args:
        score: hallucination_score (0.0-1.0).
        threshold: limiar base configurado em Settings.

    Returns:
        Tupla (texto descritivo, cor hex CSS).
    """
    low_band = threshold * 0.6
    high_band = threshold * 1.2

    if score < low_band:
        return (
            f"Score {score:.2f} — Baixo risco de alucinação. Resposta confiável.",
            "#22c55e",
        )
    if score < high_band:
        return (
            f"Score {score:.2f} — Risco moderado. Valide pontos críticos.",
            "#eab308",
        )
    return (
        f"Score {score:.2f} — Alto risco de alucinação. Verificação humana recomendada.",
        "#ef4444",
    )


def _score_html(score: float, threshold: float) -> str:
    """Renderiza badge HTML colorido para o score."""
    text, color = _classify_score(score, threshold)
    # `text` é gerado internamente (sem input externo), mas escapamos por
    # defesa em profundidade: se o conteúdo evoluir para incluir dado dinâmico,
    # o escape já está em vigor.
    return (
        f'<div style="padding: 8px 12px; border-radius: 6px; '
        f"background: {color}1a; border-left: 4px solid {color}; "
        f'color: {color}; font-weight: 500;">{html.escape(text)}</div>'
    )


def _processing_html() -> str:
    """Placeholder visual exibido enquanto a API processa."""
    return (
        '<div style="padding: 8px 12px; border-radius: 6px; '
        "background: #6b72801a; border-left: 4px solid #6b7280; "
        'color: #6b7280; font-weight: 500;">Processando — aguardando resposta da API...</div>'
    )


def _user_facing_http_error(status_code: int) -> str:
    """Mensagem amigavel para erro HTTP (sem expor URL ou body).

    Detalhes tecnicos vao para o logger; o usuario recebe apenas o que pode
    acionar (tentar de novo, reportar ao operador).
    """
    if status_code == 503:
        return (
            "Serviço temporariamente indisponível. O backend pode estar iniciando "
            "(Ollama ou Qdrant). Tente novamente em alguns instantes."
        )
    if status_code == 504:
        return (
            "Gateway atingiu o tempo limite. O modelo está demorando mais do que "
            "o esperado. Tente novamente."
        )
    if status_code == 401:
        return "Sessão expirou. Faça login novamente."
    if status_code == 429:
        return "Limite de requisições excedido. Aguarde alguns segundos."
    if 400 <= status_code < 500:
        return (
            f"Sua requisição foi rejeitada (código {status_code}). Revise os dados e tente de novo."
        )
    return "O servidor encontrou um problema. Tente novamente em instantes."


def _error_html(user_msg: str) -> str:
    """Renderiza badge vermelho de erro para o painel de verificação.

    `user_msg` é escapado por defesa em profundidade — atualmente vem de
    `_user_facing_http_error` (strings estáticas), mas o escape protege
    contra regressões futuras que venham a incluir conteúdo dinâmico.
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
    """Acrescenta turn de erro ao histórico sem perder a pergunta do usuário."""
    return history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": f"⚠ {error_text}"},
    ]


def create_interface(api_url: str) -> gr.Blocks:
    """Cria interface Gradio completa.

    Args:
        api_url: URL base da API SmartB100.

    Returns:
        Aplicação Gradio configurada.
    """
    session = ChatSession(api_url)

    def respond(
        message: str,
        history: list[dict[str, str]],
        name: str,
        expertise: str,
    ) -> Generator[tuple[list[dict[str, str]], str, str], None, None]:
        """Processa mensagem e atualiza histórico.

        Yields tripla ``(history, score_html, msg_input_value)``:
        - Primeiro yield: placeholder "Processando..." (<1s) preservando input.
        - Segundo yield: resultado final (sucesso ou erro). Em sucesso o
          input é limpo; em erro o input é preservado para o usuário poder
          tentar novamente sem redigitar.

        Args:
            message: Mensagem do usuário.
            history: Histórico de mensagens no formato Gradio.
            name: Nome do usuário.
            expertise: Nível de expertise.

        Yields:
            Tupla (histórico atualizado, badge HTML do score, valor do input).
        """
        if not message.strip():
            yield history, "", message
            return

        user_name = name.strip() or "Usuário"
        user_expertise = expertise or "intermediate"

        # Yield #1: placeholder imediato para o usuário ver atividade
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
            # Yield #2 sucesso: histórico final + score colorido + input vazio
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
                "Tempo esgotado aguardando a API. Em ambientes CPU-only o Ollama "
                "pode levar vários minutos por resposta. Tente novamente em instantes."
            )
            yield _history_with_error(history, message, user_msg), _error_html(user_msg), message

        except httpx.RequestError:
            logger.exception("chat.connection_error url=%s", api_url)
            user_msg = (
                "Não foi possível conectar à API. Verifique se o servidor está "
                "rodando e tente novamente."
            )
            yield _history_with_error(history, message, user_msg), _error_html(user_msg), message

    def reset_session() -> tuple[list[dict[str, str]], str, str]:
        """Reseta sessão e limpa histórico.

        Returns:
            Tupla com (histórico vazio, novo session_id, score vazio).
        """
        new_session_id = session.reset()
        return [], f"Session ID: {new_session_id[:8]}...", ""

    def get_session_info() -> str:
        """Retorna informação da sessão atual.

        Returns:
            String com session_id truncado.
        """
        return f"Session ID: {session.session_id[:8]}..."

    with gr.Blocks(
        title="SmartB100 - Assistente Agrícola",
    ) as interface:
        gr.Markdown(
            """
            # SmartB100 - Assistente Agrícola Inteligente

            Faça perguntas sobre práticas agrícolas, manejo de culturas e recomendações técnicas.
            O sistema utiliza RAG (Retrieval-Augmented Generation) para buscar informações
            relevantes em documentos técnicos indexados.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Configuração do Perfil")
                name_input = gr.Textbox(
                    label="Nome",
                    placeholder="Seu nome",
                    value="Produtor",
                )
                expertise_input = gr.Dropdown(
                    label="Nível de Expertise",
                    choices=[
                        ("Iniciante", "beginner"),
                        ("Intermediário", "intermediate"),
                        ("Especialista", "expert"),
                    ],
                    value="intermediate",
                )

                gr.Markdown("### Sessão")
                session_info = gr.Textbox(
                    label="Sessão Atual",
                    value=get_session_info(),
                    interactive=False,
                )
                reset_btn = gr.Button("Nova Sessão", variant="secondary")

                gr.Markdown("### Verificação")
                # `label` via Markdown — gr.HTML não suporta `label=` como Textbox,
                # então preservamos o título "Última Verificação" acima do badge.
                gr.Markdown("**Última Verificação**")
                # gr.HTML aceita markup com cores; substitui o textbox simples
                # para permitir feedback visual alinhado ao hallucination_threshold.
                score_display = gr.HTML(value="")

            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversa",
                    height=500,
                )
                msg_input = gr.Textbox(
                    label="Sua Pergunta",
                    placeholder="Digite sua pergunta sobre agricultura...",
                    lines=2,
                )
                with gr.Row():
                    submit_btn = gr.Button("Enviar", variant="primary")
                    clear_btn = gr.Button("Limpar Chat")

        # `respond` agora retorna 3 outputs: (history, score_html, input_value).
        # Em sucesso input vira ""; em erro input mantem o texto original para
        # o usuario poder tentar novamente sem redigitar.
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
    """Ponto de entrada principal da aplicação."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Interface Gradio para SmartB100",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"URL da API SmartB100 (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Porta do servidor Gradio (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Criar link público temporário",
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
