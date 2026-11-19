"""Load the project .env without printing values."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _apply_env_file(path: Path) -> None:
    """Set missing names from path. Existing variables win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def load_project_env(path: Path = ENV_PATH) -> None:
    """Load the container runtime file, then the project .env. Existing variables win."""
    runtime = Path(os.environ.get("LUMEN_RUNTIME_ENV", "/home/lumen/lumen-runtime.env"))
    _apply_env_file(runtime)
    _apply_env_file(path)


def require(name: str) -> str:
    load_project_env()
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing {name}")
    return value
