"""Push the local image and deploy the Cloud Run instance. Secret values are not printed."""

from __future__ import annotations

import subprocess
import sys
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
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, capture_output=True, text=True)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "command failed").strip()
        raise SystemExit(args[1] + " " + args[2] + " failed: " + message.splitlines()[-1][:180])
    return completed


def cloud() -> tuple[str, str, str, str]:
    values = env_values()
    project = run([GCLOUD, "config", "get-value", "project"]).stdout.strip()
    number = run([GCLOUD, "projects", "describe", project, "--format=value(projectNumber)"]).stdout.strip()
    region = values.get("GCP_REGION") or "us-west1"
    image = f"{region}-docker.pkg.dev/{project}/lumen/lumen:phase6"
    return project, number, region, image


def push(image: str, region: str) -> None:
    run([GCLOUD, "auth", "configure-docker", f"{region}-docker.pkg.dev", "--quiet"])
    run(["docker", "tag", "lumen:phase6", image])
    run(["docker", "push", image])
    digest = run(
        [
            GCLOUD,
            "artifacts",
            "docker",
            "images",
            "describe",
            image,
            "--format=value(image_summary.digest)",
        ]
    )
    print("pushed")
    print(digest.stdout.strip())


def deploy(number: str, region: str, image: str, values: dict[str, str]) -> None:
    account = f"{number}-compute@developer.gserviceaccount.com"
    project = run([GCLOUD, "config", "get-value", "project"]).stdout.strip()
    bucket = f"lumen-home-{project}"
    digest = run(
        [GCLOUD, "artifacts", "docker", "images", "describe", image, "--format=value(image_summary.digest)"]
    ).stdout.strip()
    image = f"{image}@{digest}"
    plain = {
        "HERMES_HOME": "/hermes",
        "HOME": "/home/lumen",
        "LUMEN_APP": "/opt/lumen/app",
        "HERMES_PORT": "8081",
        "LUMEN_RUNTIME_ENV": "/home/lumen/lumen-runtime.env",
        "API_SERVER_ENABLED": "true",
        "API_SERVER_HOST": "127.0.0.1",
        "API_SERVER_PORT": "8081",
        "PYTHONUNBUFFERED": "1",
        "HERMES_TELEGRAM_DISABLE_FALLBACK_IPS": "1",
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_MODEL": values.get("OLLAMA_MODEL") or "gemma4:e2b",
        "OLLAMA_UPSTREAM": _ollama_upstream(),
        "OPENAI_MODEL": values.get("OPENAI_MODEL") or "gpt-6.1-sol",
        "EMAIL_ADDRESS": values["EMAIL_ADDRESS"],
        "EMAIL_IMAP_HOST": values.get("EMAIL_IMAP_HOST") or "imap.gmail.com",
        "EMAIL_IMAP_PORT": values.get("EMAIL_IMAP_PORT") or "993",
        "EMAIL_SMTP_HOST": values.get("EMAIL_SMTP_HOST") or "smtp.gmail.com",
        "EMAIL_SMTP_PORT": values.get("EMAIL_SMTP_PORT") or "587",
        "EMAIL_ALLOWLIST": values["EMAIL_ALLOWLIST"],
    }
    env_arg = "^|^" + "|".join(f"{key}={value}" for key, value in plain.items())
    secrets = ",".join(
        [
            "OPENAI_API_KEY=lumen-openai-api-key:latest",
            "TELEGRAM_BOT_TOKEN=lumen-telegram-bot-token:latest",
            "TELEGRAM_ALLOWED_USERS=lumen-telegram-allowed-users:latest",
            "DISCORD_BOT_TOKEN=lumen-discord-bot-token:latest",
            "DISCORD_ALLOWED_USERS=lumen-discord-allowed-users:latest",
            "SLACK_BOT_TOKEN=lumen-slack-bot-token:latest",
            "SLACK_APP_TOKEN=lumen-slack-app-token:latest",
            "SLACK_ALLOWED_USERS=lumen-slack-allowed-users:latest",
            "SLACK_HOME_CHANNEL=lumen-slack-home-channel:latest",
            "API_SERVER_KEY=lumen-gateway-key:latest",
            "CALENDAR_ICS_URL=lumen-calendar-ics-url:latest",
            "EMAIL_APP_PASSWORD=lumen-email-app-password:latest",
            "TAILSCALE_AUTHKEY=lumen-tailscale-authkey:latest",
        ]
    )
    flags = Path(r"C:\Users\hp\AppData\Local\Temp\lumen-deploy-flags.yaml")
    flags.write_text(
        "\n".join(
            [
                f"--image: {image}",
                "--cpu: '1'",
                "--memory: 1Gi",
                "--port: '8080'",
                "--restart-policy: always",
                "--public:",
                f"--region: {region}",
                f"--service-account: {account}",
                "--add-volume:",
                "  type: cloud-storage",
                f"  bucket: {bucket}",
                "  mount-path: /hermes",
                "  mount-options: uid=10001;gid=10001",
                f"--update-env-vars: {json_quote(env_arg)}",
                f"--set-secrets: {json_quote(secrets)}",
                "--startup-probe: initialDelaySeconds=20,timeoutSeconds=5,periodSeconds=10,failureThreshold=30,httpGet.port=8080,httpGet.path=/health",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        completed = run(
            [
                GCLOUD,
                "beta",
                "run",
                "instances",
                "deploy",
                "lumen",
                f"--flags-file={flags}",
                "--format=value(status.uri)",
            ]
        )
    finally:
        flags.unlink(missing_ok=True)
    print("deployed")
    print(completed.stdout.strip())


def _ollama_upstream() -> str:
    completed = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
    address = completed.stdout.strip().splitlines()[0] if completed.returncode == 0 else ""
    if not address:
        raise SystemExit("tailscale ip failed")
    return address + ":11434"


def json_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "push"
    _project, number, region, image = cloud()
    if action == "push":
        push(image, region)
        return
    if action == "deploy":
        deploy(number, region, image, env_values())
        return
    raise SystemExit("use push or deploy")


if __name__ == "__main__":
    main()
