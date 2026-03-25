"""
Módulo para geração de múltiplas respostas de um modelo de linguagem (LLM).

Gera várias respostas para a mesma entrada utilizando chamadas assíncronas,
permitindo posterior análise de consistência via entropia semântica.
"""

import asyncio
from typing import Callable, Awaitable


async def generate_responses(
    prompt: str,
    model_call: Callable[[str, float], Awaitable[str]],
    num_responses: int = 5,
    temperature: float = 0.7,
) -> list[str]:
    """
    Gera múltiplas respostas para um prompt utilizando chamadas assíncronas.

    Executa várias chamadas ao modelo em paralelo para obter respostas
    diversas que serão usadas na análise de entropia semântica.

    Args:
        prompt: Texto de entrada para o modelo.
        model_call: Função assíncrona que chama o modelo.
                   Assinatura: async def(prompt: str, temperature: float) -> str
        num_responses: Número de respostas a gerar (default: 5).
        temperature: Parâmetro de aleatoriedade do modelo (default: 0.7).
                    Valores mais altos geram respostas mais diversas.

    Returns:
        Lista de strings contendo as respostas geradas pelo modelo.
    """
    tasks = [model_call(prompt, temperature) for _ in range(num_responses)]
    responses = await asyncio.gather(*tasks)
    return list(responses)


async def mock_model_call(prompt: str, temperature: float) -> str:
    """
    Simula uma chamada assíncrona a um modelo de linguagem (para testes).

    Esta função serve como placeholder para testes unitários e desenvolvimento.
    Em produção, deve ser substituída pela chamada real ao modelo.

    Args:
        prompt: Texto de entrada.
        temperature: Parâmetro de temperatura (não utilizado na simulação).

    Returns:
        String simulando uma resposta do modelo.
    """
    await asyncio.sleep(0.1)
    return f"Resposta simulada para: {prompt}"


if __name__ == "__main__":
    async def main():
        responses = await generate_responses(
            prompt="Qual a capital do Brasil Império?",
            model_call=mock_model_call,
            num_responses=5,
        )
        for i, response in enumerate(responses, 1):
            print(f"{i}. {response}")

    asyncio.run(main())
