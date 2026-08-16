"""
Docker tool functions exposed to the LangChain agent.

Design notes:
- Every subprocess call uses list-form args (never shell=True), so there is
  no shell-injection surface even though input ultimately comes from an LLM.
- Container/image identifiers are validated against Docker's own naming
  rules before being used, as defense in depth.
- Every tool returns a string (LLMs can only reason over text) and never
  raises — failures are caught and turned into a readable message so the
  agent can react intelligently instead of crashing.
"""

from __future__ import annotations

import logging
import re
import subprocess

from langchain_core.tools import tool

from dockops_agent.config import settings

logger = logging.getLogger(__name__)

# Docker allows [a-zA-Z0-9][a-zA-Z0-9_.-]* for container/image names.
_VALID_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


def _run(args: list[str]) -> subprocess.CompletedProcess:
    logger.info("Executing: %s", " ".join(args))
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=settings.command_timeout_seconds,
        check=True,
    )


def _validate_identifier(identifier: str) -> str | None:
    """Returns an error message if invalid, otherwise None."""
    if not _VALID_NAME.match(identifier):
        return (
            f"'{identifier}' is not a valid Docker container/image name. "
            "Refusing to execute."
        )
    return None


def _safe_execute(args: list[str], empty_message: str) -> str:
    try:
        result = _run(args)
        output = result.stdout.strip()
        return output or empty_message
    except FileNotFoundError:
        return "Docker is not installed or not available on PATH."
    except subprocess.TimeoutExpired:
        return f"Command timed out after {settings.command_timeout_seconds}s."
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        return f"Docker command failed: {stderr}"
    except Exception as exc:  # last-resort guard so the agent never crashes
        logger.exception("Unexpected error running docker command")
        return f"Unexpected error: {exc}"


@tool
def list_containers(show_all: bool = False) -> str:
    """List Docker containers. Set show_all=True to include stopped containers,
    otherwise only running containers are shown."""
    args = ["docker", "ps"] + (["-a"] if show_all else [])
    return _safe_execute(args, "No containers found.")


@tool
def container_logs(container_name: str, tail_lines: int = 50) -> str:
    """Fetch the most recent logs for a specific container.
    container_name: exact container name or ID.
    tail_lines: number of lines to fetch from the end of the log (default 50)."""
    if error := _validate_identifier(container_name):
        return error
    tail_lines = max(1, min(tail_lines, 1000))  # clamp to a sane range
    args = ["docker", "logs", "--tail", str(tail_lines), container_name]
    return _safe_execute(args, "No log output for this container.")


@tool
def start_container(container_name: str) -> str:
    """Start a stopped Docker container by name or ID."""
    if error := _validate_identifier(container_name):
        return error
    args = ["docker", "start", container_name]
    return _safe_execute(args, f"Container '{container_name}' did not report a status.")


@tool
def stop_container(container_name: str) -> str:
    """Stop a running Docker container by name or ID."""
    if error := _validate_identifier(container_name):
        return error
    args = ["docker", "stop", container_name]
    return _safe_execute(args, f"Container '{container_name}' did not report a status.")


@tool
def container_stats() -> str:
    """Get a live-resource snapshot (CPU, memory, network I/O) for all
    running containers, similar to `docker stats --no-stream`."""
    args = ["docker", "stats", "--no-stream"]
    return _safe_execute(args, "No running containers to report stats for.")


@tool
def list_images() -> str:
    """List Docker images available locally."""
    args = ["docker", "images"]
    return _safe_execute(args, "No local images found.")


ALL_TOOLS = [
    list_containers,
    container_logs,
    start_container,
    stop_container,
    container_stats,
    list_images,
]
