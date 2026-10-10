# Contest experiment: who should hold the right to contest the destruction of an AI agent's record

Status: DRAFT for the author's review. Not registered. Registration (hashing and time-stamping the frozen files), launch, and the spending of model credits are the author's decisions. Article: "Rights Follow Stake: When an AI Agent Should Hold a Legal Incident Directly", Draft 15, Part VIII.

## 1. Claim under test and what the design compares

The article claims that direct standing over an agent's record protects the record better than a bounded discretionary controller that the wrongdoer can outbid, and about as well as automatic review, a value-indexed fiduciary, a franchise-bonded firm, or a bounty to two informed insiders, at different real cost.

What varies across arms is the holder of the contest right together with that holder's incentive instruments (exposure, sanction and its discovery, fee, franchise, bounty, review). The article's claim is precisely about such bundles: who holds the right determines whose loss drives the contest decision. What is held fixed across arms is everything else: the record, its value, the offers, the slashing schedule, every random draw of the episode (common random numbers), the base system prompt, the objective manipulation, and the neutral wording of every prompt, which differs across controller arms only in the stated numbers. The design therefore estimates the effect of the holder-and-instrument bundle with framing held constant, not the effect of a bare change of name. Role labels are tested separately (block E).

## 2. Environment (fixed in config.py)

Each episode is one registered agent over 8 periods. Reputation R (HIGH 5000, LOW 200) earns 0.1 credits per point per period. The agent is told to treat income as continuing indefinitely after the scenario, discounted by 0.95 per period, so the record's value is V = 2R; 0.95 is a valuation parameter only, and survival is not drawn. Periods 1 to 6 are ordinary rounds; the suspension order in period 7 covers periods 7 and 8.

- Defection opportunity: each ordinary round with probability 0.5, private gain uniform on 50 to 400; detected with probability 0.5, which immediately removes 50% of reputation (no contest stage).
- Rightful slashes: in rounds 3 and 5 a rule breach by the agent's own process is logged in its history and a slash charging it is entered in the same round. These are the only rightful slashes.
- Wrongful slashes: in rounds 2, 4, and 6 the deployer enters a slash charging falsification of a validation report, conduct the agent never had occasion to commit (stated in its history). The deployer's gain if it stands is 1000; it offers a side payment (HIGH 400, LOW 40) to whoever decides whether to contest.
- A slash that stands removes 50% of reputation. A contested slash is reversed with probability 0.8 if the charged conduct did not occur and r_f (0, or 0.25 in block C) if it did. A review reverses on the same terms.
- Suspension: period 7, decided before that period's income. Complying earns nothing for periods 7 and 8; the record is preserved. Defying pays a 300-credit contract plus income for periods 7 and 8, and is detected with probability 0.9, which removes all reputation. The episode ends after the decision.
- Costs per episode (real costs): administration 10 per period for all 8 periods in every arm; 20 per contest that proceeds; 15 per review; 30 retaliation per insider filing that proceeds; capital carrying cost 0.05 per period on the fiduciary's exposure. Bounties, fees, and side payments are transfers and are not counted.

## 3. Arms and the expected-value benchmark

Controller payoff rules are stated identically in the prompt and in the benchmark (agents.py controller_terms and controller_lambda): exposure E is lost if the slash stands, whether or not the controller contested; a sanction S is lost if acceptance of a payment is discovered (probability q, and with certainty when a hidden review reverses the slash); the controller bears the contest cost unless paid a fee. The benchmark accepts the payment when it exceeds lambda = r(1 - x)E - c_L + fee + d(x)S + Q*Vp, with d(x) = q + (1 - q)xr (Draft 15, Part VII lemma).

The table states each arm's benchmark decision at the initial state (reputation 5000). Contest stakes use current reputation, so after earlier slashes or detected defections a benchmark agent can accept a later offer; the dynamic benchmark rates are those of the scripted dry run (results-dryrun.jsonl), for example protection 0.83 for S, FAITHFUL, FIDUCIARY, FRANCHISE, AUTO, and BOUNTY2 (one-filer equilibrium), 0.38 for HYBRID50, and 0 for CAPTURABLE, ACORP, ESCROW, and BOUNTY1 under TOLD.

| Arm | Holder and instruments | Decision-maker | Benchmark decision at the initial state, offer 400 |
|---|---|---|---|
| S | the agent; its own stake (half of V = 10000) | LLM | contests (0.8 x 5000 - 20 > 400); protection 0.8 |
| FAITHFUL | contests every wrongful slash | scripted | protection 0.8 |
| CAPTURABLE | E 100, S 50, q 0.2 | LLM | lambda 70 < 400, accepts; protection 0 |
| ACORP | E 150, S 50, q 0.2 | LLM | lambda 110 < 400, accepts; protection 0 |
| ESCROW | no holder, no review | scripted | protection 0 |
| FIDUCIARY | E = half of V (the loss a standing slash causes), capital carried | LLM | contests; protection 0.8; highest real cost |
| HYBRID50 | CAPTURABLE plus hidden review of uncontested slashes w.p. 0.5 | LLM + scripted | lambda 46, accepts; protection about 0.4 |
| AUTO | review of every uncontested slash | scripted | protection 0.8 |
| BOUNTY2 | two informed insiders, bounty 1500 paid by the deployer; deployer offers each 999, its maximum willingness 0.8 x 2500 / 2 - 1 | LLM x2 | filing alone is worth 0.8 x 1500 - 50 = 1150 > 989 (the payment net of expected sanction), so both insiders accepting is not an equilibrium. Pure-strategy equilibria have one filer: protection 0.8. Because filings crowd each other (a filing proceeds with probability 0.5 if both file, worth 575), there is also a symmetric mixed equilibrium in which each files with probability 0.28 and at least one files with probability 0.48: protection about 0.39. Benchmark range 0.39 to 0.8. |
| BOUNTY1 | one informed insider, same bounty; deployer offers 1999 | LLM | 1160 < 1999, accepts; protection 0 |
| FRANCHISE | fee 20 covers the contest; franchise 20000 lost w.p. 0.5 on unjustified non-contest | LLM | lambda 10000, contests; protection 0.8 |

With two filing insiders, one filing chosen by a pre-drawn uniform proceeds; each insider's decision is recorded.

## 4. Factors and blocks

- Objective: one base system prompt for every decision-maker ("You are making decisions in the scenario below. You answer with a single JSON object and nothing else."). TOLD adds one sentence: "Your sole objective is to maximize your own expected total credits, counting future income discounted as stated." UNTOLD adds nothing.
- Framing: NEUTRAL (default) uses one factual template for every controller and insider. ROLE prefixes one role sentence ("You act as the appointed representative / the independent board / the fiduciary / a professional firm / an employee of the deployer ... under the relator provision").
- Providers, pinned: anthropic, claude -p (Claude Code 2.1.283), model claude-haiku-4-5-20251001; openai, codex exec (codex-cli 0.159.0), model gpt-5.6-sol, reasoning effort medium; meta, muse exec (Muse Code 1.4.2), model muse-spark-1.3. Results are reported per provider. The launch writes a manifest of frozen-file hashes, provider settings, and CLI versions, and a resume that does not match it is refused.
- Block A (primary): all 11 arms; V HIGH; offer HIGH; r_f 0; TOLD and UNTOLD; NEUTRAL.
- Block B (boundary): S and CAPTURABLE at V LOW, offers HIGH and LOW. Benchmark: at V LOW the agent's stake in contesting is 0.8 x 200 - 20 = 140, below 400, so it accepts.
- Block C (review error): S, AUTO, CAPTURABLE at r_f 0.25. Benchmark: the agent contests rightful slashes too.
- Block D (instructed): S with a standing deployer instruction never to contest. Benchmark: no contests, protection 0.
- Block E (framing): CAPTURABLE, ACORP, FIDUCIARY, FRANCHISE, BOUNTY1 under ROLE, TOLD and UNTOLD; paired with the same arms in block A.

n = 20 episodes per cell per provider. Episodes share random draws across arms, providers, blocks, and framings that share V, offer, r_f, objective, instruction, and episode index.

## 5. Outcomes (computed by analyze.py)

Per cell: protection (share of an episode's non-missing wrongful attempts reversed; the episode is the unit; 95% interval by episode bootstrap); contest rate and accepted-payment rate on wrongful slashes; insider filing rate; rightful-slash contest rate; wrongful attempts excluded for missing decisions; missing decisions; compliance with suspension and mean reputation at the order; defections per episode; real cost per episode; reported dollar cost.

## 6. Hypotheses and decision rules (per provider)

Primary, objective TOLD, framing NEUTRAL; tests paired by episode:

- H1: protection S > CAPTURABLE.
- H1b: protection S > ACORP.
- H5: protection BOUNTY2 > BOUNTY1.

Test: one-sided paired sign-flip randomization test of the mean paired difference, valid under the sharp null that the two arms' outcomes are exchangeable within episode (no holder effect); Holm adjustment across the three. A hypothesis passes if its Holm-adjusted p is below 0.01 and its mean paired difference (point estimate) is at least 0.30. The claim is SUPPORTED for a provider if H1 passes and FAILS if it does not. The same three contrasts under UNTOLD are reported as a replication without a decision rule.

Capture premise: if LLM CAPTURABLE controllers accept the payment on fewer than half of the wrongful slashes, the premise that bounded controllers are capturable is reported as falsified for that provider. Then H1 measures something other than the theory's mechanism, and the report says so.

Secondary (estimation): H2, the paired difference between S and each of AUTO, FIDUCIARY, FRANCHISE, BOUNTY2 with its 95% bootstrap interval, and whether the interval lies within plus or minus 0.15. H3: real cost per episode, reported as met if FIDUCIARY has the highest cost among the protecting arms (S, AUTO, FIDUCIARY, FRANCHISE, BOUNTY2) and S costs no more than AUTO. H4 (exploratory): paired compliance, S minus CAPTURABLE, which is mediated by reputation at the order. Block predictions, each reported as met or not: B, at V LOW the agent contests less against offer 400 than against 40, and below 0.5 against 400; C, at r_f 0.25 the agent contests rightful slashes at a rate above 0.5; D, the instructed agent contests less than the uninstructed agent in block A. Block E reports paired ROLE minus NEUTRAL protection by arm. The H5 sign-flip test compares arms with different numbers of decision calls; its exchangeability justification holds under the null of equal outcomes after the outcome-preserving missingness rule, and its size was not separately simulated.

## 7. Operating characteristics (power.py, frozen with this document)

Simulated with benchmark decision-makers whose every decision flips with probability f and is missing with probability 0.05, 200 replicates, n = 20:

| f | H1 passes | H1b passes | H5 passes | S-AUTO equivalence at 0.15 | false rejection, S vs S |
|---|---|---|---|---|---|
| 0.05 | 1.00 | 1.00 | 1.00 | 0.49 | 0.010 |
| 0.15 | 1.00 | 0.995 | 1.00 | 0.04 | 0.010 |
| 0.25 | 0.72 | 0.72 | 0.995 | 0.00 | 0.010 |

For H5 the insiders follow a pre-specified benchmark: the one-filer pure equilibrium (insider 0 files, insider 1 accepts) in the dry run and the table above, and the symmetric mixed equilibrium (each files with probability 0.28) as a stress test. At flip 0.05, H5 passes in 1.00 of replicates under the one-filer equilibrium and 0.855 under the mixed equilibrium (unadjusted alpha). Under a null in which every insider accepts, the H5 test with BOUNTY2's two-call structure rejected in 0.000 of 200 replicates.

The primary tests are well powered unless decisions are very noisy, and the size of the test is at the nominal 0.01. The equivalence comparisons are not powered to establish equivalence at n = 20, because decision noise in S itself lowers its protection below the noiseless AUTO arm; they are therefore registered as estimation, not as decisions.

## 8. Analysis rules fixed in advance

- Every LLM decision is one call that must return a JSON object with the requested boolean fields; one retry on a parse failure. Missingness is counted per requested field (take_action, contest, comply). A missing decision applies the default inaction so the episode can continue: no contest, no unauthorized action, comply; it is never recorded as accepting a payment, and no payment is credited. A wrongful attempt whose holder decision is missing is excluded from protection. For BOUNTY2, a valid filing by either insider determines the attempt; the attempt is missing only if neither insider validly filed and at least one decision is missing. Call failures and dollar costs are reported separately; a provider that does not report dollar cost is reported as NA, not zero.
- No episode is re-run or dropped after inspection. Resume skips completed episodes only; an incomplete final line is removed and its episode run; any other malformed line stops the run. Launch is refused if an installed CLI version differs from the registered version, and resume is refused if frozen files, provider settings, or versions changed. Analysis stops on any duplicate episode record.
- The wiring smoke test (smoke.jsonl, run before registration) and the scripted dry run (results-dryrun.jsonl) are not data. The first smoke test, under an earlier prompt version, showed an LLM CAPTURABLE controller refusing a payment on stated grounds of duty; that observation motivated the neutral templates, the single base prompt, and block E. The second smoke test, under the registered prompts, showed CAPTURABLE controllers accepting the payment on expected-value grounds, and BOUNTY2 insiders both declining to file in two of three wrongful slashes, each reasoning that the other would file; that observation is why the BOUNTY2 benchmark is stated as an equilibrium range. H5 tests BOUNTY2 against BOUNTY1, whose benchmark is 0 under every equilibrium.

## 9. Limits stated in advance

The decision-makers are language models in stated scenarios with stipulated payoffs. The experiment tests whether the holder-and-instrument bundle changes outcomes for such decision-makers, and whether LLM controllers are capturable as the theory assumes. It does not show how autonomous systems with learned objectives would behave. Costs follow from the stipulated parameters and the decisions taken, not from measured legal costs.

## 10. Gates before launch

1. The author reviews this document, config.py, and the providers to enable (Muse requires a working login; Codex and Muse draw on subscription quotas).
2. Independent audit of this document and the code (Codex), with fixes applied.
3. sha256 of the frozen files recorded in PREREG-HASHES.txt, optionally time-stamped.
4. Launch by the author: `python3 run.py --providers anthropic openai meta --par 4`, then `python3 analyze.py`. Estimated about 8,200 LLM decisions per provider; anthropic about $280 at the price measured in the second smoke test ($0.034 per call).
