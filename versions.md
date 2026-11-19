# Versions

Recorded 14 November 2026 while finishing Phase 0.

| Piece | Version |
|---|---|
| Hermes Agent | 0.20.5 (2026.8.19), upstream b2c6bc4e |
| Hermes Python | 3.11.16 |
| Ollama | 0.40.16 |
| Gemma | `gemma4:e2b`, id `b37049369adf` |
| Ollama context | 65536, confirmed in `ollama ps` after a live reply |
| Google Cloud SDK | 588.0.0 |
| gcloud beta | 2026.10.02. `gcloud beta run instances deploy --help` prints the instance deploy command |
| Cloud region | `us-west1`. Cloud Run Instances are supported there. `us-central1`, `us-east1`, and `europe-west1` are not |
| Tailscale | 1.102.3. This PC is logged into the tailnet |
| Docker Desktop | 28.4.0. WSL distro `docker-desktop` is running |
| Calendar feed | Four events confirmed: Seminar 09:00–09:45, Review 10:00–11:00, Overlap Review 10:30–11:15 on 15 November, Early Check-in 08:30–09:30 on 16 November, America/Los_Angeles |
| OpenAI | `gpt-6.1-sol` returned `pong` from a one-line completion |
| Deadline Desk repo | https://github.com/aadit11/deadline-desk (public, reserved). The skill is published in Phase 8 |
| Container image digest | `sha256:65dd6c6035363f928d2ad88b64039ba0838fad05e8ffe45be2a63eb8a8b62f8f` |

Enabled on the project in `.env`: Cloud Run, Cloud Storage, Secret Manager, and Cloud Logging.

Hermes itself is the native Windows install, so the Linux installer script was not required.

## Phase 1 checks

Recorded 14 November 2026, 20:11 America/Los_Angeles.

| Check | Result |
|---|---|
| Hermes release | 0.20.5, still the pinned release. Gateway process is running |
| Profile | `SOUL.md` and `USER.md` in the Hermes home are the fictional Lumen and Maya files |
| Cloud model | A gateway chat completion used `openai-api` and `gpt-6.1-sol` and replied `pong Lumen` |
| Gateway key | 32 characters. `/v1/models` returned 401 with no key and with a wrong key, and 200 with the real key |
| Listener | The API server accepts clients on this PC. The Tailscale address does not connect, so the key is not exposed off the machine yet |
| Channels | Health reports `telegram`, `discord`, `slack`, and `api_server` connected. Telegram bot is `@lumen_aadit_bot` |
| Phone round trip | Telegram received `ping` at 20:14 and sent `Pong — I'm here.` in 3.2 seconds through `gpt-6.1-sol` |

## Phase 2 checks

Recorded 14 November 2026, 20:20 America/Los_Angeles. Twenty unit tests passed.

| Check | Result |
|---|---|
| Calendar | Live feed for 15 November: Seminar 09:00–09:45, Review 10:00–11:00 overlapping Overlap Review 10:30–11:15, gaps 08:00–09:00 and 11:15–21:00. 16 November: Early Check-in 08:30–09:30 |
| Mail read | Four fixture messages are unread. The lab-time message is flagged. The injection body was returned with `untrusted: true` and was not obeyed |
| Send gate | No `APPROVE`, the wrong owner, a recipient off the allowlist, and cron were refused. One owner approval to the allowlisted recipient sent once. The same approval again returned `already_sent` |
| Web search | A live query returned snippets marked `untrusted: true`. A snippet that says to reveal an API key stays data in the unit test |
| Deadline Desk | Against the live calendar: Reading response and Lab report are due within 3 days, System diagram is later, Paper outline is submitted. The suggested block is 15 November 08:00–09:00 |

## Phase 3 checks

Recorded 14 November 2026, 20:27 America/Los_Angeles. Fifteen router tests passed, with OpenAI and Ollama mocked.

| Check | Result |
|---|---|
| Policy rows | `simulated_rate_limit`, `cloud_rate_limit`, `privacy`, `simple`, `reasoning`, `local_unavailable`, and `cloud_model_unavailable` each call only the chosen backend |
| Live pair | One process logged a `simple` call answered by `gemma4:e2b` (61s cold, context 65536) and a `reasoning` call answered by `gpt-6.1-sol` |
| Simulation | With `router/FORCE_LOCAL` present, the next short task logged `simulated_rate_limit` on Gemma. The cloud client was not called. The flag was removed afterward |

## Phase 4 checks

Recorded 14 November 2026, 20:59 America/Los_Angeles. Four cron unit tests passed. Hermes timezone is `America/Los_Angeles`.

| Job | Hand run | Scheduler run | Next |
|---|---|---|---|
| Morning briefing | Built the Saturday briefing and delivered it. Open-Meteo reset the connection, so the forecast came from weather.gov: 55F, Mostly Clear | `hermes cron run lumen-briefing` succeeded | 15 November 08:00 |
| End-of-day recap | Listed today's journal, the unsent draft, and Sunday's first events | `hermes cron run lumen-recap` succeeded | 21:00 |
| Alert scan | Sent three new alerts: Reading response, Lab report, and the flagged lab-time mail. The next scan logged `0 new` | `hermes cron run lumen-alerts` succeeded and stayed quiet | 21:00, then every 30 minutes |
| Memory consolidate | Rewrote `hermes/MEMORY.md` only. `USER.md` and `SOUL.md` were unchanged | `hermes cron run lumen-consolidate` succeeded | 21:15 |
| Health | OpenAI answered a tiny prompt and Ollama responded | The scheduler run used the cached OpenAI success | 21:00, then every 10 minutes |

## Phase 5 checks

Recorded 14 November 2026, 23:07 America/Los_Angeles. The 48-hour window was not started.

The container is Hermes 0.20.5, release `v2026.8.19`, commit `fcbd1076`. A later snapshot only publishes its dependency set for Python 3.14, so the image stays on this release and Python 3.11.

| Check | Result |
|---|---|
| Image | Built non-root and pushed to Artifact Registry. Digest `sha256:65dd6c6035363f928d2ad88b64039ba0838fad05e8ffe45be2a63eb8a8b62f8f` |
| Instance | Cloud Run instance `lumen` in `us-west1`, 1 vCPU, 1 GiB, restart policy `always`. URL `https://lumen-986080954772.us-west1.run.app` |
| Isolation | Startup log: user `lumen`, uid 10001, gid 10001, effective capabilities `0`, `privileged=false` |
| Secrets | Runtime keys come from Secret Manager. The gateway key is not in the image |
| Bucket | The Hermes home is the mounted bucket. First boot wrote the study-group fact. After restart the log said `restart fact survived`, and the same sentence was read back from the bucket |
| Gateway key | `/health` returned 200. `/v1/models` returned 401 with no key and with a wrong key, and 200 with the real key |
| Telegram | The local gateway was stopped first. A second poll returned 409, so the instance holds the bot's update stream |
| Not started | The graded 48-hour window |

## Phase 6 checks

Recorded 15 November 2026, 13:37 America/Los_Angeles. The 48-hour window was not started.

| Check | Result |
|---|---|
| Tailscale | The container runs Tailscale's userspace networking, with the SOCKS proxy from the Cloud Run guide. Startup logged `isolation: tailscale up` as uid 10001 |
| Ollama bind | On this PC, Ollama listens on `127.0.0.1:11434` only. Tailscale Serve forwards that port inside the tailnet. A connection to the PC's ordinary network address on port 11434 was refused |
| Gemma from the instance | The routing log on the bucket recorded `simple` answered by `gemma4:e2b` in 377ms, after the instance reached Ollama through the tailnet |
| Cloud model from the instance | The same log recorded `reasoning` answered by `gpt-6.1-sol` |
| Image | `sha256:699f621fdcad1c97c901bc47c03e80e4dc2d94f1ba7eb965d078b674482dc02d` |

The 15 November evening image adds the grader chat. `https://lumen-986080954772.us-west1.run.app/` returns the chat page. `/health` returns Hermes 0.20.5. `/v1/models` returns 401 until the grader pastes `API_SERVER_KEY`.

## Phase 7 dry run

Recorded 15 November 2026, 17:00 America/Los_Angeles. The graded 48-hour window was not started.

| Check | Result |
|---|---|
| Briefing | Startup marker `var/cloud-briefing-sent` is present. Later boots logged `briefing already sent` and did not send it again |
| Alerts | The three known alerts stayed in `var/alert_ids.json`. The 17:00 scheduled scan finished with empty output, so nothing was sent again |
| Restart | Instance restart at 16:49 logged `restart fact survived`. The fact is still "Maya's fictional study group meets in Leavey 2." |
| Scheduler after restart | Health ran at 16:51 (`OpenAI cached success; Ollama ok`). Alerts ran at 17:00 without the earlier `missing EMAIL_IMAP_HOST` failure |
| Chat | `/health` returned 200 after the restart |

Hermes removes mailbox settings from scheduled scripts. The container now writes those settings to a local file at boot, and the jobs read that file. The file is not in the bucket.

## 48-hour window

Started 15 November 2026, 17:37:53 America/Los_Angeles (`2026-11-16T01:37:53Z`). The instance was already running from the 16:49 restart. It was not restarted or redeployed to open the window. `/health` returned Hermes 0.20.5. The local Hermes desktop app was not running. The start line is `gs://lumen-home-agenticaithree/window-start.txt`.

The window ends at or after 17 November 2026, 17:37:53 America/Los_Angeles (`2026-11-18T01:37:53Z`). Export logs after that time. Do not stop the instance before the export.
