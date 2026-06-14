"""
Run the SB100 evaluation against the question dataset.

Iterates over the question dataset, calls POST /chat for each question
with a unique session_id (prevents history contamination), and saves
the SB100 answers to the results dataset.

Supports checkpointing: every `CHECKPOINT_EVERY` results, partial state
is persisted to `evaluation_checkpoint.json`. If interrupted, the next
run resumes only the pending questions.

Usage:
    python eval/run_evaluation.py
    python eval/run_evaluation.py --api-url http://localhost:8000 --concurrent 5
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from tqdm import tqdm

# Allow `from eval._utils import ...` when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval._utils import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_EVAL_RESULTS_PATH,
    DEFAULT_REFERENCES_PATH,
    validate_dataset_schema,
)

# Default settings
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PROFILE = {"name": "eval", "expertise": "intermediate"}
DEFAULT_CONCURRENT = 1  # Concurrent requests (1 = sequential)
DEFAULT_TIMEOUT = 300.0  # Per-request timeout in seconds (5 min for local Ollama)
CHECKPOINT_EVERY = 10  # Persist partial state every N results
AUTH_TIMEOUT = 30.0  # Timeout for the one-time /auth/token exchange


class EvalAuthError(Exception):
    """Raised when evaluation credentials are missing or rejected."""


async def resolve_token(client: httpx.AsyncClient, api_url: str = DEFAULT_API_URL) -> str:
    """Resolve a bearer token for /chat from the environment.

    Uses ``EVAL_API_TOKEN`` directly when set; otherwise exchanges
    ``EVAL_USERNAME``/``EVAL_PASSWORD`` for a token via ``POST /auth/token``.

    Args:
        client: Async HTTP client.
        api_url: API base URL.

    Returns:
        A bearer token string.

    Raises:
        EvalAuthError: if no credentials are configured or the exchange fails.
    """
    explicit = os.getenv("EVAL_API_TOKEN")
    if explicit:
        return explicit

    username = os.getenv("EVAL_USERNAME")
    password = os.getenv("EVAL_PASSWORD")
    if not username or not password:
        raise EvalAuthError(
            "No evaluation credentials configured. Set EVAL_API_TOKEN, or "
            "EVAL_USERNAME and EVAL_PASSWORD, to authenticate against /chat."
        )

    try:
        response = await client.post(
            f"{api_url}/auth/token",
            data={"username": username, "password": password},
            timeout=AUTH_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise EvalAuthError(
            f"Authentication failed (HTTP {e.response.status_code}). "
            "Check EVAL_USERNAME/EVAL_PASSWORD for a registered evaluation user."
        ) from e
    except httpx.RequestError as e:
        raise EvalAuthError(f"Could not reach {api_url}/auth/token to authenticate: {e}") from e

    return response.json()["access_token"]


async def call_chat_api(
    client: httpx.AsyncClient,
    question: str,
    api_url: str = DEFAULT_API_URL,
    *,
    token: str,
) -> dict:
    """
    Make a single call to the POST /chat endpoint.

    Args:
        client: Async HTTP client
        question: Question text
        api_url: API base URL
        token: Bearer token sent in the Authorization header

    Returns:
        API response or an error dict
    """
    session_id = str(uuid.uuid4())  # Unique session per question

    payload = {
        "session_id": session_id,
        "question": question,
        "profile": DEFAULT_PROFILE,
    }

    try:
        response = await client.post(
            f"{api_url}/chat",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
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
            "answer": f"[ERROR] {str(e)}",
            "hallucination_score": None,
            "session_id": session_id,
        }


def load_checkpoint(checkpoint_path: Path) -> list[dict]:
    """Load partial results from a checkpoint, if it exists.

    Returns an empty list if the checkpoint is missing or corrupted.
    """
    if not checkpoint_path.exists():
        return []
    try:
        with open(checkpoint_path, encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", [])
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict) and "question_id" in r]
        return []
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: corrupted checkpoint ({e}); ignoring")
        return []


def save_checkpoint(checkpoint_path: Path, results: list[dict]) -> None:
    """Persist partial results atomically.

    Writes to `.tmp` and renames, preventing corruption if interrupted
    mid-write.
    """
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, ensure_ascii=False, indent=2)
    tmp.replace(checkpoint_path)


async def run_evaluation_async(
    questions: list[dict],
    api_url: str = DEFAULT_API_URL,
    concurrent: int = DEFAULT_CONCURRENT,
    checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH,
    checkpoint_every: int = CHECKPOINT_EVERY,
) -> list[dict]:
    """
    Evaluate every question asynchronously, persisting progress
    incrementally via checkpoint.

    Args:
        questions: List of question objects from the dataset
        api_url: API base URL
        concurrent: Number of concurrent requests
        checkpoint_path: File for writing partial progress
        checkpoint_every: Flush interval (in completed results)

    Returns:
        List of results (existing from checkpoint + new)
    """
    existing = load_checkpoint(checkpoint_path)
    completed_ids = {r["question_id"] for r in existing}
    pending = [q for q in questions if q["question_id"] not in completed_ids]

    if existing:
        print(
            f"Checkpoint found at {checkpoint_path}: "
            f"{len(existing)} results already processed; "
            f"resuming {len(pending)} pending"
        )

    results: list[dict] = list(existing)

    if not pending:
        print("No pending questions.")
        return results

    semaphore = asyncio.Semaphore(concurrent)

    async def process_question(question_obj: dict, client: httpx.AsyncClient, token: str) -> dict:
        async with semaphore:
            result = await call_chat_api(
                client,
                question_obj["question"],
                api_url,
                token=token,
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
        # Authenticate before any /chat work; abort fast (EvalAuthError) when
        # credentials are missing or rejected, so a run never silently produces
        # 401-only results.
        token = await resolve_token(client, api_url)

        # Check that the API is available
        try:
            health = await client.get(f"{api_url}/health", timeout=5.0)
            health.raise_for_status()
            print(f"API available: {api_url}")
        except Exception as e:
            print(f"Error: API not available at {api_url}: {e}")
            return results

        # Process questions with a progress bar
        tasks = [process_question(q, client, token) for q in pending]
        new_since_checkpoint = 0

        for task in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc="Running evaluation",
        ):
            result = await task
            results.append(result)
            new_since_checkpoint += 1

            if new_since_checkpoint >= checkpoint_every:
                save_checkpoint(checkpoint_path, results)
                new_since_checkpoint = 0

    # Sort by question_id to keep the original order
    results.sort(key=lambda x: x["question_id"])

    return results


def run_evaluation(
    input_path: str = str(DEFAULT_REFERENCES_PATH),
    output_path: str = str(DEFAULT_EVAL_RESULTS_PATH),
    api_url: str = DEFAULT_API_URL,
    concurrent: int = DEFAULT_CONCURRENT,
    checkpoint_path: str | None = None,
) -> dict:
    """
    Run the full SB100 evaluation.

    Args:
        input_path: Path to the dataset with questions and references
        output_path: Path to the output file
        api_url: API base URL
        concurrent: Number of concurrent requests
        checkpoint_path: Checkpoint path (default: DEFAULT_CHECKPOINT_PATH)

    Returns:
        Results dataset
    """
    checkpoint = Path(checkpoint_path) if checkpoint_path else DEFAULT_CHECKPOINT_PATH

    # Load dataset
    with open(input_path, encoding="utf-8") as f:
        dataset = json.load(f)

    validate_dataset_schema(dataset, ["metadata", "questions"])

    questions = dataset["questions"]
    print(f"Loaded {len(questions)} questions from {input_path}")
    print(f"API URL: {api_url}")
    print(f"Concurrent requests: {concurrent}")
    print(f"Checkpoint: {checkpoint} (every {CHECKPOINT_EVERY} results)")

    # Run evaluation
    results = asyncio.run(run_evaluation_async(questions, api_url, concurrent, checkpoint))

    if not results:
        print("No results obtained. Check that the API is available.")
        return {}

    # Statistics
    successful = sum(1 for r in results if r["sb100_success"])
    failed = len(results) - successful

    # Build results dataset
    results_dataset = {
        "metadata": {
            **dataset.get("metadata", {}),
            "evaluation_run_at": datetime.now(UTC).isoformat(),
            "api_url": api_url,
            "total_questions": len(results),
            "successful_requests": successful,
            "failed_requests": failed,
            "profile": DEFAULT_PROFILE,
        },
        "results": results,
    }

    # Save results
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results_dataset, f, ensure_ascii=False, indent=2)

    # Remove checkpoint on successful completion
    if checkpoint.exists():
        checkpoint.unlink()

    print(f"\nResults saved to: {output}")
    print(f"Successful requests: {successful}/{len(results)}")
    if failed > 0:
        print(f"Failed requests: {failed}")

    return results_dataset


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the SB100 evaluation against the question dataset"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_REFERENCES_PATH),
        help=f"Path to the dataset with references (default: {DEFAULT_REFERENCES_PATH})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_EVAL_RESULTS_PATH),
        help=f"Path to the output file (default: {DEFAULT_EVAL_RESULTS_PATH})",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT,
        help=f"Concurrent requests (default: {DEFAULT_CONCURRENT})",
    )
    parser.add_argument(
        "--checkpoint",
        default=str(DEFAULT_CHECKPOINT_PATH),
        help=f"Checkpoint file (default: {DEFAULT_CHECKPOINT_PATH})",
    )

    args = parser.parse_args()

    # Check that the input file exists
    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}")
        print("Run first:")
        print("  1. python eval/generate_questions.py <document>")
        print("  2. python eval/collect_references.py")
        return 1

    # Run evaluation
    try:
        result = run_evaluation(
            input_path=args.input,
            output_path=args.output,
            api_url=args.api_url,
            concurrent=args.concurrent,
            checkpoint_path=args.checkpoint,
        )
    except EvalAuthError as e:
        print(f"Error: {e}")
        return 1

    return 0 if result else 1


if __name__ == "__main__":
    exit(main())
