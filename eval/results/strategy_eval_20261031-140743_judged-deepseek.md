# Strategy eval — 20261029-212243

- Model under test: `main`; judge: `deepseek-v4-pro-ron` (re-judged from `eval/results/strategy_eval_20261029-212243.json`)
- 20 queries × 3 runs per strategy; LLM cache disabled
- Raw rows: `eval/results/strategy_eval_20261031-140743_judged-deepseek.json`
- Values are mean ± sample std over all successful calls for that strategy (n = queries × runs, minus errors). Judge scores are 1–5.

| Strategy | n ok / total | Latency (s) | Prompt tokens | Completion tokens | LLM calls | Judge overall | Correct | Complete | Secure defaults | Valid syntax |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 59/60 | 17.3 ± 12.8 | 15914 ± 27402 | 965 ± 406 | 2.6 ± 1.1 | 4.01 ± 0.84 | 3.49 ± 1.12 | 4.61 ± 0.74 | 3.84 ± 0.93 | 3.62 ± 1.28 |
| chaining | 60/60 | 22.4 ± 15.4 | 7222 ± 1387 | 2273 ± 1891 | 4.0 ± 0.0 | 1.75 ± 0.92 | 1.58 ± 0.89 | 1.60 ± 1.06 | 2.96 ± 0.66 | 3.04 ± 1.04 |
| meta | 58/60 | 5.6 ± 4.7 | 1418 ± 13 | 500 ± 521 | 1.0 ± 0.0 | 2.57 ± 1.45 | 2.47 ± 1.50 | 2.69 ± 1.84 | 3.47 ± 0.77 | 3.58 ± 0.90 |
| reflection | 60/60 | 26.3 ± 16.2 | 16205 ± 16640 | 1965 ± 922 | 3.5 ± 1.2 | 3.58 ± 1.14 | 3.15 ± 1.25 | 4.10 ± 1.47 | 3.57 ± 0.93 | 3.63 ± 1.11 |

## Compose-generation queries only (3 queries)

| Strategy | n | Judge overall | Correct | Complete | Secure defaults | Valid syntax |
|---|---|---|---|---|---|---|
| baseline | 9 | 2.83 ± 0.85 | 2.00 ± 0.50 | 3.78 ± 1.30 | 3.00 ± 0.76 | 3.00 ± 1.20 |
| chaining | 9 | 2.78 ± 0.89 | 2.44 ± 0.88 | 3.22 ± 1.39 | 3.00 ± 0.53 | 2.88 ± 1.13 |
| meta | 9 | 2.69 ± 1.35 | 2.22 ± 1.09 | 3.11 ± 1.76 | 3.50 ± 0.84 | 3.67 ± 0.82 |
| reflection | 9 | 3.22 ± 0.97 | 2.78 ± 1.09 | 4.00 ± 1.73 | 3.29 ± 0.76 | 3.43 ± 0.98 |

## Judge overall score per query (mean ± std over runs)

| # | Query | baseline | chaining | meta | reflection |
|---|---|---|---|---|---|
| 1 | Generate a compose file for Gitea with PostgreSQL | 3.17 ± 0.38 | 3.67 ± 0.14 | 3.58 ± 0.14 | 3.42 ± 0.38 |
| 2 | Does Immich have any recent CVEs? | 4.33 ± 0.58 | 1.67 ± 1.15 | 1.67 ± 1.15 | 1.42 ± 0.72 |
| 3 | How do I set up NextCloud? | 3.33 ± 0.58 | 3.17 ± 0.52 | 2.58 ± 1.42 | 3.17 ± 0.52 |
| 4 | What dependencies does VaultWarden need? | 4.25 ± 0.25 | 2.42 ± 0.14 | 1.75 ± 1.30 | 3.42 ± 2.10 |
| 5 | What environment variables do I need for WireGuard | 3.58 ± 0.80 | 1.33 ± 0.58 | 3.17 ± 0.29 | 3.25 ± 0.90 |
| 6 | What are the resource requirements for Jellyfin vs | 4.50 ± 0.00 | 1.42 ± 0.72 | 1.83 ± 1.44 | 4.36 ± 0.13 |
| 7 | I am looking for an open source media player that  | 4.92 ± 0.14 | 1.33 ± 0.58 | 3.17 ± 2.02 | 4.83 ± 0.29 |
| 8 | What are the main differences between Joplin and O | 4.17 ± 0.58 | 1.17 ± 0.29 | 1.00 ± 0.00 | 3.08 ± 1.84 |
| 9 | How can I configure SSO/OAuth for Authentik with m | 3.58 ± 0.38 | 1.00 ± 0.00 | 1.00 ± 0.00 | 4.33 ± 0.58 |
| 10 | How does the Sonarr/Radarr with Prowlarr and Jelly | 4.42 ± 0.14 | 1.50 ± 0.87 | 4.00 ± 0.50 | 3.25 ± 0.66 |
| 11 | My NextCloud container keeps restarting, what coul | 4.67 ± 0.14 | 1.42 ± 0.72 | 1.00 ± 0.00 | 4.08 ± 0.38 |
| 12 | Are there any known vulnerabilities in the latest  | 4.00 ± 1.32 | 1.00 ± 0.00 | 1.67 ± 1.15 | 2.33 ± 1.15 |
| 13 | What security hardening steps should I take after  | 4.50 ± 0.00 | 1.92 ± 0.80 | 1.83 ± 1.44 | 3.33 ± 0.29 |
| 14 | I have the following message on my admin dashboard | 4.00 ± 0.66 | 1.50 ± 0.87 | 3.92 ± 0.14 | 4.00 ± 0.87 |
| 15 | What are the best self-hosted alternatives for Goo | 4.67 ± 0.58 | 1.00 ± 0.00 | 2.17 ± 1.04 | 4.08 ± 1.18 |
| 16 | What are the differences between LinuxServer.io im | 4.56 ± 0.10 | 1.00 ± 0.00 | 4.17 ± 1.44 | 4.56 ± 0.10 |
| 17 | How should I back up the data on my NextCloud inst | 3.58 ± 0.38 | 2.33 ± 1.26 | 2.58 ± 1.42 | 3.50 ± 0.50 |
| 18 | What is LetsEncrypt used for? | 4.75 ± 0.43 | 1.42 ± 0.72 | 4.83 ± 0.29 | 4.83 ± 0.29 |
| 19 | Could You walk me through how to set up VaultWarde | 2.33 ± 1.26 | 1.92 ± 0.88 | 2.17 ± 2.02 | 2.92 ± 1.77 |
| 20 | Set up Paperless-ngx with Redis and PostgreSQL beh | 3.00 ± 0.75 | 2.75 ± 0.25 | 2.33 ± 1.15 | 3.33 ± 0.52 |

## Paired comparison per query

Each query's mean overall score over runs, compared between two strategies on the same queries. Sign test: exact two-sided binomial on better vs worse, ties dropped; p-values are not corrected for the number of comparisons.

| A vs B | Queries | Mean diff (A − B) | A better | A worse | Tie | Sign test p |
|---|---|---|---|---|---|---|
| baseline vs chaining | 20 | +2.27 | 19 | 1 | 0 | 0.000 |
| baseline vs meta | 20 | +1.49 | 18 | 2 | 0 | 0.000 |
| baseline vs reflection | 20 | +0.44 | 13 | 5 | 2 | 0.096 |
| chaining vs meta | 20 | -0.78 | 7 | 11 | 2 | 0.481 |
| chaining vs reflection | 20 | -1.83 | 2 | 17 | 1 | 0.001 |
| meta vs reflection | 20 | -1.05 | 3 | 16 | 1 | 0.004 |

## Errors

- meta q11 run 2: empty response
- meta q9 run 3: HTTP 500
- baseline q13 run 3: stream error
