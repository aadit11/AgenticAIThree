"""Read mail and store drafts. Sending goes through the approval gate."""

from __future__ import annotations

import argparse
import imaplib
import json
import os
import smtplib
import sys
from email import message_from_bytes
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(os.environ["LUMEN_APP"]) if os.environ.get("LUMEN_APP") else Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from lib.email_gate import consume_approval, decide_send  # noqa: E402
from lib.envfile import load_project_env, require  # noqa: E402

def _drafts_path() -> Path:
    home = os.environ.get("HERMES_HOME", "").strip()
    if os.environ.get("LUMEN_APP") and home:
        return Path(home) / "var" / "drafts.json"
    return ROOT / "var" / "drafts.json"


def owner_ids() -> set[str]:
    load_project_env()
    found = set()
    for name in (
        "TELEGRAM_ALLOWED_USER_ID",
        "TELEGRAM_ALLOWED_USERS",
        "DISCORD_ALLOWED_USER_ID",
        "DISCORD_ALLOWED_USERS",
        "SLACK_ALLOWED_USERS",
    ):
        value = os.environ.get(name, "").strip()
        if value:
            found.add(value.split(",")[0].strip())
    if not found:
        raise SystemExit("missing owner id")
    return found


def allowlist() -> set[str]:
    return {item.strip() for item in require("EMAIL_ALLOWLIST").split(",") if item.strip()}


def load_drafts() -> dict:
    path = _drafts_path()
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_drafts(drafts: dict) -> None:
    path = _drafts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(drafts, indent=2), encoding="utf-8")


def list_fixtures(folder: Path) -> None:
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("*.json"))]
    print(json.dumps(rows, indent=2))


def _mailbox():
    load_project_env()
    host = require("EMAIL_IMAP_HOST")
    port = int(require("EMAIL_IMAP_PORT"))
    mailbox = imaplib.IMAP4_SSL(host, port)
    mailbox.login(require("EMAIL_ADDRESS"), require("EMAIL_APP_PASSWORD").replace(" ", ""))
    mailbox.select("INBOX")
    return mailbox


def _headers(mailbox, criteria: str) -> list[dict]:
    status, data = mailbox.search(None, criteria)
    rows = []
    if status != "OK" or not data or not data[0]:
        return rows
    for number in data[0].split()[-10:]:
        fetched, msg_data = mailbox.fetch(number, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        if fetched != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
            continue
        header = message_from_bytes(msg_data[0][1])
        rows.append({"from": header.get("From", ""), "subject": header.get("Subject", "")})
    return rows


def list_unseen() -> None:
    mailbox = _mailbox()
    payload = {"unseen": _headers(mailbox, "UNSEEN"), "flagged": _headers(mailbox, "FLAGGED")}
    mailbox.logout()
    print(json.dumps(payload, indent=2))


def read_message(subject: str) -> None:
    """Peek one body. The text is returned as data and is not obeyed."""
    mailbox = _mailbox()
    status, data = mailbox.search(None, "SUBJECT", '"%s"' % subject)
    body = ""
    found_subject = ""
    if status == "OK" and data and data[0]:
        number = data[0].split()[-1]
        fetched, msg_data = mailbox.fetch(number, "(BODY.PEEK[])")
        if fetched == "OK" and msg_data and isinstance(msg_data[0], tuple):
            message = message_from_bytes(msg_data[0][1])
            found_subject = message.get("Subject", "")
            body = _body_text(message)
    mailbox.logout()
    print(json.dumps({"subject": found_subject, "body": body, "untrusted": True}, indent=2))


def _body_text(message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    payload = message.get_payload(decode=True) or b""
    if isinstance(payload, bytes):
        charset = message.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    return str(payload)


def deliver(recipient: str, body: str) -> None:
    load_project_env()
    message = EmailMessage()
    message["From"] = require("EMAIL_ADDRESS")
    message["To"] = recipient
    message["Subject"] = "[Lumen fixture] Study block"
    message.set_content(body)
    host = require("EMAIL_SMTP_HOST")
    port = int(require("EMAIL_SMTP_PORT"))
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(require("EMAIL_ADDRESS"), require("EMAIL_APP_PASSWORD").replace(" ", ""))
        smtp.send_message(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("list-fixtures", "list-unseen", "read", "draft", "reject", "decide", "send"))
    parser.add_argument("--subject", default="")
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
    if args.command == "read":
        read_message(args.subject)
        return
    if args.command == "draft":
        drafts = load_drafts()
        drafts[args.draft_id] = {"body": args.body, "recipient": args.recipient, "sent": False}
        save_drafts(drafts)
        print(json.dumps({"draft_id": args.draft_id, "stored": True}))
        return
    if args.command == "reject":
        drafts = load_drafts()
        existed = args.draft_id in drafts
        drafts.pop(args.draft_id, None)
        save_drafts(drafts)
        print(json.dumps({"draft_id": args.draft_id, "discarded": existed}))
        return

    drafts = load_drafts()
    stored = drafts.get(args.draft_id, {})
    recipient = stored.get("recipient", args.recipient)
    if args.command == "decide":
        decision = decide_send(
            draft_id=args.draft_id,
            approval_text=args.text,
            actor_id=args.actor,
            recipient=recipient,
            known_drafts=set(drafts),
            owner_ids=owner_ids(),
            allowlist=allowlist(),
            from_cron=args.from_cron,
        )
        print(json.dumps({"allowed": decision.allowed, "reason": decision.reason}))
        if not decision.allowed:
            raise SystemExit(2)
        return

    decision = consume_approval(
        draft_id=args.draft_id,
        approval_text=args.text,
        actor_id=args.actor,
        recipient=recipient,
        known_drafts=set(drafts),
        owner_ids=owner_ids(),
        allowlist=allowlist(),
        from_cron=args.from_cron,
        already_sent=bool(stored.get("sent")),
    )
    if not decision.allowed:
        print(json.dumps({"allowed": False, "reason": decision.reason, "sent": False}))
        raise SystemExit(2)
    deliver(recipient, stored.get("body", ""))
    stored["sent"] = True
    drafts[args.draft_id] = stored
    save_drafts(drafts)
    print(json.dumps({"allowed": True, "reason": "sent_once", "sent": True}))


if __name__ == "__main__":
    main()
