#!/usr/bin/env python3
"""
Quick consistency checks of the processed store, without reading event data.

Only parquet footers (metadata) are read, plus one small column from one file
per MC dataset, so a full run over all eras takes minutes, not hours.

Checks, per config:
  1. files       every merged reduced and produced file is non-empty and has a
                 readable footer (catches empty and truncated files)
  2. complete    every MC dataset has all passes, every data dataset nominal
  3. rows        merged reduced events and produced columns have the same
                 number of rows per dataset and pass (outputs belong together)
  4. shifts      event counts of the lepton-shift passes are within a few
                 percent of nominal (a shift that changed nothing, or far too
                 much, shows up here)
  5. weights     normalization_weight is finite and non-zero (MC, one file per
                 dataset)
  6. data        selected data events per fb^-1, for comparing eras

Damage inside a file (corrupted data pages) is not seen by footer reads, but a
completed cf.ProduceColumns has read all of its merged inputs, and filling
histograms reads all produced outputs, so such damage surfaces there.

Usage (inside the analysis environment, which provides pyarrow):
    python scripts/quick_checks.py                      # all five eras
    python scripts/quick_checks.py --configs config_2024
"""

import argparse
import glob
import math
import os
import sys
from collections import defaultdict

import pyarrow.parquet as pq

PASSES = ["nominal"] + [
    f"{v}_{d}" for v in ("e_scale", "e_smear", "mu_scale", "mu_resol") for d in ("up", "down")
]
CONFIGS = ["config_2022pre", "config_2022post", "config_2023pre", "config_2023post", "config_2024"]
LUMI_FB = {  # brilcalc, see the README
    "config_2022pre": 7.9895, "config_2022post": 26.6749, "config_2023pre": 17.9642,
    "config_2023post": 9.6767, "config_2024": 109.7103,
}


def scan(store, task, cfg, version, sub_pattern):
    """{(dataset, pass): {"files": n, "rows": n, "bad": [(path, reason)], "example": path}}"""
    out = {}
    root = os.path.join(store, task, cfg)
    if not os.path.isdir(root):
        return out
    for ds in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, ds)):
            continue
        for p in sorted(os.listdir(os.path.join(root, ds))):
            files = sorted(glob.glob(os.path.join(root, ds, p, "**", sub_pattern, version, "*.parquet"), recursive=True))
            info = {"files": len(files), "rows": 0, "bad": [], "example": files[0] if files else None}
            for f in files:
                try:
                    if os.path.getsize(f) == 0:
                        raise ValueError("empty file")
                    info["rows"] += pq.ParquetFile(f).metadata.num_rows
                except Exception as e:
                    info["bad"].append((f, f"{type(e).__name__}: {str(e)[:70]}"))
            if files:
                out[(ds, p)] = info
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", default=os.path.expandvars("$CF_DATA/cf_store/analysis_azh"))
    ap.add_argument("--version", default="v9")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--producer", default="default", help="producer name in the store path (prod__<name>)")
    ap.add_argument("--shift-tolerance", type=float, default=0.05, help="max. relative event-count change of a lepton-shift pass")
    args = ap.parse_args()

    if "$" in args.store or not os.path.isdir(args.store):
        sys.exit(f"store not found: {args.store} (set CF_DATA or pass --store)")

    problems, warnings = [], []
    for cfg in args.configs.split(","):
        print(f"\n===== {cfg}")
        merged = scan(args.store, "cf.MergeReducedEvents", cfg, args.version, "")
        produced = scan(args.store, "cf.ProduceColumns", cfg, args.version, f"prod__{args.producer}")
        if not produced:
            produced = scan(args.store, "cf.ProduceColumns", cfg, args.version, "")
            if produced:
                warnings.append(f"{cfg}: no 'prod__{args.producer}' directories, counted all producers")
        if not merged and not produced:
            problems.append(f"{cfg}: no outputs found at version {args.version}")
            continue

        # 1. unreadable or empty files
        n_files = sum(i["files"] for d in (merged, produced) for i in d.values())
        bad = [b for d in (merged, produced) for i in d.values() for b in i["bad"]]
        print(f"  files:    {n_files} checked, {len(bad)} empty or unreadable")
        for f, why in bad[:20]:
            problems.append(f"{cfg}: broken file {f.split('analysis_azh/')[-1]} ({why})")

        # 2. completeness
        datasets = sorted({ds for ds, _ in produced} | {ds for ds, _ in merged})
        mc = [d for d in datasets if not d.startswith("data_")]
        data = [d for d in datasets if d.startswith("data_")]
        missing = [(d, p) for d in mc for p in PASSES if (d, p) not in produced]
        missing += [(d, "nominal") for d in data if (d, "nominal") not in produced]
        print(f"  complete: {len(mc)} MC x {len(PASSES)} passes, {len(data)} data; {len(missing)} missing")
        for d, p in missing:
            problems.append(f"{cfg}: no production output for {d} / {p}")

        # 3. merged vs produced rows
        mismatch = [(k, merged[k]["rows"], produced[k]["rows"]) for k in produced
                    if k in merged and merged[k]["rows"] != produced[k]["rows"] and not merged[k]["bad"] and not produced[k]["bad"]]
        print(f"  rows:     {len(mismatch)} dataset/pass combinations where merged and produced row counts differ")
        for (d, p), m, n in mismatch:
            problems.append(f"{cfg}: {d} / {p}: {m} merged rows vs {n} produced rows")

        # 4. shifted vs nominal event counts
        out_of_range = []
        for d in mc:
            nom = produced.get((d, "nominal"), {}).get("rows", 0)
            for p in PASSES[1:]:
                if nom and (d, p) in produced:
                    r = produced[(d, p)]["rows"] / nom
                    if abs(r - 1) > args.shift_tolerance:
                        out_of_range.append((d, p, r))
        print(f"  shifts:   {len(out_of_range)} passes outside +-{100 * args.shift_tolerance:.0f}% of nominal")
        for d, p, r in out_of_range:
            warnings.append(f"{cfg}: {d} / {p} has {r:.3f} x the nominal event count")

        # 5. normalization weights (one file per MC dataset)
        bad_w = []
        for d in mc:
            ex = produced.get((d, "nominal"), {}).get("example")
            if not ex:
                continue
            try:
                w = pq.read_table(ex, columns=["normalization_weight"]).column(0).to_pylist()
                if not w or any((x is None) or (not math.isfinite(x)) for x in w) or all(x == 0 for x in w):
                    bad_w.append(d)
            except Exception as e:
                bad_w.append(f"{d} ({type(e).__name__})")
        print(f"  weights:  {len(mc) - len(bad_w)} of {len(mc)} MC datasets with finite, non-zero normalization_weight")
        for d in bad_w:
            problems.append(f"{cfg}: normalization_weight not finite/non-zero in {d}")

        # 6. data yield per fb^-1
        n_data = sum(produced[(d, "nominal")]["rows"] for d in data if (d, "nominal") in produced)
        if n_data and cfg in LUMI_FB:
            print(f"  data:     {n_data:,} selected events = {n_data / LUMI_FB[cfg] / 1e6:.2f} M per fb^-1")

    print("\n===== summary")
    for w in warnings:
        print("  WARN ", w)
    for p in problems:
        print("  FAIL ", p)
    if not problems:
        print("  all checks passed" + (f" ({len(warnings)} warnings)" if warnings else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
