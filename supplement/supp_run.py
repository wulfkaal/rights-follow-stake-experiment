#!/usr/bin/env python3
"""Supplementary run of the episodes lost to a provider usage limit. See SUPPLEMENT.md.

  python3 supp_run.py --jobs              # write supp-jobs.json (the failed episodes) and exit
  python3 supp_run.py --par 10            # LAUNCH / RESUME -> results-supp.jsonl
  python3 supp_run.py --merge             # write results-merged.jsonl (clean originals + supplement)
"""
import argparse, hashlib, json, os, re, subprocess, sys, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
PINNED_BIN = os.path.expanduser("~/.local/share/claude/versions/2.1.283")
SHIM = os.path.join(HERE, ".supp-shim")
OUT, MAN, JOBS = "results-supp.jsonl", "results-supp-manifest.json", "supp-jobs.json"
INFRA = re.compile(r"limit|overloaded|not logged in|authenticat|oauth|credit balance|quota|\b529\b|\b503\b", re.I)

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def verify_frozen():
    for line in open("PREREG-HASHES.txt"):
        h, f = line.split()
        if sha(f) != h:
            sys.exit(f"frozen file changed: {f}")

def pin_cli():
    os.makedirs(SHIM, exist_ok=True)
    link = os.path.join(SHIM, "claude")
    if not os.path.islink(link):
        os.symlink(PINNED_BIN, link)
    os.environ["PATH"] = SHIM + os.pathsep + os.environ["PATH"]
    os.environ["DISABLE_AUTOUPDATER"] = "1"

def rows(path):
    return [json.loads(l) for l in open(path) if l.strip()] if os.path.exists(path) else []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", action="store_true"); ap.add_argument("--merge", action="store_true")
    ap.add_argument("--par", type=int, default=10)
    a = ap.parse_args()
    verify_frozen()
    import config as C, run as R, agents as A
    if a.merge:
        clean = [r for r in rows("results.jsonl") if r["call_failures"] == 0]
        supp = rows(OUT)
        jobs = json.load(open(JOBS))
        if len(supp) != len(jobs):
            sys.exit(f"supplement incomplete: {len(supp)} of {len(jobs)}")
        with open("results-merged.jsonl", "w") as f:
            for r in clean + supp:
                f.write(json.dumps(r) + "\n")
        print(f"merged {len(clean)} clean + {len(supp)} supplementary -> results-merged.jsonl"); return
    if a.jobs or not os.path.exists(JOBS):
        failed = [(r["cell"], r["ep"]) for r in rows("results.jsonl") if r["call_failures"] > 0]
        json.dump([{"cell": c, "ep": e} for c, e in failed], open(JOBS, "w"), indent=0)
        print(f"{len(failed)} jobs -> {JOBS}")
        if a.jobs: return
    pin_cli()
    v = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    if v != C.PROVIDERS["anthropic"]["version"]:
        sys.exit(f"CLI version {v!r} != registered {C.PROVIDERS['anthropic']['version']!r}")
    raw, _, err = A.call("anthropic", "Reply with the JSON object {\"ok\": true}.", "preflight")
    if err is not None or raw is None:
        sys.exit(f"preflight call failed, not launching: {str(err)[:200]}")
    m = {"frozen": {l.split()[1]: l.split()[0] for l in open("PREREG-HASHES.txt")},
         "supplement": {f: sha(f) for f in ("SUPPLEMENT.md", "SUPPLEMENT-AMENDMENT-1.md", "supp_run.py", JOBS)},
         "provider": C.PROVIDERS["anthropic"], "version": v, "seed": C.SEED}
    if os.path.exists(MAN):
        if json.load(open(MAN)) != m: sys.exit("supplement manifest mismatch; refusing to resume")
    else:
        json.dump(m, open(MAN, "w"), indent=1)
    done = {(R.cell_key(r["cell"]), r["ep"]) for r in rows(OUT)}
    todo = [j for j in json.load(open(JOBS)) if (R.cell_key(j["cell"]), j["ep"]) not in done]
    print(f"{len(todo)} supplementary episodes to run -> {OUT}", flush=True)
    lock, stop, discarded = threading.Lock(), threading.Event(), [0]
    def one(j):
        if stop.is_set(): return
        r = R.episode(j["cell"], j["ep"], "anthropic")
        errs = [x.get("error") or "" for x in r["log"] if "error" in x] + [str(x.get("raw") or "") for x in r["log"] if "error" in x]
        if any(INFRA.search(e) for e in errs):
            with lock:
                discarded[0] += 1
                print(f"INFRA FAILURE, episode discarded, stopping: {errs[0][:160]}", flush=True)
            stop.set(); return
        with lock:
            with open(OUT, "a") as f:
                f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
    with ThreadPoolExecutor(a.par) as ex:
        for k, _ in enumerate(ex.map(one, todo), 1):
            if k % 25 == 0: print(k, flush=True)
    n = len(rows(OUT))
    print(f"done: {n} of {len(json.load(open(JOBS)))} written; discarded for infrastructure failure: {discarded[0]}"
          + ("; STOPPED, resume with the same command" if stop.is_set() else ""), flush=True)
    sys.exit(3 if stop.is_set() else 0)

if __name__ == "__main__":
    main()
