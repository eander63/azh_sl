#!/usr/bin/env python3
# coding: utf-8
"""
Probe the local /data/dust area for MuonScaRe JSON files and check whether
the expected per-era files exist. Run on DESY.

Prints the path of every existing candidate, plus what the patched
``azh/config/config_run3.py`` is *expecting* per era. Use the output to
update the path table in the config (or to fetch missing files from
https://github.com/cms-muon-pog/MuonScaRe).
"""
from __future__ import annotations

import glob
import os
import re

# What the patched config will look for (per era):
EXPECTED = {
    "2022preEE":   "/data/dust/user/eranders/AZHtt/data/json/muon_scalesmearing_2022preEE.json.gz",
    "2022postEE":  "/data/dust/user/eranders/AZHtt/data/json/muon_scalesmearing_2022postEE.json.gz",
    "2023preBPix": "/data/dust/user/eranders/AZHtt/data/json/muon_scalesmearing_2023preBPix.json.gz",
    "2023postBPix":"/data/dust/user/eranders/AZHtt/data/json/muon_scalesmearing_2023postBPix.json.gz",
}

SEARCH_DIRS = [
    "/data/dust/user/eranders/AZHtt/data/json",
    "/data/dust/user/eranders",
]


def main():
    print("=== Files matching *muon_scalesmearing* under common locations ===")
    found = []
    for root in SEARCH_DIRS:
        if not os.path.isdir(root):
            print(f"  [skip] {root} (not a directory)")
            continue
        for path in glob.iglob(os.path.join(root, "**", "*muon_scalesmearing*"), recursive=True):
            size = os.path.getsize(path)
            print(f"  {path}   ({size:,} bytes)")
            found.append(path)

    print("\n=== Per-era expectations from the patched config ===")
    for era, path in EXPECTED.items():
        exists = os.path.exists(path)
        badge = "OK  " if exists else "MISS"
        print(f"  [{badge}] {era:14s} -> {path}")

    print("\n=== Tip ===")
    print("Official per-era JSONs: https://github.com/cms-muon-pog/MuonScaRe")
    print("Or check the jsonpog-integration mirror:")
    print("  ls /cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/")

if __name__ == "__main__":
    main()
