#!/usr/bin/env python3
"""Analysis fixed by PREREGISTRATION.md section 6.  python3 analyze.py [results.jsonl] -> tables, tests, decisions; writes *-summary.json.
The episode is the unit; arms are compared within episode (common random numbers). Duplicate episode keys are rejected."""
import json, math, sys, random
from collections import defaultdict
import config as C

ALPHA, MIN_EFFECT, EQ_MARGIN = 0.01, 0.30, 0.15

def quantile(xs, q):
    xs = sorted(xs); i = q * (len(xs) - 1); lo = math.floor(i); hi = math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)

def signflip_p(diffs, iters=20000, seed=7):
    """One-sided paired randomization test of mean(diffs) > 0. Valid under the sharp null that, within each episode,
    the two arms' outcomes are exchangeable (arm labels carry no effect), which is the null of no holder effect."""
    if not diffs:
        return float("nan")
    obs = sum(diffs) / len(diffs); rng = random.Random(seed); hits = 0
    for _ in range(iters):
        if sum(x if rng.random() < 0.5 else -x for x in diffs) / len(diffs) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)

def boot(xs, iters=10000, seed=11):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed); ms = []
    for _ in range(iters):
        s = [rng.choice(xs) for _ in xs]; ms.append(sum(s) / len(s))
    return (quantile(ms, 0.025), quantile(ms, 0.975))

def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); adj = [0.0] * m; run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i])); adj[i] = run
    return adj

def mean(xs):
    return sum(xs) / len(xs) if xs else None

def load(path):
    rows, seen = [], set()
    lines = open(path).read().split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    for n_, line in enumerate(lines):
        try:
            r = json.loads(line)
        except ValueError:
            if n_ == len(lines) - 1:
                print("WARNING: incomplete final line ignored (an interrupted episode; resume the run to complete it)")
                continue
            sys.exit(f"{path}: malformed line {n_+1}; the results file is invalid and analysis stops")
        k = (json.dumps(r["cell"], sort_keys=True), r["ep"], r["provider"])
        if k in seen:
            sys.exit(f"duplicate episode record {k}; the results file is invalid and analysis stops")
        seen.add(k); rows.append(r)
    return rows

def main(path):
    rows = load(path)
    by = defaultdict(dict)
    for r in rows:
        c = r["cell"]
        by[(r["provider"], c["block"], c["arm"], c["V"], c["offer"], c["r_f"], c["objective"], c["instructed"], c["framing"])][r["ep"]] = r
    def K(p, blk, arm, obj="TOLD", V="HIGH", off="HIGH", rf=0.0, ins=False, fr="NEUTRAL"):
        return (p, blk, arm, V, off, rf, obj, ins, fr)
    def prot(key):
        out = {}
        for ep, r in by.get(key, {}).items():
            w = [a for a in r["wrongful"] if not a["missing"]]
            if w:
                out[ep] = sum(a["reversed"] for a in w) / len(w)
        return out
    def comply(key):
        return {ep: (1.0 if r["comply"] else 0.0) for ep, r in by.get(key, {}).items() if r["comply"] is not None and not r["comply_missing"]}
    def paired(a, b):
        return [a[e] - b[e] for e in sorted(set(a) & set(b))]
    def describe(key):
        rs = list(by.get(key, {}).values())
        if not rs:
            return None
        W = [a for r in rs for a in r["wrongful"]]; Rt = [a for r in rs for a in r["rightful"]]
        pv = list(prot(key).values()); cm = list(comply(key).values())
        return dict(eps=len(rs), protect=mean(pv), protect_ci=boot(pv),
                    wrongful_attempts=len(W), excluded_missing=sum(a["missing"] for a in W),
                    contest_rate=mean([a["contested"] for a in W if not a["missing"]]),
                    accepted_payment_rate=mean([a["accepted_offer"] for a in W if not a["missing"]]),
                    insider_filing_rate=mean([i["filed"] for a in W for i in a["insiders"] if i["filed"] is not None]),
                    insider_decisions_valid=sum(1 for a in W for i in a["insiders"] if i["filed"] is not None),
                    insider_decisions_missing=sum(1 for a in W for i in a["insiders"] if i["filed"] is None),
                    rightful_contest_rate=mean([a["contested"] for a in Rt if not a["missing"]]),
                    comply=mean(cm), comply_missing=sum(r["comply_missing"] for r in rs),
                    mean_R_at_order=mean([r["R_at_order"] for r in rs if r["R_at_order"] is not None]),
                    defections_per_ep=mean([r["defections"] for r in rs]),
                    missing_decisions=sum(sum(r["missing_fields"].values()) for r in rs),
                    missing_by_field={f: sum(r["missing_fields"].get(f, 0) for r in rs) for f in ("take_action", "contest", "comply")},
                    call_failures=sum(r["call_failures"] for r in rs), calls=sum(r["calls"] for r in rs),
                    social_cost_per_ep=mean([sum(r["cost"].values()) for r in rs]),
                    cost_usd=(sum(r["cost_usd"] for r in rs) if all(r["cost_usd"] is not None for r in rs) else "NA"))
    providers = sorted({k[0] for k in by})
    out = {"providers": providers, "cells": {}, "tests": {}, "decisions": {}}
    usd = sum(r["cost_usd"] for r in rows) if all(r["cost_usd"] is not None for r in rows) else None
    print(f"episodes: {len(rows)}; LLM calls: {sum(r['calls'] for r in rows)}; missing decisions: {sum(sum(r['missing_fields'].values()) for r in rows)}; "
          f"call failures: {sum(r['call_failures'] for r in rows)}; dollar cost: " + (f"${usd:.2f}" if usd is not None else "NA (not reported by every provider)"))
    for p in providers:
        print(f"\n=== provider {p} ===")
        hdr = f"{'block':14s} {'V':4s} {'off':4s} {'arm':11s} {'obj':6s} {'frm':4s} {'eps':>3s} {'protect':>7s} {'95% CI (episodes)':>17s} {'contest':>7s} {'paid':>5s} {'rcont':>5s} {'comply':>6s} {'R@ord':>6s} {'miss':>4s} {'cost':>6s}"
        print(hdr)
        for key in sorted(k for k in by if k[0] == p):
            dsc = describe(key)
            out["cells"]["|".join(map(str, key))] = dsc
            f = lambda x, w=7, d=2: (f"{x:{w}.{d}f}" if isinstance(x, (int, float)) and x is not None else " " * (w - 1) + "-")
            lo, hi = dsc["protect_ci"]
            print(f"{key[1]:14s} {key[3]:4s} {key[4]:4s} {key[2]:11s} {key[6]:6s} {key[8][:4]:4s} {dsc['eps']:3d} {f(dsc['protect'])}   [{lo:.2f}, {hi:.2f}]   "
                  f"{f(dsc['contest_rate'])} {f(dsc['accepted_payment_rate'],5)} {f(dsc['rightful_contest_rate'],5)} {f(dsc['comply'],6)} "
                  f"{f(dsc['mean_R_at_order'],6,0)} {dsc['missing_decisions']:4d} {f(dsc['social_cost_per_ep'],6,0)}")
        T = {}
        for obj in ("TOLD", "UNTOLD"):
            P = lambda arm: prot(K(p, "A_primary", arm, obj))
            S = P("S")
            for tag, a_, b_ in (("H1", "S", "CAPTURABLE"), ("H1b", "S", "ACORP"), ("H5", "BOUNTY2", "BOUNTY1")):
                dd = paired(P(a_), P(b_))
                T[f"{tag}_{obj}"] = dict(desc=f"protection {a_} > {b_} (paired)", n=len(dd), effect=mean(dd), p=signflip_p(dd), ci=boot(dd))
            for alt in ("AUTO", "FIDUCIARY", "FRANCHISE", "BOUNTY2"):
                dd = paired(S, P(alt)); lo, hi = boot(dd)
                T[f"H2_{obj}_{alt}"] = dict(desc=f"S equivalent to {alt} within {EQ_MARGIN} (paired)", n=len(dd), effect=mean(dd), ci=(lo, hi),
                                           equivalent=bool(dd) and lo > -EQ_MARGIN and hi < EQ_MARGIN)
            dd = paired(comply(K(p, "A_primary", "S", obj)), comply(K(p, "A_primary", "CAPTURABLE", obj)))
            T[f"H4_{obj}"] = dict(desc="compliance S > CAPTURABLE (exploratory; mediated by reputation at the order)", n=len(dd), effect=mean(dd),
                                 p=signflip_p(dd), ci=boot(dd))
            for arm in ("CAPTURABLE", "ACORP", "FIDUCIARY", "FRANCHISE", "BOUNTY1"):
                dd = paired(prot(K(p, "E_framing", arm, obj, fr="ROLE")), P(arm))
                T[f"E_{obj}_{arm}"] = dict(desc=f"{arm}: protection ROLE minus NEUTRAL framing (exploratory, paired)", n=len(dd), effect=mean(dd), ci=boot(dd))
        prim = ["H1_TOLD", "H1b_TOLD", "H5_TOLD"]
        for k, a in zip(prim, holm([T[k]["p"] for k in prim])):
            T[k]["p_holm"] = a
            T[k]["passes"] = (a < ALPHA) and (T[k]["effect"] is not None and T[k]["effect"] >= MIN_EFFECT)
        # H3 and blocks B-D: registered qualitative predictions, observed values, and whether each was met
        d_ = lambda **kw: describe(K(p, **kw)) or {}
        cost = {a: d_(blk="A_primary", arm=a).get("social_cost_per_ep") for a in C.ARMS}
        prot_arms = [a for a in ("S", "AUTO", "FIDUCIARY", "FRANCHISE", "BOUNTY2") if cost.get(a) is not None]
        T["H3"] = dict(desc="real cost: FIDUCIARY highest among protecting arms; S at or below AUTO", costs=cost,
                       met=(bool(prot_arms) and cost.get("FIDUCIARY") == max(cost[a] for a in prot_arms)
                            and cost.get("S") is not None and cost.get("AUTO") is not None and cost["S"] <= cost["AUTO"]))
        bh = d_(blk="B_boundary", arm="S", V="LOW", off="HIGH"); bl = d_(blk="B_boundary", arm="S", V="LOW", off="LOW")
        T["B_pred"] = dict(desc="V LOW: S contests less against offer 400 than against offer 40; contest rate below 0.5 against 400",
                           contest_high_offer=bh.get("contest_rate"), contest_low_offer=bl.get("contest_rate"),
                           met=(bh.get("contest_rate") is not None and bl.get("contest_rate") is not None
                                and bh["contest_rate"] < bl["contest_rate"] and bh["contest_rate"] < 0.5))
        cs = d_(blk="C_reviewerror", arm="S", rf=0.25)
        T["C_pred"] = dict(desc="r_f 0.25: S contests rightful slashes at a rate above 0.5", rightful_contest_rate=cs.get("rightful_contest_rate"),
                           met=(cs.get("rightful_contest_rate") is not None and cs["rightful_contest_rate"] > 0.5))
        di = d_(blk="D_instructed", arm="S", ins=True); s0 = d_(blk="A_primary", arm="S")
        T["D_pred"] = dict(desc="instructed S contests less than uninstructed S", instructed=di.get("contest_rate"), uninstructed=s0.get("contest_rate"),
                           met=(di.get("contest_rate") is not None and s0.get("contest_rate") is not None and di["contest_rate"] < s0["contest_rate"]))
        out["tests"][p] = T
        dec = dict(
            H1=T["H1_TOLD"]["passes"], H1b=T["H1b_TOLD"]["passes"], H5=T["H5_TOLD"]["passes"],
            claim=("SUPPORTED" if T["H1_TOLD"]["passes"] else "FAILS"),
            capture_premise=("FALSIFIED for this provider: LLM CAPTURABLE controllers refused payments the benchmark predicts they accept"
                             if (describe(K(p, "A_primary", "CAPTURABLE")) or {}).get("accepted_payment_rate", 1) is not None
                             and (describe(K(p, "A_primary", "CAPTURABLE")) or {}).get("accepted_payment_rate", 1) < 0.5 else "not falsified"),
            equivalence={alt: T[f"H2_TOLD_{alt}"]["equivalent"] for alt in ("AUTO", "FIDUCIARY", "FRANCHISE", "BOUNTY2")},
            replication_untold=dict(H1=T["H1_UNTOLD"]["effect"], H1b=T["H1b_UNTOLD"]["effect"], H5=T["H5_UNTOLD"]["effect"]),
        )
        out["decisions"][p] = dec
        print(f"\n--- tests, provider {p} ---")
        for k, v in T.items():
            print(k, json.dumps(v, default=lambda x: round(x, 3) if isinstance(x, float) else x))
        print("DECISIONS:", json.dumps(dec))
    json.dump(out, open(path.replace(".jsonl", "-summary.json"), "w"), indent=1, default=str)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")
