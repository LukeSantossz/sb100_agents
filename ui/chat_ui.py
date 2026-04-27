"""Interface Gradio para chat com o agente SmartB100.

Este módulo implementa uma interface web interativa que consome
o endpoint POST /chat da API FastAPI, permitindo:

- Envio de perguntas em linguagem natural.
- Configuração do perfil do usuário (nome e expertise).
- Visualização do hallucination_score em cada resposta.
- Gerenciamento de sessão com opção de reset.

Uso:
    python ui/chat_ui.py [--api-url URL] [--port PORT]

    Exemplo:
        python ui/chat_ui.py --api-url http://localhost:8000 --port 7860
"""

import argparse
import uuid
from collections.abc import Generator

import gradio as gr
import httpx

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PORT = 7860
REQUEST_TIMEOUT = 300.0


class ChatSession:
    """Gerencia estado da sessão de chat."""

    def __init__(self, api_url: str) -> None:
        """Inicializa sessão de chat.

        Args:
            api_url: URL base da API SmartB100.
        """
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        self.client = httpx.Client(timeout=REQUEST_TIMEOUT)

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
    ) -> Generator[tuple[list[dict[str, str]], str], None, None]:
        """Processa mensagem e atualiza histórico.

        Args:
            message: Mensagem do usuário.
            history: Histórico de mensagens no formato Gradio.
            name: Nome do usuário.
            expertise: Nível de expertise.

        Yields:
            Tupla com (histórico atualizado, info do score).
        """
        if not message.strip():
            yield history, ""
            return

        user_name = name.strip() or "Usuário"
        user_expertise = expertise or "intermediate"

        try:
            answer, score = session.send_message(message, user_name, user_expertise)

            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]

            score_info = f"Hallucination Score: {score:.2f}"
            if score > 0.7:
                score_info += " (alto risco)"
            elif score > 0.4:
                score_info += " (risco moderado)"
            else:
                score_info += " (baixo risco)"

            yield history, score_info

        except httpx.HTTPStatusError as e:
            error_msg = f"Erro da API: {e.response.status_code}"
            if e.response.status_code == 503:
                error_msg += " - Serviço indisponível. Verifique se Ollama e Qdrant estão rodando."
            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"Erro: {error_msg}"},
            ]
            yield history, error_msg

        except httpx.RequestError as e:
            error_msg = f"Erro de conexão: {e}"
            history = history + [
                {"role": "user", "content": message},
                {
                    "role": "assistant",
                    "content": f"Erro: Não foi possível conectar à API em {api_url}",
                },
            ]
            yield history, error_msg

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
                score_display = gr.Textbox(
                    label="Última Verificação",
                    value="",
                    interactive=False,
                )

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

        submit_btn.click(
            fn=respond,
            inputs=[msg_input, chatbot, name_input, expertise_input],
            outputs=[chatbot, score_display],
        ).then(
            fn=lambda: "",
            outputs=msg_input,
        )

        msg_input.submit(
            fn=respond,
            inputs=[msg_input, chatbot, name_input, expertise_input],
            outputs=[chatbot, score_display],
        ).then(
            fn=lambda: "",
            outputs=msg_input,
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
