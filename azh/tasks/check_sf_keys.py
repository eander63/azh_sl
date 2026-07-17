# coding: utf-8
"""
Standalone introspection script. Run on DESY (where /cvmfs is mounted) to
verify that every JSON key strings hardcoded for each era in
``azh/config/config_run3.py`` actually exists in the jsonpog-integration
files. Reports a clear PASS / FAIL per (era, key) pair.

Usage:
    python tasks/check_sf_keys.py

No columnflow / order dependencies; pure correctionlib + gzip.
"""
from __future__ import annotations

import gzip
import io
import os
import sys
from dataclasses import dataclass, field
from typing import Iterable

try:
    import correctionlib
except ImportError:
    sys.exit("correctionlib is required: pip install correctionlib")

JSON_MIRROR = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration"


# ---------------------------------------------------------------------------
# Per-era key configurations — keep in sync with azh/config/config_run3.py
# ---------------------------------------------------------------------------
@dataclass
class EraConfig:
    label: str               # e.g. "2022preEE"
    corr_tag: str            # e.g. "2022_Summer22"   (path component)
    # ("first_token", "second_token") for muon_Z.json scale-factor names:
    muon_id: tuple = ("NUM_TightID_DEN_TrackerMuons", "")
    muon_iso: tuple = ("NUM_TightPFIso_DEN_TightID", "")
    muon_trig: tuple = (
        "NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight",
        "",
    )
    # electron.json identifiers (Electron-ID-SF, period, working-point)
    ele_above75: tuple = ("Electron-ID-SF", "", "RecoAbove75")
    ele_mid: tuple = ("Electron-ID-SF", "", "Reco20to75")
    ele_id: tuple = ("Electron-ID-SF", "", "wp80iso")
    # electronHlt.json identifiers
    ele_hlt: tuple = ("Electron-HLT-SF", "", "HLT_SF_Ele30_MVAiso80ID")
    # electronSS.json identifiers — just the *correction-set* names
    ele_scale: str = "Scale"
    ele_smear: str = "Smearing"


ERAS: list[EraConfig] = [
    EraConfig(
        label="2022preEE", corr_tag="2022_Summer22",
        muon_id=("NUM_TightID_DEN_TrackerMuons", "2022preEE"),
        muon_iso=("NUM_TightPFIso_DEN_TightID", "2022preEE"),
        muon_trig=(
            "NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight",
            "2022preEE",
        ),
        ele_above75=("Electron-ID-SF", "2022Re-recoBCD", "RecoAbove75"),
        ele_mid=("Electron-ID-SF", "2022Re-recoBCD", "Reco20to75"),
        ele_id=("Electron-ID-SF", "2022Re-recoBCD", "wp80iso"),
        ele_hlt=("Electron-HLT-SF", "2022Re-recoBCD", "HLT_SF_Ele30_MVAiso80ID"),
        ele_scale="Scale",
        ele_smear="Smearing",
    ),
    EraConfig(
        label="2022postEE", corr_tag="2022_Summer22EE",
        muon_id=("NUM_TightID_DEN_TrackerMuons", "2022postEE"),
        muon_iso=("NUM_TightPFIso_DEN_TightID", "2022postEE"),
        muon_trig=(
            "NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight",
            "2022postEE",
        ),
        ele_above75=("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoAbove75"),
        ele_mid=("Electron-ID-SF", "2022Re-recoE+PromptFG", "Reco20to75"),
        ele_id=("Electron-ID-SF", "2022Re-recoE+PromptFG", "wp80iso"),
        ele_hlt=("Electron-HLT-SF", "2022Re-recoE+PromptFG", "HLT_SF_Ele30_MVAiso80ID"),
        ele_scale="Scale",
        ele_smear="Smearing",
    ),
    EraConfig(
        label="2023preBPix", corr_tag="2023_Summer23",
        muon_id=("NUM_TightID_DEN_TrackerMuons", "2023preBPix"),
        muon_iso=("NUM_TightPFIso_DEN_TightID", "2023preBPix"),
        muon_trig=(
            "NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight",
            "2023preBPix",
        ),
        ele_above75=("Electron-ID-SF", "2023PromptC", "RecoAbove75"),
        ele_mid=("Electron-ID-SF", "2023PromptC", "Reco20to75"),
        ele_id=("Electron-ID-SF", "2023PromptC", "wp80iso"),
        ele_hlt=("Electron-HLT-SF", "2023PromptC", "HLT_SF_Ele30_MVAiso80ID"),
        ele_scale="2023PromptC_ScaleJSON",
        ele_smear="2023PromptC_SmearingJSON",
    ),
    EraConfig(
        label="2023postBPix", corr_tag="2023_Summer23BPix",
        muon_id=("NUM_TightID_DEN_TrackerMuons", "2023postBPix"),
        muon_iso=("NUM_TightPFIso_DEN_TightID", "2023postBPix"),
        muon_trig=(
            "NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight",
            "2023postBPix",
        ),
        ele_above75=("Electron-ID-SF", "2023PromptD", "RecoAbove75"),
        ele_mid=("Electron-ID-SF", "2023PromptD", "Reco20to75"),
        ele_id=("Electron-ID-SF", "2023PromptD", "wp80iso"),
        ele_hlt=("Electron-HLT-SF", "2023PromptD", "HLT_SF_Ele30_MVAiso80ID"),
        ele_scale="2023PromptD_ScaleJSON",
        ele_smear="2023PromptD_SmearingJSON",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_cset(path: str):
    if not os.path.exists(path):
        return None, f"FILE MISSING: {path}"
    try:
        with gzip.open(path, "rb") as f:
            data = f.read().decode("utf-8")
        return correctionlib.CorrectionSet.from_string(data), None
    except Exception as exc:
        return None, f"FAILED TO LOAD {path}: {exc}"


def check_top_level_key(cset, key: str) -> bool:
    """A correction-set name lookup."""
    try:
        _ = cset[key]
        return True
    except Exception:
        return False


def check_evaluate(cset, top_key: str, inputs: tuple) -> tuple[bool, str]:
    """Try evaluating to see if the *second-level* token is also accepted.

    The muon/electron SF JSONs are typically structured so that the top key
    selects a correction object and the first input is the era period. If
    that period is wrong, ``.evaluate`` raises with a friendly message.
    """
    try:
        corr = cset[top_key]
    except Exception as exc:
        return False, f"top key '{top_key}' missing: {exc}"
    try:
        corr.evaluate(*inputs)
        return True, ""
    except Exception as exc:
        return False, str(exc).strip().splitlines()[0][:120]


def report(label: str, ok: bool, detail: str = ""):
    badge = "  OK " if ok else "FAIL "
    print(f"  [{badge}] {label}" + (f"   ({detail})" if detail else ""))


# ---------------------------------------------------------------------------
# Main per-era checks
# ---------------------------------------------------------------------------
def check_era(era: EraConfig):
    print(f"\n=== {era.label}   (corr_tag = {era.corr_tag}) ===")
    base = f"{JSON_MIRROR}/POG"
    failed = 0

    # ----- muon_Z.json.gz -----
    cset, err = load_cset(f"{base}/MUO/{era.corr_tag}/muon_Z.json.gz")
    print(f"-- muon_Z.json.gz")
    if cset is None:
        report("file load", False, err); failed += 1
    else:
        # tightID
        name, period = era.muon_id
        ok, msg = check_evaluate(cset, name, (0.0, 30.0, "nominal"))
        report(f"muon_id name = {name}, period = '{period}'", ok, msg); failed += not ok
        # tightPFIso
        name, period = era.muon_iso
        ok, msg = check_evaluate(cset, name, (0.0, 30.0, "nominal"))
        report(f"muon_iso name = {name}, period = '{period}'", ok, msg); failed += not ok
        # trigger
        name, period = era.muon_trig
        ok, msg = check_evaluate(cset, name, (0.0, 30.0, "nominal"))
        report(f"muon_trig name = {name}, period = '{period}'", ok, msg); failed += not ok
        # list of top keys for reference
        keys = list(cset.keys())
        print(f"     [available keys] {', '.join(keys[:5])}{' ...' if len(keys) > 5 else ''}")

    # ----- electron.json.gz -----
    cset, err = load_cset(f"{base}/EGM/{era.corr_tag}/electron.json.gz")
    print(f"-- electron.json.gz")
    if cset is None:
        report("file load", False, err); failed += 1
    else:
        # tries the (sf, period, wp, eta, pt) signature
        for label, (top, period, wp) in [
            ("electron_above75", era.ele_above75),
            ("electron_mid",     era.ele_mid),
            ("electron_id",      era.ele_id),
        ]:
            ok, msg = check_evaluate(cset, top, (period, "sf", wp, 0.0, 30.0))
            report(f"{label} period='{period}' wp='{wp}'", ok, msg); failed += not ok

    # ----- electronHlt.json.gz -----
    cset, err = load_cset(f"{base}/EGM/{era.corr_tag}/electronHlt.json.gz")
    print(f"-- electronHlt.json.gz")
    if cset is None:
        report("file load", False, err); failed += 1
    else:
        top, period, path = era.ele_hlt
        ok, msg = check_evaluate(cset, top, (period, "sf", path, 0.0, 35.0))
        report(f"electron_hlt period='{period}' path='{path}'", ok, msg); failed += not ok

    # ----- electronSS.json.gz -----
    cset, err = load_cset(f"{base}/EGM/{era.corr_tag}/electronSS.json.gz")
    print(f"-- electronSS.json.gz")
    if cset is None:
        report("file load", False, err); failed += 1
    else:
        ok = check_top_level_key(cset, era.ele_scale)
        report(f"electron Scale correction set = '{era.ele_scale}'", ok); failed += not ok
        ok = check_top_level_key(cset, era.ele_smear)
        report(f"electron Smearing correction set = '{era.ele_smear}'", ok); failed += not ok
        # always show what is available — these are the ones most likely to drift
        keys = list(cset.keys())
        print(f"     [available keys] {', '.join(keys)}")

    return failed


def main():
    total_failed = 0
    for era in ERAS:
        total_failed += check_era(era)
    print()
    if total_failed == 0:
        print("ALL KEYS VALIDATED")
    else:
        print(f"TOTAL FAILURES: {total_failed}")
        print("Re-introspect the offending JSON manually:")
        print("    import correctionlib, gzip")
        print("    cset = correctionlib.CorrectionSet.from_string(gzip.open(PATH,'rb').read().decode())")
        print("    print(list(cset.keys()))")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
