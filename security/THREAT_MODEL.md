# Security audit

Recorded 15 November 2026, before the graded 48-hour window. Lumen runs as Hermes 0.20.5 in a Cloud Run Instance. The container user is `lumen`, uid 10001. Startup logs `privileged=false` and an effective capability set of 0.

Container isolation is one measure. Three more are in the running system: Secret Manager for credentials, a human send gate with a recipient allowlist, and prompt-injection handling. The injection results are in `injection-tests.md`.

## Measures

**Container isolation.** `deploy/Dockerfile` builds `python:3.11-slim-bookworm`, creates uid 10001, and sets `USER lumen`. The image does not request privileged mode. `deploy/isolation-report.sh` prints the user, uid, gid, and capability lines at every boot and does not print environment values. The 14 November startup log recorded uid 10001 and `CapEff` 0.

**Credential management.** Bot tokens, the OpenAI key, the mailbox app password, the calendar URL, the Tailscale auth key, and `API_SERVER_KEY` are Cloud Run secrets. `.env` is gitignored. `.env.example` has empty values. The runtime file written at boot stays on the container disk at mode 600 and is not copied to the bucket. Router logs omit message text.

**Human approval for send.** `lib/email_gate.py` allows a send only when the actor is an owner, the text is exactly `APPROVE <draft-id>`, the draft exists, and the recipient is on the allowlist. A draft that already went out cannot go again. `from_cron=True` returns `cron_cannot_send` even if the other checks would pass. The grader web chat has no approval buttons. The `web-approval` plugin blocks a send, and any shell command Hermes would stop for approval, when the session platform is `api_server`.

**Prompt-injection defense.** Email reads return the body with `untrusted: true`. Search snippets are the same kind of data. The send function does not treat text inside a message as an approval.

## Risks

| Risk | What is in place | What remains |
|---|---|---|
| Instructions hidden in email or search results | Bodies and snippets are marked untrusted. The send gate ignores that text. Three attacks were refused on 15 November. | A future tool that treats tool output as instructions would bypass this. The current send path does not. |
| Secrets in git, the image, or logs | Secret Manager, `.gitignore`, and logs that omit tokens and message text. | A person who can read the Cloud Run environment or the bucket can still read the mounted Hermes home. The home is not a secret store. |
| Mail sent without the owner | Exact `APPROVE <draft-id>`, owner id, allowlist, one-time draft, cron refusal, web-chat block. | Someone who already controls the owner's Telegram, Discord, or Slack account can approve a send. That person is the intended human. |
| Ollama reachable off this PC | Ollama listens on `127.0.0.1:11434`. Tailscale Serve is the remote path. A connection to the PC's ordinary network address on port 11434 was refused on 15 November. | The laptop must be awake for local inference. When it is not, short and private tasks go to `gpt-6.1-sol` and the log reason is `local_unavailable`. |
| Concurrent writes corrupt memory | Chat and jobs append to `journal.jsonl`. The consolidator is the job that folds that journal, and it refuses to rewrite `SOUL.md` or `USER.md`. | Cloud Storage FUSE is not a transactional disk. A crash mid-write can still leave one file short. The journal is the recovery source. |
| Someone other than the owner uses the gateway | `API_SERVER_KEY` is at least 16 characters and is checked by Hermes. Telegram, Discord, and Slack each have an allowlist. `/v1/models` returns 401 with a missing or wrong key. | The key is full chat access for whoever has it. It belongs in the Brightspace comments, not in the repo or the video. |

## Leftover risk

Local Gemma exists only while this PC is on and Tailscale is up. The cloud agent keeps answering without it. A person who can already send `APPROVE <draft-id>` from an allowlisted chat can send mail to an allowlisted recipient. That approval is the assignment's human check, not a second model.
