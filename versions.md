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
