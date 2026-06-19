"""THROWAWAY go/no-go spike (SPEC: chore(agent) substrate spike, issue #163).

Proves a hosted Groq model can drive a LangChain deepagents loop: the model must
call the ``search_corpus`` tool and ground its answer in the returned chunks.

A canned corpus is used on purpose so the go/no-go needs ONLY a Groq key
(no Qdrant / Docker / indexing). Real Qdrant retrieval is wired in a later slice.

Run:
    # free key at https://console.groq.com
    $env:GROQ_API_KEY = "gsk_..."      # PowerShell
    uv run python spikes/deepagents_smoke.py

This file is throwaway and is removed before merge; the durable A0 outputs are the
pinned dependencies and the two ADRs.
"""

import os
import sys

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()  # read GROQ_API_KEY from a local .env (gitignored)
sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crashes on Windows consoles

# openai/gpt-oss-20b issues valid tool calls on Groq; llama-3.3-70b-versatile does NOT
# (it emits malformed function-call syntax -> tool_use_failed). See SPEC.md / ADR-0009.
MODEL = os.environ.get("SPIKE_GROQ_MODEL", "openai/gpt-oss-20b")

# Canned corpus (stands in for Qdrant) so the spike isolates the one open question:
# can a hosted Groq model drive the deepagents tool loop and ground its answer?
_CHUNKS = (
    "[smart_boletim.pdf] A janela ideal de plantio da soja na regiao Centro-Oeste vai "
    "de meados de outubro a meados de novembro, apos o inicio regular das chuvas e com "
    "a temperatura do solo acima de 20 C.\n\n"
    "[smart_boletim.pdf] O espacamento entre linhas recomendado para a soja varia de "
    "0,45 m a 0,50 m, com densidade de 12 a 15 plantas por metro."
)


def search_corpus(query: str) -> str:
    """Search the agricultural manual corpus and return the most relevant chunks.

    Use this for ANY question about agronomy, crops, planting, soil, or pests.

    Args:
        query: the user's information need, in natural language.
    """
    # Spike stub: returns the canned chunks regardless of query (grounding test).
    return _CHUNKS


SYSTEM_PROMPT = (
    "You are an agronomy assistant. You MUST call the search_corpus tool before "
    "answering, and answer ONLY from the chunks it returns. If the chunks do not "
    "contain the answer, say so. Cite the source file in brackets. "
    "Always respond in the language of the question."
)


def main() -> None:
    real_key = os.environ.get("GROQ_API_KEY")
    if not real_key:
        # Allow a build-only wiring check without a key (no model call is made).
        os.environ["GROQ_API_KEY"] = "PLACEHOLDER_BUILD_ONLY"

    model = ChatGroq(model=MODEL, temperature=0)
    agent = create_deep_agent(
        model=model,
        tools=[search_corpus],
        system_prompt=SYSTEM_PROMPT,
    )
    print(f"WIRING OK: deepagents + langchain-groq; agent graph compiled (model={MODEL}).")

    if not real_key:
        print("NO GROQ_API_KEY set -> skipping live invoke. Set it to run the go/no-go.")
        return

    question = "Qual a epoca ideal de plantio da soja e o espacamento recomendado?"
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result["messages"]
    tool_calls = [
        call["name"]
        for message in messages
        for call in (getattr(message, "tool_calls", None) or [])
    ]
    print(f"TOOL CALLS: {tool_calls}")
    print(f"FINAL ANSWER:\n{messages[-1].content}")


if __name__ == "__main__":
    main()
