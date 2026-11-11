#!/usr/bin/env python
# coding: utf-8

"""
Empirical check of TrigObj filter-bit definitions, using the NanoAOD files already
copied to /data/dust. No law, no columnflow: uproot + awkward only.

For every HLT path and every candidate bit definition this prints

    eff  = P(offline-style leg match | HLT path fired)   -> should be ~1.00
    fake = P(leg match | HLT path NOT fired)             -> should be ~0

A correct definition has eff close to 1 and small fake. A bit that does not exist in
that NanoAOD version gives eff = 0. The leg logic mirrors azh/selection/trigger.py:
each leg needs >= 1 TrigObj with the right |id| and pt, and for a list of masks,
every mask must share at least one bit with filterBits (AND over masks, OR within).

Each candidate is evaluated with three TrigObj pt requirements: the HLT thresholds
("hlt"), the leg min_pt currently in triggers.py ("config"), and none ("none"), so that
losses from the bit definition and from the TrigObj pt cut can be told apart.
Files matching mc_*.root are included, which gives the data-vs-MC comparison.

    source setup.sh
    source modules/columnflow/sandboxes/venv_columnar_dev.sh
    python tests/preflight_trigger_bits.py 2>&1 | tee preflight_trigger_bits.log
"""

import glob
import os

import awkward as ak
import numpy as np
import uproot

_BASE = f"/data/dust/user/{os.environ.get('USER', '*')}"
FILES = sorted(glob.glob(f"{_BASE}/pf_*.root") + glob.glob(f"{_BASE}/mc_*.root"))
MAX_EVENTS = 300_000

B = lambda n: 1 << n  # noqa: E731

# path -> (pdg id, [leg HLT pt thresholds], {label: [masks for leg 1, masks for leg 2, ...]})
PATHS = {
    "HLT_Ele30_WPTight_Gsf": (11, [30.0], {
        "config v12 [2**19]": [[B(19)]],
        "config v15 [2**18]": [[B(18)]],
        "bit 1 '1e (WPTight)'": [[B(1)]],
    }),
    "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": (11, [23.0, 12.0], {
        "config v12 ([2**0], [2**5])": [[B(0)], [B(5)]],
        "config v15 ([2**4], [2**5])": [[B(4)], [B(5)]],
        "v12 proposal ([0 AND 4], [0 AND 4])": [[B(0), B(4)], [B(0), B(4)]],
        "v15 proposal ([0 AND 4], [0 AND 5])": [[B(0), B(4)], [B(0), B(5)]],
        "bit 0 only ([2**0], [2**0])": [[B(0)], [B(0)]],
    }),
    "HLT_IsoMu24": (13, [24.0], {
        "config [2**1]": [[B(1)]],
        "proposal [1 AND 3]": [[B(1), B(3)]],
    }),
    "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": (13, [17.0, 8.0], {
        "config ([2**0], [2**0])": [[B(0)], [B(0)]],
        "proposal ([0 AND 4], [0 AND 4])": [[B(0), B(4)], [B(0), B(4)]],
    }),
}


# leg min_pt as configured in azh/config/triggers.py (applied to TrigObj pt there)
CONFIG_PT = {
    "HLT_Ele30_WPTight_Gsf": [32.0],
    "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": [24.0, 13.0],
    "HLT_IsoMu24": [26.0],
    "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": [18.0, 10.0],
}
PT_MODES = ("hlt", "config", "none")


def leg_match(tid, tpt, tbits, pdg, pt_min, masks):
    m = (abs(tid) == pdg) & (tpt >= pt_min)
    for mask in masks:
        m = m & ((tbits & mask) > 0)
    return ak.any(m, axis=1)


def main():
    if not FILES:
        print("no pf_*.root files found under /data/dust/user/$USER")
        return
    for f in FILES:
        tree = uproot.open(f)["Events"]
        keys = set(tree.keys())
        hlt = [p for p in PATHS if p in keys]
        missing = [p for p in PATHS if p not in keys]
        arr = tree.arrays(["TrigObj_id", "TrigObj_pt", "TrigObj_filterBits"] + hlt,
                          entry_stop=MAX_EVENTS)
        tid = arr["TrigObj_id"]
        tpt = arr["TrigObj_pt"]
        tbits = ak.values_astype(arr["TrigObj_filterBits"], np.int64)
        print(f"\n== {os.path.basename(f)}  ({len(arr)} events read)")
        if missing:
            print(f"   HLT branches absent in this file: {missing}")
        for path in hlt:
            pdg, thresholds, candidates = PATHS[path]
            fired = ak.to_numpy(arr[path]).astype(bool)
            n_fired, n_not = int(fired.sum()), int((~fired).sum())
            print(f"   {path}: fired in {n_fired} events")
            if n_fired == 0:
                continue
            for label, leg_masks in candidates.items():
                row = []
                for mode in PT_MODES:
                    pts = {"hlt": thresholds, "config": CONFIG_PT[path],
                           "none": [0.0] * len(thresholds)}[mode]
                    ok = np.ones(len(arr), dtype=bool)
                    for pt_min, masks in zip(pts, leg_masks):
                        ok &= ak.to_numpy(leg_match(tid, tpt, tbits, pdg, pt_min, masks))
                    eff = ok[fired].mean()
                    fake = ok[~fired].mean() if n_not else float("nan")
                    row.append(f"{mode}: eff={eff:5.3f} fake={fake:5.3f}")
                print(f"      {label:38s} " + " | ".join(row))

if __name__ == "__main__":
    main()
