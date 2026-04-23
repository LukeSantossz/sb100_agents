"""
Executa avaliacao do SB100 contra o dataset de perguntas.

Itera sobre o dataset de perguntas, executa POST /chat para cada uma
com session_id unico (impede contaminacao de historico), e salva as
respostas do SB100 no dataset de resultados.

Uso:
    python eval/run_evaluation.py
    python eval/run_evaluation.py --api-url http://localhost:8000 --concurrent 5
"""

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from tqdm import tqdm

# Configuracoes padrao
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PROFILE = {"name": "eval", "expertise": "intermediate"}
DEFAULT_CONCURRENT = 1  # Requests simultaneos (1 = sequencial)
DEFAULT_TIMEOUT = 300.0  # Timeout por request em segundos (5 min para Ollama local)


async def call_chat_api(
    client: httpx.AsyncClient,
    question: str,
    api_url: str = DEFAULT_API_URL,
) -> dict:
    """
    Executa uma chamada ao endpoint POST /chat.

    Args:
        client: Cliente HTTP async
        question: Texto da pergunta
        api_url: URL base da API

    Returns:
        Resposta da API ou dict com erro
    """
    session_id = str(uuid.uuid4())  # Sessao unica por pergunta

    payload = {
        "session_id": session_id,
        "question": question,
        "profile": DEFAULT_PROFILE,
    }

    try:
        response = await client.post(
            f"{api_url}/chat",
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "success": True,
            "answer": data.get("answer", ""),
            "hallucination_score": data.get("hallucination_score", 0.0),
            "session_id": session_id,
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "answer": f"[HTTP {e.response.status_code}] {e.response.text}",
            "hallucination_score": None,
            "session_id": session_id,
        }
    except Exception as e:
        return {
            "success": False,
            "answer": f"[ERRO] {str(e)}",
            "hallucination_score": None,
            "session_id": session_id,
        }


async def run_evaluation_async(
    questions: list[dict],
    api_url: str = DEFAULT_API_URL,
    concurrent: int = DEFAULT_CONCURRENT,
) -> list[dict]:
    """
    Executa avaliacao de todas as perguntas de forma assincrona.

    Args:
        questions: Lista de objetos question do dataset
        api_url: URL base da API
        concurrent: Numero de requests simultaneos

    Returns:
        Lista de resultados
    """
    results = []
    semaphore = asyncio.Semaphore(concurrent)

    async def process_question(question_obj: dict) -> dict:
        async with semaphore:
            result = await call_chat_api(
                client,
                question_obj["question"],
                api_url,
            )
            return {
                "question_id": question_obj["question_id"],
                "question": question_obj["question"],
                "reference_answers": question_obj.get("reference_answers", []),
                "sb100_answer": result["answer"],
                "sb100_hallucination_score": result["hallucination_score"],
                "sb100_session_id": result["session_id"],
                "sb100_success": result["success"],
            }

    async with httpx.AsyncClient() as client:
        # Verifica se API esta disponivel
        try:
            health = await client.get(f"{api_url}/health", timeout=5.0)
            health.raise_for_status()
            print(f"API disponivel: {api_url}")
        except Exception as e:
            print(f"Erro: API nao disponivel em {api_url}: {e}")
            return []

        # Processa perguntas com barra de progresso
        tasks = [process_question(q) for q in questions]

        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Executando avaliacao",
        ):
            result = await task
            results.append(result)

    # Reordena por question_id para manter ordem original
    results.sort(key=lambda x: x["question_id"])

    return results


def run_evaluation(
    input_path: str = "eval/dataset/reference_answers.json",
    output_path: str = "eval/results/evaluation_results.json",
    api_url: str = DEFAULT_API_URL,
    concurrent: int = DEFAULT_CONCURRENT,
) -> dict:
    """
    Executa avaliacao completa do SB100.

    Args:
        input_path: Caminho do dataset com perguntas e referencias
        output_path: Caminho do arquivo de saida
        api_url: URL base da API
        concurrent: Numero de requests simultaneos

    Returns:
        Dataset de resultados
    """
    # Carrega dataset
    with open(input_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    questions = dataset["questions"]
    print(f"Carregadas {len(questions)} perguntas de {input_path}")
    print(f"API URL: {api_url}")
    print(f"Requests simultaneos: {concurrent}")

    # Executa avaliacao
    results = asyncio.run(
        run_evaluation_async(questions, api_url, concurrent)
    )

    if not results:
        print("Nenhum resultado obtido. Verifique se a API esta disponivel.")
        return {}

    # Estatisticas
    successful = sum(1 for r in results if r["sb100_success"])
    failed = len(results) - successful

    # Monta dataset de resultados
    results_dataset = {
        "metadata": {
            **dataset.get("metadata", {}),
            "evaluation_run_at": datetime.now(timezone.utc).isoformat(),
            "api_url": api_url,
            "total_questions": len(results),
            "successful_requests": successful,
            "failed_requests": failed,
            "profile": DEFAULT_PROFILE,
        },
        "results": results,
    }

    # Salva resultados
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results_dataset, f, ensure_ascii=False, indent=2)

    print(f"\nResultados salvos em: {output}")
    print(f"Requests bem-sucedidos: {successful}/{len(results)}")
    if failed > 0:
        print(f"Requests com erro: {failed}")

    return results_dataset


def main():
    parser = argparse.ArgumentParser(
        description="Executa avaliacao do SB100 contra o dataset de perguntas"
    )
    parser.add_argument(
        "--input",
        default="eval/dataset/reference_answers.json",
        help="Caminho do dataset com referencias (padrao: eval/dataset/reference_answers.json)",
    )
    parser.add_argument(
        "--output",
        default="eval/results/evaluation_results.json",
        help="Caminho do arquivo de saida (padrao: eval/results/evaluation_results.json)",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"URL base da API (padrao: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT,
        help=f"Requests simultaneos (padrao: {DEFAULT_CONCURRENT})",
    )

    args = parser.parse_args()

    # Verifica se arquivo de entrada existe
    if not Path(args.input).exists():
        print(f"Erro: Arquivo de entrada nao encontrado: {args.input}")
        print("Execute primeiro:")
        print("  1. python eval/generate_questions.py <documento>")
        print("  2. python eval/collect_references.py")
        return 1

    # Executa avaliacao
    result = run_evaluation(
        input_path=args.input,
        output_path=args.output,
        api_url=args.api_url,
        concurrent=args.concurrent,
    )

    return 0 if result else 1


if __name__ == "__main__":
    exit(main())
