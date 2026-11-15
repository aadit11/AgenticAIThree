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
| Container image digest | Not built yet |

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
