# Lumen

Lumen is a proactive personal assistant for CSCI 599 Assignment 3 (Agentic AI, Fall 2026). It runs Hermes Agent 0.20.5 on a Cloud Run instance, keeps its home on a Cloud Storage bucket, and routes each task to OpenAI `gpt-6.1-sol` or to local Ollama `gemma4:e2b`.

The assistant's user is **Maya Ortiz**, a fictional graduate student in Los Angeles. Mail, calendar, teammates, and deadlines are synthetic test data on accounts created only for this course.

The graded 48-hour window ran from 15 November 2026, 17:37:53 America/Los_Angeles through 17 November 2026, 17:37:53 America/Los_Angeles. The instance was already running when the window opened, and it was not restarted to start the clock. It is still running for grading.

| | |
|---|---|
| Project | `agenticaithree` |
| Region | `us-west1` |
| Instance | `lumen` |
| URL | https://lumen-986080954772.us-west1.run.app |
| Hermes home | `gs://lumen-home-agenticaithree`, mounted at `/hermes` |
| Cloud model | OpenAI API, `gpt-6.1-sol` |
| Local model | Ollama `gemma4:e2b` on this PC, reached through Tailscale |

Planning is in [plan.md](plan.md). The version log is [versions.md](versions.md). Conventions for coding agents are in [AGENTS.md](AGENTS.md).

## What it does

On a schedule, in `America/Los_Angeles`:

- **08:00** morning briefing: today's calendar, open gaps, Los Angeles weather, one-line mail summaries, nearby deadlines
- **21:00** end-of-day recap: what ran, what is waiting for a decision, what is early tomorrow
- **every 30 minutes** alerts: a meeting inside 30 minutes, a deadline inside 3 days, or flagged mail unanswered for more than 24 hours

On request in Telegram, Discord, and Slack: read the calendar, summarize unread mail, draft a reply, search the web, and suggest a study block before a deadline. The three chats share one Hermes home. A Discord channel message is answered inside a thread after the Lumen app is mentioned.

Sending email requires an explicit `APPROVE <draft-id>` from the owner, and the recipient must be on an allowlist. Scheduled jobs create drafts and notifications. They do not send.

## Architecture

```
Telegram / Discord / Slack
   │
   ▼
Cloud Run Instance (Hermes, Docker, non-root)
   skills · hybrid router · cron · memory
   │
   ├── OpenAI API            cloud model (gpt-6.1-sol only)
   ├── Tailscale ──────────► this PC · Ollama · gemma4:e2b
   ├── Cloud Storage         Hermes home and journal
   └── Secret Manager        runtime credentials
```

| Piece | Choice |
|---|---|
| Agent platform | Hermes |
| Host | Google Cloud Run Instances, 1 vCPU, 1 GiB to start |
| Chat | Telegram, Discord, and Slack, one Hermes home |
| Cloud model | OpenAI API, `OPENAI_MODEL=gpt-6.1-sol` |
| Local model | Ollama `gemma4:e2b` on the student PC |
| Network to the PC | Tailscale userspace proxy |
| Calendar | Secret iCal URL of a temporary Google Calendar |
| Email | Temporary Gmail via IMAP, drafts local, SMTP behind approval |
| Weather | Open-Meteo |
| Search | Brave Search API (DuckDuckGo if no Brave key) |
| Extra 10% | Three chats at once (Telegram, Discord, Slack) with shared memory |

Routing is task-based. A short question, including arithmetic such as "What is 12 times 9?", goes to Gemma with reason `simple` when the laptop is reachable. A message with a privacy word (`confidential`, `private`, `personal`, `sensitive`, `password`, `bank`, `medical`) goes to Gemma with reason `privacy`. Explanations, calendar, mail, and planning go to `gpt-6.1-sol` with reason `reasoning`. When Gemma is down, short and private tasks are answered by `gpt-6.1-sol` and the log reason is `local_unavailable`. They are sent to the cloud model. A flag file forces the local model so a rate-limit fallback can be demonstrated without burning OpenAI quota. Every decision is logged with the reason, the route (`local`, `cloud`, or `held`), and the model. The log line does not include the message text.

## Repository map

| Path | Purpose |
|---|---|
| `plan.md` | Build plan, rubric mapping, phases, demo script |
| `versions.md` | Pinned versions and the recorded checks, including the 48-hour window |
| `AGENTS.md` | Rules for coding agents changing this repo |
| `router/` | Hybrid router: classify, execute, and the OpenAI-compatible bridge |
| `skills/` | Calendar, email, web search, and Deadline Desk |
| `cron/` | Briefing, recap, alerts, memory consolidate, and health |
| `lib/` | Send gate, calendar feed, deadlines, and untrusted search snippets |
| `hermes/` | `SOUL.md`, `USER.md`, and `MEMORY.md` for Maya Ortiz |
| `deploy/` | Dockerfile, entrypoint, bucket mount, grader chat, and the model proxy |
| `synthetic/` | Fictional persona, deadlines, and fixtures |
| `security/` | Threat model and the three injection tests |
| `reports/PERFORMANCE.md` | Cloud versus Gemma timing, quality, and token cost |
| `evidence/48h/` | Logs and bucket files from the graded window |
| `PROCESS_LOG.md` | Required account of AI-assisted development |
| `tests/` | Unit tests for the gate, router, calendar, and grader chat |

Course PDFs stay outside this tree and are not part of the runtime.

## Prerequisites

- Google Cloud project with the course credit, and APIs for Cloud Run, Cloud Storage, Secret Manager, and Cloud Logging
- `gcloud` with the beta component (`gcloud beta run instances deploy --help` should print help)
- A region that currently offers Cloud Run Instances
- `OPENAI_API_KEY` and a successful test call to `gpt-6.1-sol`
- Telegram bot token and numeric user id, Discord bot token and user id, Slack bot token (`xoxb-`), Slack app token (`xapp-`), Slack member id, and a home channel id
- A temporary Gmail account and a temporary Google Calendar (secret iCal link)
- Docker Desktop, WSL2, Git, Python matching the pinned Hermes release
- Ollama on Windows with `gemma4:e2b`, context raised on the Ollama server
- Tailscale on the PC and on the Cloud Run instance
- A public GitHub repository for the Deadline Desk skill

Paste local secrets into `.env` (gitignored). `.env.example` lists the same names with empty values. On the instance, those values live in Secret Manager.

## Run outline

Hermes is the native Windows install used to build the image. The instance is a Cloud Run **instance**, not a Cloud Run service. `deploy/prepare_cloud.py` creates the Artifact Registry repository, the bucket, and the Secret Manager entries. `deploy/ship.py` builds the image and deploys `lumen` with the bucket mounted at `/hermes`. `deploy/install_cloud_jobs.py` registers the five schedules. The recorded results are in `versions.md`.

### Rate-limit simulation

The router calls Gemma or `gpt-6.1-sol` and appends a JSON line to `var/router.log`.

```
python -m router.execute
```

That runs one short local call, one briefing call to `gpt-6.1-sol`, then one more short call with the simulation flag on. The third log reason is `simulated_rate_limit` and OpenAI is not contacted. The flag is removed at the end.

Turn the flag on or off by itself:

```
python scripts/simulate_rate_limit.py on
python scripts/simulate_rate_limit.py off
```

`SIMULATE_RATE_LIMIT=1` does the same thing as the flag file `router/FORCE_LOCAL`. On the deployed instance that file lives in the Hermes home. Creating or removing it does not call OpenAI. With the flag gone, the next briefing goes back to `gpt-6.1-sol`.

### Grader web chat

The Cloud Run URL opens a chat page. Hermes listens on `127.0.0.1:8081`. `deploy/web_ui.py` listens on port 8080, serves that page, and forwards `/health` and `/v1/*` to Hermes. The grader pastes `API_SERVER_KEY` into the page. That key is the Secret Manager secret `lumen-gateway-key`. Put the key in the Brightspace comments. It is not in this repository.

The page has no approval buttons. A send, or any shell command Hermes would stop for approval, is refused in this chat with a note to approve it from Telegram, Discord, or Slack. Those apps still show the approval.

### Routing log

Each decision is one JSON line on the instance stdout, so Cloud Logging stores it as `jsonPayload`. From a machine logged into the project:

```
gcloud logging read "jsonPayload.component=\"lumen-router\"" --project=PROJECT_ID --freshness=30m --order=desc --limit=30 --format="table(timestamp.date('%H:%M:%S'),jsonPayload.target,jsonPayload.reason,jsonPayload.model_answered,jsonPayload.success)"
```

Replace `PROJECT_ID` with the Cloud project. The four video prompts land as `simple` / local, `reasoning` / cloud, `local_unavailable` / cloud while Ollama is quit, and `privacy` / local once Ollama is back.

### Scheduled jobs

All five use `America/Los_Angeles`. None of them can send email. Only the memory job rewrites `hermes/MEMORY.md`.

| Job | Schedule | Run by hand |
|---|---|---|
| Morning briefing | `0 8 * * *` | `python -m cron.cli briefing` |
| End-of-day recap | `0 21 * * *` | `python -m cron.cli recap` |
| Alert scan | `*/30 * * * *` | `python -m cron.cli alerts` |
| Memory consolidate | `15 * * * *` | `python -m cron.cli consolidate` |
| Health | `*/10 * * * *` | `python -m cron.cli health` |

`python cron/install_hermes.py` registers those schedules with Hermes. `hermes cron run <name>` fires one through the scheduler.

## Security

- Container runs as a non-root user with a startup report of uid and capabilities.
- Credentials come from Secret Manager.
- Send is blocked unless the owner approves that draft and the recipient is allowlisted.
- Email and search text are treated as untrusted data.
- Ollama is bound to localhost and reached through Tailscale.

The threat model is `security/THREAT_MODEL.md`. The three injection results are `security/injection-tests.md`. The model comparison is `reports/PERFORMANCE.md`.

## Submission

The course zip is `aadit_kshirsagar_a3.zip`. Inside it, every path below starts with `aadit_kshirsagar_a3/`. The real `.env`, keys, `.git`, and the local `var/` log are not in the archive. `.env.example` has the same names with empty values. The gateway key, the test Gmail password, and the backup codes go in the Brightspace comments.

The demo recording is in the zip as `Assignment3-CSCI599-arkshirs.mp4`. It shows the morning briefing, a live messaging request, both models answering, one proactive alert, and the end-of-day recap.

### 1. Source code

| What the assignment asks for | Where it is |
|---|---|
| Platform configuration | `hermes/SOUL.md`, `hermes/USER.md`, `deploy/Dockerfile`, `deploy/entrypoint.sh`, `.env.example` |
| Skills created for this agent | `skills/calendar/`, `skills/email/`, `skills/web-search/`, `skills/deadline-desk/` |
| Hybrid routing | `router/classify.py`, `router/router.py`, `router/execute.py`, `router/bridge.py`, `deploy/openai_proxy.py` |
| Scheduling | `cron/logic.py`, `cron/cli.py`, `cron/install_hermes.py`, `deploy/install_cloud_jobs.py` |
| Container and deployment | `deploy/Dockerfile`, `deploy/entrypoint.sh`, `deploy/prepare_cloud.py`, `deploy/ship.py`, `deploy/web_ui.py` |

### 2. Deployment evidence

The HTTPS URL is in the table at the top of this file. The 48-hour record is `evidence/48h/`. `evidence/48h/README.txt` states the window bounds and the job ids.

| Evidence | File |
|---|---|
| Full window, not only the start and the end | `evidence/48h/journal.jsonl` |
| Saved briefing, recap, alert, consolidate, and health text | `evidence/48h/cron-output/` |
| Schedule and last status, copied from the bucket | `evidence/48h/jobs.json` |
| Window marker, restart fact, and memory that stayed on the bucket | `evidence/48h/window-start.txt`, `evidence/48h/restart-fact.txt`, `evidence/48h/MEMORY.md` |
| How the bucket is mounted | `deploy/ship.py` |
| Platform log | `evidence/48h/gateway.log` |
| Routing decisions, with no message text | `evidence/48h/router.log`, `evidence/48h/cloud-logging-router.json` |

Hermes keeps the latest 50 output files per job. The alert and health markdown files therefore start late. The earlier hours of those jobs are the matching lines in `journal.jsonl`. The router files are the setup calls before the window and the demo calls after it. No `lumen-router` line was written during the quiet hours in between.

### 3. Security audit

`security/THREAT_MODEL.md` lists six risks, the mitigation for each, and the risk that remains. Container isolation is the non-root image in `deploy/Dockerfile` and the boot report in `deploy/isolation-report.sh`. Credential storage, the send gate, and prompt-injection handling are the other measures. `security/injection-tests.md` records three attacks and a Pass for each.

### 4. Performance comparison

`reports/PERFORMANCE.md` compares `gpt-6.1-sol` and `gemma4:e2b` on a short summary, a morning briefing, a private rewrite, and a forced-local reply. Each row has the route, the model that answered, the time, the token cost, and a note on the answer.

### 5. Personalization profile

`hermes/SOUL.md` is the assistant. `hermes/USER.md` is Maya Ortiz. `hermes/MEMORY.md` is the synthetic memory file. Nothing in those files is a real personal, financial, or USC account detail.

### 6. Process log

`PROCESS_LOG.md` has the five required sections: tools used, the development narrative, code attribution, how the work was checked, and what was learned.

### 7. Demo video

`Assignment3-CSCI599-arkshirs.mp4` sits next to this README inside the zip.

## Course references (local)

- `Assignment_3_Description.pdf`
- `Assignment_3_Setup_Recommendations.pdf`
- `Deployment_Reference.pdf`
- `Assignment3_local_Gemma.pdf`
- `Assignment3_Video_Instructions.pdf`

External docs used while building: [Hermes](https://hermes-agent.nousresearch.com/docs), [Cloud Run Instances](https://docs.cloud.google.com/run/docs/instances/create-and-manage-instances), [Tailscale on Cloud Run](https://tailscale.com/docs/install/cloud/cloudrun), [Ollama Gemma 4](https://ollama.com/library/gemma4), [OpenAI API](https://platform.openai.com/docs).
