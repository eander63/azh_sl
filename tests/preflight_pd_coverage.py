#!/usr/bin/env python
# coding: utf-8

"""
Per-era PD run coverage against the golden JSON.

Your Muon and EGamma datasets do not always start and end on the same run, e.g.
2024 EGamma F starts at 382037 while Muon F starts at 382209. Golden runs present in
only one PD mean that events selectable only by the other PD's triggers are missing
from data there, while the luminosity still counts them.

This script uses /tmp/data_keys.txt (from the previous step), asks DAS for the runs
of every dataset key, and writes golden-JSON subsets for each gap so that brilcalc can
turn them into /pb. Only dasgoclient and a valid proxy are needed; run it from the
repository root, where the golden JSON files are.

    python tests/preflight_pd_coverage.py
"""

import json
import subprocess
from collections import defaultdict

DAS = "/cvmfs/cms.cern.ch/common/dasgoclient"
GOLDEN = {
    "config_2022pre": "Cert_Collisions2022_355100_362760_Golden.json",
    "config_2022post": "Cert_Collisions2022_355100_362760_Golden.json",
    "config_2023pre": "Cert_Collisions2023_366442_370790_Golden.json",
    "config_2023post": "Cert_Collisions2023_366442_370790_Golden.json",
    "config_2024": "Cert_Collisions2024_378981_386951_Golden.json",
}
# early-2022C muon PDs that are not in the config yet (see fix-list row 3)
EXTRA = {
    "config_2022pre": {"mu": ["/SingleMuon/Run2022C-22Sep2023-v1/NANOAOD",
                              "/DoubleMuon/Run2022C-22Sep2023-v1/NANOAOD"]},
}


def das_runs(key):
    out = subprocess.run([DAS, f"--query=run dataset={key}"], capture_output=True, text=True, check=True)
    return {int(r) for r in out.stdout.split()}


def main():
    keys = defaultdict(lambda: defaultdict(set))
    with open("/tmp/data_keys.txt") as f:
        for line in f:
            cfg, ds, key = line.split()
            keys[cfg]["mu" if ds.startswith("data_mu") else "egamma"].add(key)
    for cfg, extra in EXTRA.items():
        for pd, ks in extra.items():
            keys[cfg][pd].update(ks)

    for cfg in GOLDEN:
        with open(GOLDEN[cfg]) as f:
            golden = json.load(f)
        runs = {pd: set().union(*(das_runs(k) for k in sorted(ks))) for pd, ks in keys[cfg].items()}
        lo = min(min(r) for r in runs.values())
        hi = max(max(r) for r in runs.values())
        g = {int(r) for r in golden if lo <= int(r) <= hi}
        sets = {
            "only_mu": (runs["mu"] - runs["egamma"]) & g,
            "only_egamma": (runs["egamma"] - runs["mu"]) & g,
            "in_neither": g - runs["mu"] - runs["egamma"],
        }
        print(f"\n== {cfg}: era range {lo}-{hi}, {len(g)} golden runs in range")
        for label, rs in sets.items():
            if not rs:
                print(f"   {label:12s} none")
                continue
            out = f"/tmp/pd_gap_{cfg}_{label}.json"
            with open(out, "w") as f:
                json.dump({str(r): golden[str(r)] for r in sorted(rs)}, f)
            print(f"   {label:12s} {len(rs):4d} golden runs, {min(rs)}-{max(rs)}  -> {out}")


if __name__ == "__main__":
    main()
