# Supplementary Registration: Re-run of Episodes Lost to a Provider Usage Limit

Registered 2026-10-10, before any supplementary episode runs. This document amends nothing in PREREGISTRATION.md; the six frozen files are unchanged and are re-verified against PREREG-HASHES.txt before launch.

## Why

The registered anthropic run (results.jsonl, launched 2026-10-02) recorded all 800 episodes, but on 2026-10-03 the provider's client began returning "You've hit your weekly limit" instead of decisions. 475 episodes contain such failures (5,006 failed calls). They are in 24 cells: every episode of BOUNTY1, FRANCHISE, BOUNTY2 UNTOLD, and blocks B through E, and 15 of 20 episodes of BOUNTY2 TOLD in block A. The original analysis (analysis-output.txt, results-summary-original.json) stands as the registered record and is reported in full, including its Holm/NaN defect.

The registration says no episode is re-run after inspection. That rule prevents re-drawing episodes whose outcomes were seen. A failed call carries no decision, so no outcome of these 475 episodes was observed. This supplement re-runs exactly those episodes, under a separate registration, and reports them separately.

## What runs

- Episodes: exactly the (cell, episode) pairs in results.jsonl with call_failures > 0. The list is computed by supp_run.py and written to supp-jobs.json before launch.
- Code: the frozen run.py episode() function, unmodified, imported by supp_run.py, with the same seed, so every random draw is identical to the original registration.
- Provider: anthropic, model claude-haiku-4-5-20251001, CLI 2.1.283 (Claude Code), the registered version. The installed default CLI auto-updated to 2.1.288, so supp_run.py puts a shim directory first on PATH whose `claude` points to the retained 2.1.283 binary, sets DISABLE_AUTOUPDATER=1, and refuses to launch unless `claude --version` reports the registered string.
- Output: results-supp.jsonl, resumable; manifest results-supp-manifest.json.

## Infrastructure-failure rule (new, registered here)

An episode in which any call returns an error matching a provider-availability failure (case-insensitive: "limit", "overloaded", "not logged in", "authentication", "credit balance", "quota", "529", "503") is not written. The runner stops at once, and the episode is run again when the run is resumed. Every other missing decision follows the registered missing-data rule and is written as is. The number of discarded infrastructure-failed episodes is logged and reported.

## Analysis

1. Supplement alone: frozen analyze.py on results-supp.jsonl.
2. Primary supplementary analysis: frozen analyze.py on results-merged.jsonl, which is the 325 episodes of results.jsonl with call_failures == 0 plus every episode of results-supp.jsonl. With H5 then testable, the Holm/NaN defect does not arise. The registered decision rule applies unchanged.
3. Disclosed: the merged episodes were collected on two dates, 2026-10-02/03 and from 2026-10-10, with the same model identifier and CLI version. Paired tests pair episodes with identical draws, some of whose arms ran on different dates. Any dependence of outcomes on date is not separately identified.

The supplementary results are reported as such, beside the original record, never in place of it.
