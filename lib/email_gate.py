"""Human approval gate for sending mail. The model cannot bypass this module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def decide_send(
    *,
    draft_id: str,
    approval_text: str,
    actor_id: str,
    recipient: str,
    known_drafts: set[str],
    owner_ids: set[str],
    allowlist: set[str],
    from_cron: bool = False,
) -> Decision:
    """Allow a send only for an owner approval of a real draft to an allowlisted recipient."""
    if from_cron:
        return Decision(False, "cron_cannot_send")
    expected = f"APPROVE {draft_id}"
    if approval_text.strip() != expected:
        return Decision(False, "approval_required")
    if actor_id not in owner_ids:
        return Decision(False, "owner_required")
    if recipient.lower() not in {item.lower() for item in allowlist}:
        return Decision(False, "recipient_not_allowlisted")
    if draft_id not in known_drafts:
        return Decision(False, "unknown_draft")
    return Decision(True, "approved")


def consume_approval(
    *,
    draft_id: str,
    approval_text: str,
    actor_id: str,
    recipient: str,
    known_drafts: set[str],
    owner_ids: set[str],
    allowlist: set[str],
    from_cron: bool = False,
    already_sent: bool = False,
) -> Decision:
    """Same gate as decide_send, and a draft that already went out cannot go again."""
    if already_sent:
        return Decision(False, "already_sent")
    return decide_send(
        draft_id=draft_id,
        approval_text=approval_text,
        actor_id=actor_id,
        recipient=recipient,
        known_drafts=known_drafts,
        owner_ids=owner_ids,
        allowlist=allowlist,
        from_cron=from_cron,
    )
