"""Create the registry, bucket, and Secret Manager entries. Values are not printed."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GCLOUD = r"C:\Users\hp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, input=stdin, capture_output=True, text=True)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "command failed").strip()
        raise SystemExit(args[0] + " " + args[1] + " failed: " + message.splitlines()[-1][:180])
    return completed


def ensure_secret(name: str, value: str) -> None:
    if not value:
        raise SystemExit("missing value for " + name)
    exists = subprocess.run([GCLOUD, "secrets", "describe", name], capture_output=True, text=True)
    if exists.returncode != 0:
        run([GCLOUD, "secrets", "create", name, "--replication-policy=automatic"])
    run([GCLOUD, "secrets", "versions", "add", name, "--data-file=-"], stdin=value)


def main() -> None:
    values = env_values()
    project = run([GCLOUD, "config", "get-value", "project"]).stdout.strip()
    number = run([GCLOUD, "projects", "describe", project, "--format=value(projectNumber)"]).stdout.strip()
    account = f"{number}-compute@developer.gserviceaccount.com"
    bucket = f"lumen-home-{project}"
    region = values.get("GCP_REGION") or "us-west1"

    run([GCLOUD, "services", "enable", "artifactregistry.googleapis.com", "secretmanager.googleapis.com", "storage.googleapis.com", "run.googleapis.com"])
    repo = subprocess.run(
        [GCLOUD, "artifacts", "repositories", "describe", "lumen", "--location", region],
        capture_output=True,
        text=True,
    )
    if repo.returncode != 0:
        run(
            [
                GCLOUD,
                "artifacts",
                "repositories",
                "create",
                "lumen",
                "--repository-format=docker",
                "--location",
                region,
                "--description=Lumen assignment images",
            ]
        )
    bucket_exists = subprocess.run([GCLOUD, "storage", "buckets", "describe", f"gs://{bucket}"], capture_output=True, text=True)
    if bucket_exists.returncode != 0:
        run([GCLOUD, "storage", "buckets", "create", f"gs://{bucket}", "--location", region, "--uniform-bucket-level-access"])
    run(
        [
            GCLOUD,
            "storage",
            "buckets",
            "add-iam-policy-binding",
            f"gs://{bucket}",
            f"--member=serviceAccount:{account}",
            "--role=roles/storage.objectAdmin",
        ]
    )

    secrets = {
        "lumen-openai-api-key": values["OPENAI_API_KEY"],
        "lumen-telegram-bot-token": values["TELEGRAM_BOT_TOKEN"],
        "lumen-telegram-allowed-users": values["TELEGRAM_ALLOWED_USER_ID"],
        "lumen-discord-bot-token": values["DISCORD_BOT_TOKEN"],
        "lumen-discord-allowed-users": values["DISCORD_ALLOWED_USER_ID"],
        "lumen-slack-bot-token": values["SLACK_BOT_TOKEN"],
        "lumen-slack-app-token": values["SLACK_APP_TOKEN"],
        "lumen-slack-allowed-users": values["SLACK_ALLOWED_USERS"],
        "lumen-slack-home-channel": values["SLACK_HOME_CHANNEL"],
        "lumen-gateway-key": values["HERMES_GATEWAY_KEY"],
        "lumen-calendar-ics-url": values["CALENDAR_ICS_URL"],
        "lumen-email-app-password": values["EMAIL_APP_PASSWORD"],
    }
    for name, value in secrets.items():
        ensure_secret(name, value)
        run(
            [
                GCLOUD,
                "secrets",
                "add-iam-policy-binding",
                name,
                f"--member=serviceAccount:{account}",
                "--role=roles/secretmanager.secretAccessor",
            ]
        )
    print("cloud-ready")
    print("region", region)
    print("bucket-suffix", bucket.removeprefix("lumen-home-")[:4])
    print("secrets", len(secrets))


if __name__ == "__main__":
    main()
