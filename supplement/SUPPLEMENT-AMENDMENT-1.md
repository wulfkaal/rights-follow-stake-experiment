# Supplementary Registration, Amendment 1

Registered 2026-10-10, after the first supplementary launch and before any valid supplementary episode.

## What happened

The supplementary run registered in SUPPLEMENT.md (SUPP-HASHES.txt, OpenTimestamps-stamped) launched on 2026-10-10. Every call it made failed with the client error "Failed to authenticate: OAuth session expired and could not be refreshed": the command-line client's login had expired. The registered infrastructure-failure rule lists "authentication" as a pattern, intending to catch exactly this, but the client's message says "authenticate", which the literal pattern does not match. The runner therefore wrote 30 episodes in which every call failed before it was stopped by hand.

No decision was made by the model in any of the 30 episodes. They are kept, unanalyzed, in results-supp-discarded-auth.jsonl, with the void manifest (results-supp-manifest-v1-void.json) and log (run-supp-v1-void.log).

## Changes

1. The infrastructure-failure pattern becomes (case-insensitive): "limit", "overloaded", "not logged in", "authenticat", "oauth", "credit balance", "quota", "529", "503". Applied to results.jsonl, the amended pattern flags exactly the 475 failed episodes and none of the 325 clean ones; applied to the 30 void episodes, it flags all 30.
2. Before launch and on every resume, the runner makes one preflight call through the registered client and model and refuses to launch if it fails.
3. The 30 void episodes are treated as infrastructure-failed episodes under the registered rule, which they always were in intent, and are run again.

Everything else in SUPPLEMENT.md is unchanged. This amendment, the amended supp_run.py, and the unchanged SUPPLEMENT.md and supp-jobs.json are hashed into SUPP-HASHES-A1.txt and time-stamped before the relaunch.
