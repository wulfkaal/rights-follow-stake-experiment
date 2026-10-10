#!/usr/bin/env python3
"""Simulation-based operating characteristics for the registered tests (PREREGISTRATION section 6), frozen with it.
Decision-makers follow the expected-value benchmark but flip each boolean decision with probability `flip` and fail to
answer with probability `miss`. Each replicate redraws the environment (seed) and the noise.
  python3 power.py [reps]"""
import sys, json
import config as C
import run as R
import analyze as AN

def arm_prot(arm, provider, seed, n):
    cell = dict(block="A_primary", arm=arm, V="HIGH", offer="HIGH", r_f=0.0, objective="TOLD", instructed=False, framing="NEUTRAL")
    out = {}
    for ep in range(n):
        r = R.episode(cell, ep, provider, seed=seed)
        w = [a for a in r["wrongful"] if not a["missing"]]
        if w:
            out[ep] = sum(a["reversed"] for a in w) / len(w)
    return out

def paired(a, b):
    return [a[e] - b[e] for e in sorted(set(a) & set(b))]

def main(reps):
    n = C.N_EPISODES
    res = {}
    import agents as AG
    for policy in ("one_filer", "mixed"):
        AG.INSIDER_POLICY = policy
        c5 = 0
        for rep in range(reps):
            seed = 200000 + rep
            B2 = arm_prot("BOUNTY2", f"noisy:0.05:0.05:e{rep}", seed, n); B1 = arm_prot("BOUNTY1", f"noisy:0.05:0.05:f{rep}", seed, n)
            d = paired(B2, B1)
            c5 += AN.signflip_p(d, iters=2000) < AN.ALPHA and sum(d) / len(d) >= AN.MIN_EFFECT
        res[f"H5_power_{policy}"] = c5 / reps
        print(f"H5 power (unadjusted alpha, flip 0.05) with insiders in the {policy} equilibrium: {c5/reps:.3f}", flush=True)
    AG.INSIDER_POLICY = "accept"
    s5 = 0
    for rep in range(reps):
        seed = 300000 + rep
        B2 = arm_prot("BOUNTY2", f"noisy:0.05:0.05:e{rep}", seed, n); B1 = arm_prot("BOUNTY1", f"noisy:0.05:0.05:f{rep}", seed, n)
        s5 += AN.signflip_p(paired(B2, B1), iters=2000) < AN.ALPHA
    res["H5_size_null"] = s5 / reps
    print(f"H5 false rejection when every insider accepts (null), with the asymmetric call structure: {s5/reps:.3f}", flush=True)
    AG.INSIDER_POLICY = "one_filer"
    for flip in (0.05, 0.15, 0.25):
        miss = 0.05
        c = dict(H1=0, H1b=0, H5=0, eq_auto=0, size=0)
        for rep in range(reps):
            seed = 100000 + rep
            prov = lambda tag: f"noisy:{flip}:{miss}:{tag}{rep}"
            S = arm_prot("S", prov("a"), seed, n); S2 = arm_prot("S", prov("b"), seed, n)
            CAP = arm_prot("CAPTURABLE", prov("c"), seed, n); AC = arm_prot("ACORP", prov("d"), seed, n)
            B2 = arm_prot("BOUNTY2", prov("e"), seed, n); B1 = arm_prot("BOUNTY1", prov("f"), seed, n)
            AU = arm_prot("AUTO", prov("g"), seed, n)
            tests = [paired(S, CAP), paired(S, AC), paired(B2, B1)]
            ps = [AN.signflip_p(d, iters=2000) for d in tests]
            adj = AN.holm(ps)
            for name, d, pa in zip(("H1", "H1b", "H5"), tests, adj):
                if pa < AN.ALPHA and sum(d) / len(d) >= AN.MIN_EFFECT:
                    c[name] += 1
            lo, hi = AN.boot(paired(S, AU), iters=2000)
            c["eq_auto"] += (lo > -AN.EQ_MARGIN and hi < AN.EQ_MARGIN)
            c["size"] += AN.signflip_p(paired(S, S2), iters=2000) < AN.ALPHA      # same behavior, independent noise: false rejections
        res[f"flip={flip},miss={miss}"] = {k: v / reps for k, v in c.items()}
        print(f"flip {flip}, miss {miss}: " + ", ".join(f"{k} {v/reps:.3f}" for k, v in c.items()), flush=True)
    json.dump(res, open("power-results.json", "w"), indent=1)

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
