"""Read mail and store drafts. Sending goes through the approval gate."""

from __future__ import annotations

import argparse
import imaplib
import json
import sys
from email import message_from_bytes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from lib.email_gate import decide_send  # noqa: E402
from lib.envfile import load_project_env, require  # noqa: E402

DRAFTS = ROOT / "var" / "drafts.json"


def owner_ids() -> set[str]:
    load_project_env()
    names = ("TELEGRAM_ALLOWED_USER_ID", "DISCORD_ALLOWED_USER_ID", "SLACK_ALLOWED_USERS")
    return {require(name) for name in names}


def allowlist() -> set[str]:
    return {item.strip() for item in require("EMAIL_ALLOWLIST").split(",") if item.strip()}


def load_drafts() -> dict:
    if not DRAFTS.is_file():
        return {}
    return json.loads(DRAFTS.read_text(encoding="utf-8"))


def save_drafts(drafts: dict) -> None:
    DRAFTS.parent.mkdir(parents=True, exist_ok=True)
    DRAFTS.write_text(json.dumps(drafts, indent=2), encoding="utf-8")


def list_fixtures(folder: Path) -> None:
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json"))]
    print(json.dumps(rows, indent=2))


def list_unseen() -> None:
    load_project_env()
    host = require("EMAIL_IMAP_HOST")
    port = int(require("EMAIL_IMAP_PORT"))
    mailbox = imaplib.IMAP4_SSL(host, port)
    mailbox.login(require("EMAIL_ADDRESS"), require("EMAIL_APP_PASSWORD"))
    mailbox.select("INBOX")
    status, data = mailbox.search(None, "UNSEEN")
    rows = []
    if status == "OK":
        for number in data[0].split()[-10:]:
            fetched, msg_data = mailbox.fetch(number, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if fetched != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            header = message_from_bytes(msg_data[0][1])
            rows.append({"from": header.get("From", ""), "subject": header.get("Subject", "")})
    mailbox.logout()
    print(json.dumps(rows, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("list-fixtures", "list-unseen", "draft", "decide"))
    parser.add_argument("--draft-id", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--recipient", default="")
    parser.add_argument("--from-cron", action="store_true")
    args = parser.parse_args()

    if args.command == "list-fixtures":
        list_fixtures(ROOT / "synthetic" / "emails")
        return
    if args.command == "list-unseen":
        list_unseen()
        return
    if args.command == "draft":
        drafts = load_drafts()
        drafts[args.draft_id] = {"body": args.body, "recipient": args.recipient}
        save_drafts(drafts)
        print(json.dumps({"draft_id": args.draft_id, "stored": True}))
        return

    drafts = load_drafts()
    decision = decide_send(
        draft_id=args.draft_id,
        approval_text=args.text,
        actor_id=args.actor,
        recipient=args.recipient,
        known_drafts=set(drafts),
        owner_ids=owner_ids(),
        allowlist=allowlist(),
        from_cron=args.from_cron,
    )
    print(json.dumps({"allowed": decision.allowed, "reason": decision.reason}))
    if not decision.allowed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
