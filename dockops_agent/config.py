"""
Centralized configuration for the DockOps Agent.

All settings are environment-driven so the same code runs unmodified across
dev machines, CI, and containers. Falls back to sane defaults if unset.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    temperature: float = _get_float("OLLAMA_TEMPERATURE", 0.3)
    command_timeout_seconds: int = _get_int("DOCKER_CMD_TIMEOUT", 15)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
