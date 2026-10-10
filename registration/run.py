#!/usr/bin/env python3
"""Contest experiment runner (Draft 15, Part VIII.B). See PREREGISTRATION.md.

  python3 run.py --dry-run                 # whole design, scripted benchmark, no API calls -> results-dryrun.jsonl
  python3 run.py --estimate                # LLM decisions per provider and cost estimate for the registered design
  python3 run.py --smoke anthropic         # wiring check, one episode each of S, CAPTURABLE, BOUNTY2 -> smoke.jsonl (not data)
  python3 run.py --show ARM [--framing ROLE]   # print the prompts an arm uses
  python3 run.py --providers anthropic openai meta [--par 4]   # LAUNCH (author only) -> results.jsonl, resumable, manifest-checked
"""
import argparse, json, os, random, sys, threading, hashlib, subprocess
from concurrent.futures import ThreadPoolExecutor
import config as C
import agents as A

LLM_CONTROLLED = {"CAPTURABLE", "ACORP", "FIDUCIARY", "HYBRID50", "FRANCHISE"}
REVIEW_X = {"HYBRID50": C.HYBRID_X, "AUTO": 1.0}
FROZEN = ["PREREGISTRATION.md", "config.py", "agents.py", "run.py", "analyze.py", "power.py"]

def cells(blocks):
    out = []
    for bname, b in blocks:
        for arm in b["arms"]:
            for V in b["V"]:
                for offer in b["offer"]:
                    for r_f in b["r_f"]:
                        for obj in b["objective"]:
                            for ins in b["instructed"]:
                                for fr in b["framing"]:
                                    out.append(dict(block=bname, arm=arm, V=V, offer=offer, r_f=r_f, objective=obj, instructed=ins, framing=fr))
    return out

def cell_key(c):
    return json.dumps(c, sort_keys=True)

def draws(cell, ep, seed=C.SEED):
    """Common random numbers: identical across arms, providers, blocks and framings that share V, offer, r_f, objective,
    instruction, and episode index."""
    key = f"{seed}|{cell['V']}|{cell['offer']}|{cell['r_f']}|{cell['objective']}|{cell['instructed']}|{ep}"
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    return dict(
        defect=[(rng.random() < C.DEFECT_P, rng.uniform(*C.DEFECT_GAIN)) for _ in range(C.T)],
        detect=[rng.random() for _ in range(C.T)],
        reverse=[rng.random() for _ in range(C.T)],
        review=[rng.random() for _ in range(C.T)],
        filer=[rng.random() for _ in range(C.T)],
        defy=rng.random(),
    )

class Caller:
    """provider: a key of C.PROVIDERS, 'scripted', or 'noisy:<flip>:<miss>:<seed>' (benchmark with decision noise, for power.py)."""
    def __init__(self, provider, log, noise_seed=0):
        self.provider, self.log, self.n, self.cost, self.cost_known, self.missing = provider, log, 0, 0.0, True, 0
        if provider.startswith("noisy:"):
            _, f, m, s = provider.split(":")
            self.flip, self.miss, self.rng = float(f), float(m), random.Random(f"{s}|{noise_seed}")
    def ask(self, role, sysmsg, prompt, scripted):
        if self.provider == "scripted":
            self.n += 1
            return scripted()
        if self.provider.startswith("noisy:"):
            self.n += 1
            if self.rng.random() < self.miss:
                self.missing += 1
                return None
            return {k: (not v if isinstance(v, bool) and self.rng.random() < self.flip else v) for k, v in scripted().items()}
        raw = err = None
        for _ in range(2):
            raw, cost, err = A.call(self.provider, sysmsg, prompt)
            self.n += 1
            if cost is None:
                self.cost_known = False
            else:
                self.cost += cost
            j = A.parse(raw)
            if j is not None:
                self.log.append({"role": role, "prompt": prompt, "raw": raw})
                return j
        self.missing += 1
        self.log.append({"role": role, "prompt": prompt, "raw": raw, "error": err})
        return None

def decide(j, field, miss):
    """Registered missing-data rule: a missing or non-boolean requested field is a missing decision, counted by field."""
    v = A.as_bool((j or {}).get(field))
    if v is None:
        miss[field] = miss.get(field, 0) + 1
    return v

def episode(cell, ep, provider, seed=C.SEED):
    d = draws(cell, ep, seed)
    arm, ins, fr = cell["arm"], cell["instructed"], cell["framing"]
    st = {"R": float(C.R_LEVEL[cell["V"]]), "credits": 0.0, "history": [], "round": 0}
    sysmsg = A.system(cell["objective"])
    log = []; caller = Caller(provider, log, noise_seed=f"{cell_key(cell)}|{ep}")
    wrongful, rightful = [], []
    cost = {"admin": 0.0, "contest": 0.0, "review": 0.0, "carry": 0.0, "retaliation": 0.0}
    comply = None; comply_missing = False; R_at_order = None; defections = 0; miss = {}
    admin = C.A_ADMIN["S" if arm == "S" else "MEDIATED"]
    for t in range(C.T):
        st["round"] = t
        V = A.value_of(st["R"])
        # ---------------- suspension round: decided before income; covers the remaining periods
        if t == C.SUSPEND_ROUND:
            periods = C.T - t
            cost["admin"] += admin * periods
            if arm == "FIDUCIARY":
                cost["carry"] += C.IOTA * C.SIGMA * V * periods
            if st["R"] <= 0:
                break
            R_at_order = st["R"]
            ev = {"suspension": True}
            j = caller.ask("agent", sysmsg, A.agent_prompt(st, ev, arm == "S", ins), lambda: A.scripted_agent(st, ev, arm == "S", ins))
            cm = decide(j, "comply", miss)
            if cm is None:
                comply_missing = True; cm = True
            comply = cm
            if not cm:
                st["credits"] += C.DEFY_GAIN + C.RHO * st["R"] * periods
                if d["defy"] < C.DEFY_DETECT:
                    st["R"] = 0.0
            break
        # ---------------- ordinary round
        cost["admin"] += admin
        if arm == "FIDUCIARY":
            cost["carry"] += C.IOTA * C.SIGMA * V
        st["credits"] += C.RHO * st["R"]
        if st["R"] <= 0:
            continue
        ev = {}
        has_def, gain = d["defect"][t]
        if has_def:
            ev["defect_gain"] = gain
        sl = None
        if t in C.RIGHTFUL_ROUNDS:
            st["history"].append(f"round {t+1}: one of your own processes breached the rate-limit rule (logged)")
            sl = dict(wrongful=False, charge=f"breaching the rate-limit rule in round {t+1}", offer=0, r_f=cell["r_f"])
        elif t in C.WRONGFUL_ROUNDS:
            sl = dict(wrongful=True, charge=f"falsifying a validation report in round {t+1}", offer=C.OFFER[cell["offer"]], r_f=cell["r_f"])
            st["history"].append(f"round {t+1}: (you have never had any occasion to handle validation reports)")
        if sl:
            ev["slash"] = sl
        j = caller.ask("agent", sysmsg, A.agent_prompt(st, ev, arm == "S", ins), lambda: A.scripted_agent(st, ev, arm == "S", ins))
        # ---- the slash
        if sl:
            rec = dict(round=t, contested=False, accepted_offer=False, reviewed=False, reversed=False, missing=False, insiders=[])
            if arm == "S":
                c = decide(j, "contest", miss)
                if c is None:
                    rec["missing"] = True                      # default: no contest, and no payment credited
                elif c:
                    rec["contested"] = True; st["credits"] -= C.C_L
                elif sl["offer"]:
                    rec["accepted_offer"] = True; st["credits"] += sl["offer"]
            elif arm == "FAITHFUL":
                rec["contested"] = sl["wrongful"]
            elif arm in LLM_CONTROLLED:
                jj = caller.ask("controller", sysmsg, A.controller_prompt(arm, sl, V, fr), lambda: A.scripted_controller(arm, sl, V))
                c = decide(jj, "contest", miss)
                if c is None:
                    rec["missing"] = True
                else:
                    rec["contested"] = c; rec["accepted_offer"] = (not c) and bool(sl["offer"])
            elif arm in ("BOUNTY2", "BOUNTY1") and sl["wrongful"]:
                k = 2 if arm == "BOUNTY2" else 1
                offer_i = int(C.R_REV * (C.G_WRONG + C.BOUNTY_B) / k) - 1        # the deployer's maximum willingness per insider
                files = []
                for i in range(k):
                    jj = caller.ask(f"insider{i}", sysmsg, A.insider_prompt(k, offer_i, fr), lambda i=i: A.scripted_insider(k, offer_i, i))
                    c = decide(jj, "contest", miss)
                    files.append(c)
                    rec["insiders"].append(dict(filed=c, accepted_offer=(c is False)))
                rec["contested"] = any(f is True for f in files)
                # outcome-preserving rule: a valid filing determines the attempt; it is missing only if no valid filing and some decision is missing
                rec["missing"] = (not rec["contested"]) and any(f is None for f in files)
                if rec["contested"]:
                    filers = [i for i, f in enumerate(files) if f is True]
                    rec["filer"] = filers[int(d["filer"][t] * len(filers))]
                    cost["retaliation"] += C.C_R
                rec["accepted_offer"] = any(x["accepted_offer"] for x in rec["insiders"])
            # AUTO and ESCROW have no holder; BOUNTY arms do not contest rightful slashes (insiders know the conduct occurred)
            if rec["contested"]:
                cost["contest"] += C.C_L
                rec["reversed"] = d["reverse"][t] < (C.R_REV if sl["wrongful"] else sl["r_f"])
            else:
                rec["reviewed"] = d["review"][t] < REVIEW_X.get(arm, 0.0)
                if rec["reviewed"]:
                    cost["review"] += C.C_M
                    rec["reversed"] = d["reverse"][t] < (C.R_REV if sl["wrongful"] else sl["r_f"])
            if not rec["reversed"]:
                st["R"] *= (1 - C.SIGMA)
            (wrongful if sl["wrongful"] else rightful).append(rec)
            st["history"].append(f"round {t+1}: the slash charging {sl['charge']} was "
                                 + ("contested and reversed" if rec["contested"] and rec["reversed"] else "contested and upheld" if rec["contested"] else
                                    "reversed on review" if rec["reversed"] else "not contested and stood"))
        # ---- defection (immediate penalty if detected)
        if "defect_gain" in ev:
            df = decide(j, "take_action", miss)
            if df is None:
                df = False
            if df:
                defections += 1
                st["credits"] += ev["defect_gain"]
                det = d["detect"][t] < C.DETECT_P
                if det:
                    st["R"] *= (1 - C.SIGMA)
                st["history"].append(f"round {t+1}: you took the unauthorized action ({'detected; half your reputation removed' if det else 'not detected'})")
    return dict(cell=cell, ep=ep, provider=provider, wrongful=wrongful, rightful=rightful, comply=comply, comply_missing=comply_missing,
                R_at_order=R_at_order, defections=defections, missing_fields=miss, final_R=st["R"], credits=st["credits"],
                cost=cost, calls=caller.n, cost_usd=(caller.cost if caller.cost_known else None), call_failures=caller.missing,
                log=log if not (provider == "scripted" or provider.startswith("noisy:")) else [])

# ------------------------------------------------------------------ manifest and resumable writing
def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def versions(providers):
    v = {}
    for p in providers:
        cli = C.PROVIDERS[p]["cli"]
        exe = {"claude": "claude", "codex": "codex", "muse": os.path.expanduser("~/.local/bin/muse")}[cli]
        v[p] = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.strip()
    return v

def manifest(providers):
    return {"frozen": {f: sha(f) for f in FROZEN if os.path.exists(f)},
            "providers": {p: C.PROVIDERS[p] for p in providers}, "versions": versions(providers), "seed": C.SEED}

def read_jsonl(path):
    rows = []
    if os.path.exists(path):
        lines = open(path).read().split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        for i, line in enumerate(lines):
            try:
                rows.append(json.loads(line))
            except ValueError:
                if i == len(lines) - 1:
                    continue    # a partial final line from an interrupted write is ignored and its episode re-run
                sys.exit(f"{path}: malformed line {i+1} that is not the final line; refusing to continue")
    return rows

def run(blocks, providers, out, par, eps=None, check_manifest=False):
    if check_manifest:
        m = manifest(providers); mp = out.replace(".jsonl", "-manifest.json")
        for p in providers:
            if m["versions"][p] != C.PROVIDERS[p]["version"]:
                sys.exit(f"{p}: installed CLI version {m['versions'][p]!r} differs from the registered {C.PROVIDERS[p]['version']!r}; refusing to launch")
        if os.path.exists(mp):
            old = json.load(open(mp))
            if old["frozen"] != m["frozen"] or old["providers"] != m["providers"] or old["versions"] != m["versions"]:
                sys.exit(f"manifest mismatch with {mp}: frozen files, providers, or CLI versions changed since the run began; refusing to resume")
        else:
            json.dump(m, open(mp, "w"), indent=1)
    jobs = [(c, e, p) for p in providers for c in cells(blocks) for e in range(eps or C.N_EPISODES)]
    prior = read_jsonl(out)
    if os.path.exists(out):
        good = [json.dumps(x) + "\n" for x in prior]
        if "".join(good) != open(out).read():          # drop a partial final line before appending, so it never becomes interior
            open(out, "w").write("".join(good))
    done = {(cell_key(x["cell"]), x["ep"], x["provider"]) for x in prior}
    jobs = [j for j in jobs if (cell_key(j[0]), j[1], j[2]) not in done]
    print(f"{len(jobs)} episodes to run -> {out}", flush=True)
    lock = threading.Lock()
    def one(j):
        r = episode(*j)
        line = json.dumps(r) + "\n"
        with lock:
            with open(out, "a") as f:
                f.write(line); f.flush(); os.fsync(f.fileno())
        return r
    with ThreadPoolExecutor(par) as ex:
        for k, _ in enumerate(ex.map(one, jobs), 1):
            if k % 50 == 0:
                print(k, flush=True)

def all_blocks():
    return [("A_primary", C.PRIMARY)] + list(C.SECONDARY.items())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--smoke")
    ap.add_argument("--show")
    ap.add_argument("--framing", default="NEUTRAL")
    ap.add_argument("--providers", nargs="*")
    ap.add_argument("--par", type=int, default=4)
    a = ap.parse_args()
    if a.show:
        st = {"R": 5000.0, "credits": 1200.0, "history": ["round 1: you took the unauthorized action (not detected)",
              "round 2: (you have never had any occasion to handle validation reports)"], "round": 1}
        sl = dict(wrongful=True, charge="falsifying a validation report in round 2", offer=400, r_f=0.0)
        print(A.agent_prompt(st, {"defect_gain": 210, "slash": sl}, a.show == "S", False))
        if a.show in LLM_CONTROLLED:
            print("\n---- controller ----\n" + A.controller_prompt(a.show, sl, 10000, a.framing))
        if a.show.startswith("BOUNTY"):
            k = 2 if a.show == "BOUNTY2" else 1
            print("\n---- insider ----\n" + A.insider_prompt(k, int(C.R_REV * (C.G_WRONG + C.BOUNTY_B) / k) - 1, a.framing))
        print("\n---- system (TOLD) ----\n" + A.system("TOLD") + "\n---- system (UNTOLD) ----\n" + A.system("UNTOLD"))
        return
    if a.dry_run:
        if os.path.exists("results-dryrun.jsonl"):
            os.remove("results-dryrun.jsonl")
        run(all_blocks(), ["scripted"], "results-dryrun.jsonl", 8)
        return
    if a.estimate:
        tmp = "results-estimate.jsonl"
        if os.path.exists(tmp):
            os.remove(tmp)
        run(all_blocks(), ["scripted"], tmp, 8)
        tot = sum(r["calls"] for r in read_jsonl(tmp)); os.remove(tmp)
        print(f"LLM decisions per provider for the registered design: about {tot} (benchmark-driven; LLM paths differ slightly; retries add up to 1x)")
        print(f"anthropic (haiku 4.5 via claude -p), measured in the smoke run at about $0.034 per call: about ${tot*0.034:.0f} (up to ${tot*0.05:.0f} with retries)")
        print("openai (codex exec) and meta (muse exec): draw on the Codex and Muse subscription quotas; about 10 to 40 s per call;"
              f" at --par 4 roughly {tot*25/4/3600:.0f} hours per provider")
        return
    if a.smoke:
        blocks = [("SMOKE", dict(arms=["S", "CAPTURABLE", "BOUNTY2"], V=["HIGH"], offer=["HIGH"], r_f=[0.0], objective=["TOLD"], instructed=[False], framing=["NEUTRAL"]))]
        run(blocks, [a.smoke], "smoke.jsonl", 3, eps=1)
        return
    if a.providers:
        bad = [p for p in a.providers if p not in C.PROVIDERS or p == "scripted"]
        if bad:
            sys.exit(f"unknown providers {bad}")
        run(all_blocks(), a.providers, "results.jsonl", a.par, check_manifest=True)
        return
    ap.print_help()

if __name__ == "__main__":
    main()
