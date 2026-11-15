# Lumen

Lumen is a proactive personal assistant for CSCI 599 Assignment 3 (Agentic AI, Fall 2026). It runs on Hermes, delivers a daily study briefing on Telegram, Discord, and Slack, and routes each task to OpenAI `gpt-6.1-sol` or to a local Gemma 4 model.

The assistant's user is **Maya Ortiz**, a fictional graduate student in Los Angeles. Mail, calendar, teammates, and deadlines are synthetic test data on accounts created only for this course.

Planning is in [plan.md](plan.md). Conventions for coding agents are in [AGENTS.md](AGENTS.md). Phase 2 skills, the approval gate, and the router tests are in this repo. Cloud deployment has not started.

## What it does

On a schedule, in `America/Los_Angeles`:

- **08:00** morning briefing: today's calendar, open gaps, Los Angeles weather, one-line mail summaries, nearby deadlines
- **21:00** end-of-day recap: what ran, what is waiting for a decision, what is early tomorrow
- **every 30 minutes** alerts: a meeting inside 30 minutes, a deadline inside 3 days, or flagged mail unanswered for more than 24 hours

On request in Telegram: read the calendar, summarize unread mail, draft a reply, search the web, and suggest a study block before a deadline.

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

Routing is task-based. Short and private tasks go to Gemma when the laptop is reachable. Briefings, drafts, and planning go to `gpt-6.1-sol`. A flag file forces the local model so a rate-limit fallback can be demonstrated without burning OpenAI quota. Every decision is logged with the reason.

## Repository map

| Path | Purpose |
|---|---|
| `plan.md` | Build plan, rubric mapping, phases, demo script |
| `AGENTS.md` | Rules for coding agents changing this repo |
| `router/` | Hybrid router and tests |
| `skills/` | Calendar, email, web search, Deadline Desk |
| `hermes/` | `SOUL.md`, profile, cron definitions |
| `deploy/` | Dockerfile, entrypoint, Cloud Run commands |
| `synthetic/` | Fictional persona, deadlines, fixtures |
| `security/` | Threat model, approval notes, injection tests |
| `reports/` | Performance comparison and 48-hour evidence notes |
| `PROCESS_LOG.md` | Required account of AI-assisted development |

Those directories are created as each phase in `plan.md` lands. Course PDFs in this folder stay as reference and are not part of the runtime.

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

Exact commands will match the pinned Hermes release and will be filled in during Phase 1. The intended flow:

1. Install Hermes in WSL2 and configure `gpt-6.1-sol` as the primary model.
2. Connect Telegram and complete one round trip.
3. Enable calendar, email, search, and Deadline Desk against the temporary accounts.
4. Run the router tests, then one live OpenAI call and one live Ollama call.
5. Build the container, deploy a Cloud Run **instance**, mount the memory bucket, and attach Tailscale.
6. Confirm both models from the deployed instance, then start cron.
7. Dry-run for several hours, then collect the 48-hour operation logs.

### Rate-limit simulation

After the router exists:

- Turn on: create `router/FORCE_LOCAL` on the Hermes home (or set `SIMULATE_RATE_LIMIT=1`) and send a short task. The log reason is `simulated_rate_limit`. OpenAI is not called.
- Turn off: remove the flag. The next short task follows the normal policy.

## Security

- Container runs as a non-root user with a startup report of uid and capabilities.
- Credentials come from Secret Manager.
- Send is blocked unless the owner approves that draft and the recipient is allowlisted.
- Email and search text are treated as untrusted data.
- Ollama is bound to localhost and reached through Tailscale.

Details and the five-risk threat model are specified in `plan.md` and will be written up under `security/`.

## Submission

Course deliverable: `firstname_lastname_a3.zip` plus a 5–7 minute demo `Assignment3-CSCI599-<USCusername>.mp4`.

The video shows the Windows Product ID, the morning briefing, a live Telegram request, both models answering, one proactive alert, and the end-of-day recap. Gateway credentials go in the Brightspace comments, not in this repository.

## Course references (local)

- `Assignment_3_Description.pdf`
- `Assignment_3_Setup_Recommendations.pdf`
- `Deployment_Reference.pdf`
- `Assignment3_local_Gemma.pdf`
- `Assignment3_Video_Instructions.pdf`

External docs used while building: [Hermes](https://hermes-agent.nousresearch.com/docs), [Cloud Run Instances](https://docs.cloud.google.com/run/docs/instances/create-and-manage-instances), [Tailscale on Cloud Run](https://tailscale.com/docs/install/cloud/cloudrun), [Ollama Gemma 4](https://ollama.com/library/gemma4), [OpenAI API](https://platform.openai.com/docs).
