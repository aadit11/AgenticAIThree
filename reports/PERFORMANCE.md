# Performance comparison

Recorded 15 November 2026, 17:25 America/Los_Angeles, on this PC, before the graded 48-hour window. The same router that the cloud agent uses chose the model. Short local calls use Ollama's native API with `think: false`, `keep_alive` of 30 minutes, and `num_predict` 32. After the runs, `ollama ps` showed `gemma4:e2b` on CPU, context 65536, about 1.6 GB.

Local rows made no OpenAI request. The cloud row is the only one with a token charge. This report records those tokens. It does not guess a dollar price for `gpt-6.1-sol`.

| Task | Why that route | Model that answered | Time | API tokens | Quality |
|---|---|---|---|---|---|
| One-line summary of a test email about a Tuesday 7 pm lab in Leavey 2 | `simple` | `gemma4:e2b` | 19.3 s | 0 | "Confirm the Tuesday lab time is 7 pm in Leavey 2." The first local call paid the load. |
| Morning briefing from the seminar, the overlapping review, the afternoon gap, 55 F, one unread note, and a deadline in two days | `reasoning` | `gpt-6.1-sol` | 3.8 s | 93 in, 133 out | Names the overlap, the 11:15–21:00 gap, the weather, the unread note, and the deadline. |
| Rewrite of a note marked confidential, asking for one short sentence | `privacy` | `gemma4:e2b` | 1.4 s | 0 | One sentence, still the fictional sticky-note line. The cloud function was not called. |
| Same short reply, with `router/FORCE_LOCAL` present | `simulated_rate_limit` | `gemma4:e2b` | 0.6 s | 0 | Replied `pong`. The cloud function aborts if it is called, and it was not called. The flag was removed afterward. |

The routes match the policy. A short email summary and a private one-sentence rewrite stayed on Gemma. The briefing, which has to combine the calendar, weather, mail, and a deadline, went to `gpt-6.1-sol`. The flag forced Gemma even though the task would otherwise have been allowed to use the cloud, and removing the flag is what puts the next briefing back on `gpt-6.1-sol`.

Warm local calls were about 1 second. The 19.3 second summary is the cold load in this process. An earlier cold Gemma reply on 14 November took 61 seconds. A later warm `simple` call from the Cloud Run instance, reaching this PC through Tailscale, took 377 ms. Local cost is that wait and about 1.6 GB of RAM. Cloud cost for the briefing is 226 tokens and no local RAM.

When this PC is asleep, the same short and private tasks are answered by `gpt-6.1-sol` and the log reason is `local_unavailable`. That fallback is the documented policy. It is not a second model on the laptop.
