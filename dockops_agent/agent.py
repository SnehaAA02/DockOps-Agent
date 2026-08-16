"""
DockOps Agent — an LLM-powered assistant for inspecting and managing local
Docker containers, backed by a locally-running Ollama model.

Usage:
    python -m dockops_agent.agent                     # interactive REPL
    python -m dockops_agent.agent -q "list containers" # single-shot query
"""

from __future__ import annotations

import argparse
import logging
import sys

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from dockops_agent.config import settings
from dockops_agent.tools.docker_tools import ALL_TOOLS

SYSTEM_PROMPT = (
    "You are DockOps, a helpful assistant that manages Docker containers on "
    "the user's machine. Use the available tools to answer questions about "
    "running containers, logs, images, and resource usage, and to start or "
    "stop containers when asked. Always confirm the action you took and "
    "summarize tool output clearly and concisely. If a tool reports an "
    "error, explain it in plain language rather than showing a raw stack trace."
)


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_agent():
    """Constructs the LangChain agent bound to the local Ollama model."""
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=settings.temperature,
    )
    return create_agent(model=llm, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


def ask(agent, question: str) -> str:
    """Sends one question to the agent and returns its final text reply."""
    response = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return response["messages"][-1].content


def run_single_shot(agent, query: str) -> None:
    print(ask(agent, query))


def run_interactive(agent) -> None:
    print("DockOps Agent — type a request, or 'exit'/'quit' to stop.")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        try:
            print(ask(agent, question))
        except Exception as exc:
            logging.getLogger(__name__).exception("Agent invocation failed")
            print(f"Something went wrong handling that request: {exc}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM-powered Docker container assistant.")
    parser.add_argument(
        "-q", "--query",
        help="Run a single query and exit, instead of the interactive REPL.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(argv)

    try:
        agent = build_agent()
    except Exception as exc:
        logging.getLogger(__name__).exception("Failed to initialize the agent")
        print(
            f"Could not start the agent: {exc}\n"
            f"Check that Ollama is running at {settings.ollama_base_url} "
            f"and that the model '{settings.ollama_model}' is pulled."
        )
        return 1

    if args.query:
        run_single_shot(agent, args.query)
    else:
        run_interactive(agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
