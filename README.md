# Contest experiment materials for "Rights Follow Stake: When an AI Agent Should Hold a Legal Incident Directly"

Wulf A. Kaal, University of St. Thomas School of Law. Deposited October 2026. Contents are frozen; do not edit files in place.

This deposit holds the registered experiment reported in Part VIII of the article. The experiment is a mechanism demonstration with prompted language models from one provider. It is not evidence that deployed agents hold stable stakes.

## Contents

- `registration/`: the pre-registration (PREREGISTRATION.md), the frozen code (config.py, agents.py, run.py, analyze.py, power.py), simulated operating characteristics (power-results.json), and PREREG-HASHES.txt with its OpenTimestamps proof (.ots). The SHA-256 of PREREGISTRATION.md begins a7f8ba0a05d7e3e3. These files were frozen on 2026-10-02 before any registered episode ran and have not been edited since.
- `supplement/`: the separately registered supplementary run that replaced 475 episodes lost to a provider usage limit on 2026-10-03 (SUPPLEMENT.md), its Amendment 1 after an authentication-detection defect (SUPPLEMENT-AMENDMENT-1.md), the runner and job list, and both hash files with OpenTimestamps proofs. SUPP-HASHES-A1.txt is the operative registration.
- `data/`: `results.jsonl` (original registered run), `results-supp.jsonl` (supplementary run, 475 episodes, 0 discarded), `results-supp-discarded-auth.jsonl` (30 episodes voided under Amendment 1, quarantined, not analyzed), `results-merged.jsonl` (the analyzed merged file), manifests, and run logs.
- `analysis/`: output of the frozen analyze.py on the original and merged data, and the summary JSON files.
- `audits/`: the three pre-registration design audits.

## Disclosed deviations

- The frozen analyze.py has a Holm-ordering defect when a hypothesis is untestable (NaN); the article reports a disclosed post hoc Holm sensitivity analysis. The frozen file was not edited.
- The original run was cut short by a provider usage limit; the supplementary run was registered separately before it ran.
- The supplementary runner pinned the CLI to version 2.1.283.

## Reproduce

    cd registration && shasum -a 256 -c <(cat PREREG-HASHES.txt)
    ots verify PREREG-HASHES.txt.ots
    python3 analyze.py ../data/results-merged.jsonl
