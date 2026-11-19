"""Copy cron settings into a container-local file.

Hermes removes mailbox, token, and key variables from scheduled-script
processes. The file stays on the container disk, not in the bucket or the image.
"""

from __future__ import annotations

import os
from pathlib import Path

KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "EMAIL_ADDRESS",
    "EMAIL_APP_PASSWORD",
    "EMAIL_IMAP_HOST",
    "EMAIL_IMAP_PORT",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_ALLOWLIST",
    "CALENDAR_ICS_URL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USER_ID",
    "TELEGRAM_ALLOWED_USERS",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "LUMEN_APP",
    "HERMES_HOME",
)


def main() -> None:
    destination = Path(os.environ.get("LUMEN_RUNTIME_ENV", "/home/lumen/lumen-runtime.env"))
    lines = []
    for key in KEYS:
        value = os.environ.get(key, "")
        if not value or "\n" in value or "\r" in value:
            continue
        lines.append(f"{key}={value}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    destination.chmod(0o600)
    print(f"isolation: runtime env written {len(lines)}", flush=True)


if __name__ == "__main__":
    main()
