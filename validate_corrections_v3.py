#!/usr/bin/env python
# coding: utf-8

"""
Validate that every configured correction name actually exists in its external file,
for every era.

Why this exists
---------------
Correction names in config_run3.py are era-specific strings. Nothing checks them until
the corresponding task runs, and correctionlib's failure mode is a bare
"IndexError: map::at" with no indication of which lookup failed or what was available.
Worse, some mismatches do not raise at all -- a corrector whose expected "systematic"
axis is absent silently returns the nominal value for every variation, so the
uncertainty vanishes without error. Both classes of bug have already occurred here:

  * electron_ss carried the 2024 scale name in every era (crash at CalibrateEvents)
  * the JER ScaleFactor corrector has no systematic axis in the new JME file layout,
    so up/down came out identical to nominal (silent, no error)
  * the electron SF corrector version gate rejected v4 (crash at ProduceColumns)
  * the muon SF pt binning starts at 15 GeV while the selection floor is 10 (crash)

Each of these was found only when a version bump forced a task to rerun. This script
finds them in seconds, before any job starts.

Usage
-----
    python tests/validate_corrections.py                    # all configs
    python tests/validate_corrections.py config_2022pre     # one config

Exit code is non-zero if any check fails, so it can be used in CI.
"""

from __future__ import annotations

import gzip
import json
import sys


# corrector versions the columnflow producers accept; keep in sync with the fork
SUPPORTED_ELECTRON_SF_VERSIONS = {2, 3, 4, 5}

# lowest pt a lepton can have after the selection floor (lepton_selection.PT_FLOOR)
SELECTION_PT_FLOOR = 10.0


class Report(object):

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.checks = 0

    def ok(self, msg):
        self.checks += 1
        print(f"    ok      {msg}")

    def error(self, msg):
        self.checks += 1
        self.errors.append(msg)
        print(f"    ERROR   {msg}")

    def warn(self, msg):
        self.checks += 1
        self.warnings.append(msg)
        print(f"    WARN    {msg}")


def load(path):
    """
    Open a (possibly gzipped) correctionlib file.

    Returns (CorrectionSet, raw dict, set of corrector names).

    The name set matters: correctionlib's CorrectionSet.__getitem__ raises
    IndexError ("map::at") for an unknown key, while Python's default Mapping
    __contains__ only catches KeyError. So `name in cs.keys()` RAISES for a
    missing name instead of returning False. Iterating into a plain set avoids
    subscripting entirely.
    """
    import correctionlib
    opener = gzip.open if str(path).endswith(".gz") else open
    text = opener(path).read()
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    cs = correctionlib.CorrectionSet.from_string(text)
    return cs, json.loads(text), set(cs.keys())


def file_path(cfg, key):
    f = cfg.x.external_files.get(key)
    if f is None:
        return None
    return f[0] if isinstance(f, (tuple, list)) else f


def category_keys(raw, corrector_name, axis_name):
    """
    Collect the allowed values of a categorical input axis by walking the correction's
    data tree. Returns None if the axis is not a category node.
    """
    corr = next((c for c in raw["corrections"] if c["name"] == corrector_name), None)
    if corr is None:
        return None
    found = set()

    def walk(node, depth=0):
        if isinstance(node, dict):
            if node.get("nodetype") == "category" and node.get("input") == axis_name:
                found.update(str(item["key"]) for item in node.get("content", []))
            for value in node.values():
                walk(value, depth + 1)
        elif isinstance(node, list):
            for value in node:
                walk(value, depth + 1)

    walk(corr["data"])
    return found or None


def pt_range(raw, corrector_name, axis_name="pt"):
    """Lowest and highest edge of a binning node on *axis_name*, or None."""
    corr = next((c for c in raw["corrections"] if c["name"] == corrector_name), None)
    if corr is None:
        return None
    edges = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("nodetype") == "binning" and node.get("input") == axis_name:
                edges.append((node["edges"][0], node["edges"][-1]))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(corr["data"])
    return (min(e[0] for e in edges), max(e[1] for e in edges)) if edges else None


def check_named(rep, names_in_file, raw, label, name_tuple, axis_order):
    """
    Check a (corrector, *category values) tuple: the corrector must exist and each
    category value must be a valid key on its corresponding axis.
    """
    corrector, *values = name_tuple
    if corrector not in names_in_file:
        rep.error(
            f"{label}: corrector {corrector!r} not in file. "
            f"Available: {sorted(names_in_file)}",
        )
        return
    for value, axis in zip(values, axis_order):
        keys = category_keys(raw, corrector, axis)
        if keys is None:
            rep.warn(
                f"{label}: no '{axis}' category axis found, cannot verify {value!r}",
            )
        elif value not in keys:
            rep.error(f"{label}: {value!r} not a valid '{axis}'. Valid: {sorted(keys)}")
        else:
            rep.ok(f"{label}: {corrector} [{axis}={value}]")


def run_block(rep, label, fn):
    """
    Run one check block, converting any exception into an error for that block only.

    Without this, a single raising lookup (correctionlib raises a bare
    "IndexError: map::at") aborts the whole config and hides every later check --
    which is exactly the silent-gap problem this script exists to remove.
    """
    try:
        fn()
    except Exception as e:
        rep.error(f"{label}: check raised {type(e).__name__}: {e}")


def validate_config(cfg, rep):
    print(f"\n=== {cfg.name} ===")

    def _check_electron_sf():
        # ---- electron scale factors -------------------------------------------
        path = file_path(cfg, "electron_sf")
        if path:
            cs, raw, names_in_file = load(path)
            for label, key, wp_axis in [
                ("electron reco >75", "electron_sf_names", "WorkingPoint"),
                ("electron reco 20-75", "electron_sf_mid_names", "WorkingPoint"),
                ("electron reco 10-20", "electron_sf_loreco_names", "WorkingPoint"),
                ("electron ID", "electron_sf_id_names", "WorkingPoint"),
            ]:
                names = cfg.x(key, None)
                if names:
                    check_named(rep, names_in_file, raw, label, names, ["year", wp_axis])
            # version gate that already bit us once
            name = cfg.x("electron_sf_names", (None,))[0]
            if name in names_in_file:
                version = cs[name].version
                if version in SUPPORTED_ELECTRON_SF_VERSIONS:
                    rep.ok(f"electron sf corrector version {version} supported")
                else:
                    rep.error(
                        f"electron sf corrector version {version} outside supported "
                        f"{sorted(SUPPORTED_ELECTRON_SF_VERSIONS)}",
                    )

    run_block(rep, "electron sf", _check_electron_sf)

    def _check_electron_trigger():
        # ---- electron trigger --------------------------------------------------
        path = file_path(cfg, "electron_sf_hlt")
        if path:
            cs, raw, names_in_file = load(path)
            names = cfg.x("electron_sf_trig_names", None)
            if names:
                check_named(
                    rep, names_in_file, raw, "electron trigger", names,
                    ["year", "WorkingPoint"],
                )

    run_block(rep, "electron trigger", _check_electron_trigger)

    def _check_electron_ss():
        # ---- electron scale & smearing ----------------------------------------
        path = file_path(cfg, "electron_ss")
        if path:
            cs, raw, names_in_file = load(path)
            names = cfg.x("electron_ss_names", None)
            if names:
                for which, name in zip(("scale", "smear"), names):
                    if name in names_in_file:
                        rep.ok(f"electron ss {which}: {name}")
                    else:
                        rep.error(
                            f"electron ss {which}: {name!r} not in file. "
                            f"Available: {sorted(names_in_file)}",
                        )

    run_block(rep, "electron ss", _check_electron_ss)

    def _check_muon_sf():
        # ---- muon scale factors ------------------------------------------------
        path = file_path(cfg, "muon_sf")
        if path:
            cs, raw, names_in_file = load(path)
            for label, key in [
                ("muon ID", "muon_sf_id_names"),
                ("muon iso", "muon_sf_iso_names"),
                ("muon trigger", "muon_sf_trig_names"),
            ]:
                names = cfg.x(key, None)
                if not names:
                    continue
                corrector = names[0]
                if corrector not in names_in_file:
                    rep.error(
                        f"{label}: {corrector!r} not in file. "
                        f"Available: {sorted(names_in_file)}",
                    )
                    continue
                rep.ok(f"{label}: {corrector}")
                # pt coverage: SFs applied below the lowest bin edge raise at runtime
                rng = pt_range(raw, corrector)
                if rng and rng[0] > SELECTION_PT_FLOOR:
                    rep.warn(
                        f"{label}: pt binning starts at {rng[0]:g} GeV but the selection "
                        f"floor is {SELECTION_PT_FLOOR:g}; the producer must mask below "
                        f"{rng[0]:g} (see MUON_SF_PT_MIN in azh/production/weights.py)",
                    )

    run_block(rep, "muon sf", _check_muon_sf)

    def _check_pileup():
        # ---- pileup ------------------------------------------------------------
        path = file_path(cfg, "pu_sf")
        if path:
            cs, _, names_in_file = load(path)
            keys = sorted(names_in_file)
            if len(keys) == 1:
                rep.ok(f"pileup: single corrector {keys[0]}")
            else:
                rep.error(f"pileup: expected exactly one corrector, found {keys}")

    run_block(rep, "pileup", _check_pileup)

    def _check_jec_jer():
        # ---- JEC / JER ---------------------------------------------------------
        path = file_path(cfg, "jet_jerc")
        if path:
            cs, raw, names_in_file = load(path)
            keys = names_in_file
            jec = cfg.x.jec
            for source in jec["uncertainty_sources"]:
                key = f"{jec['campaign']}_{jec['version']}_MC_{source}_{jec['jet_type']}"
                (rep.ok if key in keys else rep.error)(
                    f"JES source {source}: {key}" if key in keys
                    else f"JES source {source}: {key!r} not in file",
                )
            for level in jec["levels"]:
                key = f"{jec['campaign']}_{jec['version']}_MC_{level}_{jec['jet_type']}"
                if key not in keys:
                    rep.error(f"JEC level {level}: {key!r} not in file")

            jer = cfg.x.jer
            res = f"{jer['campaign']}_{jer['version']}_MC_PtResolution_{jer['jet_type']}"
            sf = f"{jer['campaign']}_{jer['version']}_MC_ScaleFactor_{jer['jet_type']}"
            unc = f"{jer['campaign']}_{jer['version']}_MC_SFUncertainty_{jer['jet_type']}"
            for label, key in [("JER resolution", res), ("JER scale factor", sf)]:
                (rep.ok if key in keys else rep.error)(
                    f"{label}: {key}" if key in keys else f"{label}: {key!r} not in file",
                )
            # the silent one: variations need either a systematic axis or SFUncertainty
            if sf in keys:
                has_syst = any(i.name in ("systematic", "syst") for i in cs[sf].inputs)
                if has_syst:
                    rep.ok("JER variations: ScaleFactor carries a systematic axis")
                elif unc in keys:
                    rep.ok(f"JER variations: {unc.split('_MC_')[1]} present (additive)")
                else:
                    rep.error(
                        "JER variations unavailable: ScaleFactor has no systematic "
                        "axis and "
                        f"{unc!r} is absent -- jer_up/down would equal nominal SILENTLY",
                    )

    run_block(rep, "jec/jer", _check_jec_jer)

    def _check_btag():
        # ---- b-tagging ---------------------------------------------------------
        path = file_path(cfg, "btag_sf_corr")
        if path:
            cs, _, names_in_file = load(path)
            btag = cfg.x("btag_sf", None)
            if btag is not None:
                for name in btag.correction_set:
                    (rep.ok if name in names_in_file else rep.error)(
                        f"btag: {name}" if name in names_in_file
                        else f"btag: {name!r} not in file. "
                        f"Available: {sorted(names_in_file)}",
                    )
    run_block(rep, "btag", _check_btag)


def main(argv):
    import azh.config.analysis_azh_run3 as a

    # fail once with an actionable message rather than per config
    try:
        import correctionlib  # noqa: F401
    except ImportError:
        print(
            "correctionlib not found -- run inside the columnar sandbox:\n"
            '  ( source "$CF_BASE/sandboxes/venv_columnar.sh" "" && '
            "python tests/validate_corrections.py )",
        )
        return 1

    wanted = argv[1:] or None
    configs = [c for c in a.analysis_azh.configs if not wanted or c.name in wanted]
    # _limited / _10files variants differ only in dataset scope, not in corrections,
    # so checking them repeats every lookup and triples the output for nothing
    if not wanted:
        configs = [c for c in configs if not c.name.endswith(("_limited", "_10files"))]
    if not configs:
        available = [c.name for c in a.analysis_azh.configs]
        print(f"no matching configs (available: {available})")
        return 1

    rep = Report()
    for cfg in configs:
        try:
            validate_config(cfg, rep)
        except Exception as e:
            rep.error(f"{cfg.name}: validation itself failed: {type(e).__name__}: {e}")

    print(
        f"\n{rep.checks} checks, {len(rep.errors)} error(s), "
        f"{len(rep.warnings)} warning(s)",
    )
    for msg in rep.errors:
        print(f"  ERROR  {msg}")
    for msg in rep.warnings:
        print(f"  WARN   {msg}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
