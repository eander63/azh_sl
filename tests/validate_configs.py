#!/usr/bin/env python
# coding: utf-8

"""
Pre-reprocess config validator for all five AZH Run 3 eras.

Answers one question: **would a full reprocess of this era succeed and produce
physically correct output?** It does that without reading a single event, so it
costs seconds instead of grid hours.

    # from the repo root, inside a columnflow sandbox
    source modules/columnflow/sandboxes/venv_columnar.sh
    python tests/validate_configs.py

    python tests/validate_configs.py --configs config_2024
    python tests/validate_configs.py --skip-external   # no /cvmfs access

Exit code is 0 only if nothing FAILed.

--------------------------------------------------------------------------
THE THREE RESULT KINDS, AND WHY THERE ARE THREE
--------------------------------------------------------------------------
FAIL   The config is definitely wrong and a reprocess would produce garbage or
       crash. Fix before submitting.
WARN   Something is suspicious but might be intentional. Read it and decide.
INFO   A value that could not be checked against a known-correct answer, so the
       script reports what it FOUND instead of asserting.

That last kind is the point of this file. Most entries in
`cfg.x.unverified_settings` are unverified precisely because nobody knows the
right answer from memory -- e.g. "does MUO use the string '2024' as its era
key?". Asserting a guess would be worse than useless. Instead the script opens
the actual JSON, lists the keys that exist, and shows you the one the config
uses next to them. You then confirm or fix, and delete the entry from
`unverified_settings`.

--------------------------------------------------------------------------
WHAT THIS DOES *NOT* COVER
--------------------------------------------------------------------------
  * LFN availability. Whether a dataset's files are actually readable requires
    `cf.GetDatasetLFNs`. This only checks that cmsdb knows about the dataset
    and reports a non-zero file count.
  * Correction *values*. Whether a scale factor is ~0.98 rather than ~2.0 needs
    events. That is what a limited-config run is for.
  * Anything downstream of ProduceColumns.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import defaultdict


# --------------------------------------------------------------------------
# result collection
# --------------------------------------------------------------------------

class Results:
    """
    Flat record of every check, grouped by config and section.

    Deliberately not raising on the first failure: you want the complete
    picture of all five eras in one run, not a whack-a-mole loop where each
    invocation surfaces one more problem.
    """

    def __init__(self):
        self.entries = []
        self._config = "-"
        self._section = "-"

    def context(self, config: str, section: str):
        self._config, self._section = config, section

    def _add(self, kind, msg):
        self.entries.append((self._config, self._section, kind, msg))

    def ok(self, msg):
        self._add("OK", msg)

    def fail(self, msg):
        self._add("FAIL", msg)

    def warn(self, msg):
        self._add("WARN", msg)

    def info(self, msg):
        self._add("INFO", msg)

    def check(self, condition, ok_msg, fail_msg):
        (self.ok if condition else self.fail)(ok_msg if condition else fail_msg)
        return bool(condition)

    def report(self, verbose=False):
        by_kind = defaultdict(int)
        for _, _, kind, _ in self.entries:
            by_kind[kind] += 1

        for kind in ["FAIL", "WARN", "INFO"]:
            rows = [e for e in self.entries if e[2] == kind]
            if not rows:
                continue
            print(f"\n{'=' * 78}\n{kind}  ({len(rows)})\n{'=' * 78}")
            last = None
            for config, section, _, msg in rows:
                if (config, section) != last:
                    print(f"\n  [{config}] {section}")
                    last = (config, section)
                print(f"    {msg}")

        if verbose:
            rows = [e for e in self.entries if e[2] == "OK"]
            print(f"\n{'=' * 78}\nOK  ({len(rows)})\n{'=' * 78}")
            for config, section, _, msg in rows:
                print(f"  [{config}] {section}: {msg}")

        print(f"\n{'=' * 78}")
        print("  ".join(f"{k}: {by_kind[k]}" for k in ["OK", "INFO", "WARN", "FAIL"]))
        print("=" * 78)
        return by_kind["FAIL"] == 0


# --------------------------------------------------------------------------
# correctionlib JSON introspection
# --------------------------------------------------------------------------
#
# The correctionlib Python API does not expose the set of valid category keys,
# which is exactly what has to be verified here (era strings, systematic names,
# working point names). So the raw JSON is walked instead. This also means the
# checks work without correctionlib installed.

_json_cache = {}


def load_correction_json(path):
    """Load and cache a (possibly gzipped) correctionlib file. None if absent."""
    if path in _json_cache:
        return _json_cache[path]
    data = None
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt") as f:
                data = json.load(f)
        else:
            with open(path) as f:
                data = json.load(f)
    except Exception:
        data = None
    _json_cache[path] = data
    return data


def get_correction(cset, name):
    """Find a named correction in a CorrectionSet dict, else None."""
    if not cset:
        return None
    for corr in cset.get("corrections", []):
        if corr.get("name") == name:
            return corr
    for corr in cset.get("compound_corrections", []) or []:
        if corr.get("name") == name:
            return corr
    return None


def correction_names(cset):
    if not cset:
        return []
    names = [c.get("name") for c in cset.get("corrections", [])]
    names += [c.get("name") for c in (cset.get("compound_corrections") or [])]
    return sorted(n for n in names if n)


def _walk(node, fn):
    """Recursively visit every dict node of a correction's data tree."""
    if isinstance(node, dict):
        fn(node)
        for key in ("content", "value", "default"):
            _walk(node.get(key), fn)
    elif isinstance(node, list):
        for item in node:
            _walk(item, fn)


def category_keys(corr, input_name):
    """
    Every valid key of the category node(s) keyed on *input_name*.

    This is what turns "is '2024' the right MUO era string?" from a guess into
    a lookup.
    """
    found = set()

    def visit(node):
        if node.get("nodetype") == "category" and node.get("input") == input_name:
            for item in node.get("content", []) or []:
                if isinstance(item, dict) and "key" in item:
                    found.add(item["key"])

    _walk(corr.get("data") if corr else None, visit)
    return sorted(found, key=str)


def binning_edges(corr, input_name):
    """Lowest and highest edge of the binning node(s) keyed on *input_name*."""
    edges = []

    def visit(node):
        if node.get("nodetype") == "binning" and node.get("input") == input_name:
            e = node.get("edges")
            if isinstance(e, list) and e:
                edges.extend(x for x in e if isinstance(x, (int, float)))

    _walk(corr.get("data") if corr else None, visit)
    return (min(edges), max(edges)) if edges else None


def input_names(corr):
    return [i.get("name") for i in (corr or {}).get("inputs", [])]


def external_path(entry):
    """
    Unwrap a cfg.x.external_files entry into a plain path or URL.

    Entries are stored as (path, version) tuples, sometimes nested in dicts.
    """
    if isinstance(entry, tuple):
        return entry[0]
    return entry if isinstance(entry, str) else None


# --------------------------------------------------------------------------
# section 1: datasets and processes
# --------------------------------------------------------------------------

def check_datasets(cfg, res):
    res.context(cfg.name, "datasets")

    datasets = list(cfg.datasets)
    mc = [d for d in datasets if d.is_mc]
    data = [d for d in datasets if d.is_data]
    res.info(f"{len(datasets)} datasets registered ({len(mc)} MC, {len(data)} data)")

    # Every dataset must actually carry files. A cmsdb entry with n_files == 0
    # produces an empty store silently rather than an error, which is the worst
    # possible failure mode for a background you then forget about.
    for dataset in datasets:
        try:
            n_files = dataset.n_files
            n_events = dataset.n_events
        except Exception as e:
            res.fail(f"{dataset.name}: cannot read file/event counts ({e})")
            continue
        if not n_files:
            res.fail(f"{dataset.name}: 0 files registered in cmsdb")
        elif dataset.is_mc and not n_events:
            res.warn(f"{dataset.name}: {n_files} files but n_events is 0")

    # Data primary datasets must be tagged, because triggers.py gates
    # Trigger.applies_to_dataset on exactly these tags. An untagged data PD is
    # loaded, processed, and then selected by no trigger at all.
    for dataset in data:
        tags = {t for t in ("mu", "egamma") if dataset.has_tag(t)}
        if dataset.name.startswith("data_muoneg"):
            # config_run3.py deliberately tags MuonEG with BOTH 'mu' and
            # 'egamma', so single-mu and single-e triggers both apply to it.
            # That is a choice, not a bug -- but it means MuonEG can contain the
            # same events as the Muon and EGamma PDs, so anything that sums data
            # datasets needs an explicit PD-overlap scheme or it double counts.
            if tags == {"mu", "egamma"}:
                res.info(
                    f"{dataset.name}: tagged mu+egamma, so single-lepton triggers "
                    f"apply; confirm PD overlap removal before summing data",
                )
            else:
                res.warn(f"{dataset.name}: MuonEG PD tagged {tags or 'nothing'}")
            continue
        if not tags:
            res.fail(
                f"{dataset.name}: data PD has neither 'mu' nor 'egamma' tag, so no "
                f"trigger will apply to it",
            )
        elif len(tags) > 1:
            res.fail(f"{dataset.name}: tagged as both mu and egamma")

    # Cross-check the MC tags the producers branch on.
    for dataset in mc:
        if "tt_" in dataset.name and dataset.name.startswith("tt_"):
            if not dataset.has_tag("is_ttbar"):
                res.fail(
                    f"{dataset.name}: missing 'is_ttbar' tag "
                    f"(top pT weight is silently skipped)",
                )
        if dataset.name.endswith("_pythia") and not dataset.has_tag("no_lhe_weights"):
            res.fail(
                f"{dataset.name}: pythia sample without 'no_lhe_weights' tag; "
                f"the scale/PDF producers will raise on the missing LHE branches",
            )


def check_processes(cfg, res):
    res.context(cfg.name, "processes")

    # Every dataset must resolve to a process that the config knows about,
    # otherwise process_ids / normalization_weights have nothing to attach to.
    #
    # NOTE: `cfg.processes` is only the TOP-LEVEL index. Children (e.g. `wz`
    # under `vv`, or the ttz/ttw leaves) are reachable only by walking, so
    # build the registered set by walking each root process.
    registered = set()
    for root in cfg.processes:
        for proc, _, _ in root.walk_processes(include_self=True):
            registered.add(proc.name)

    for dataset in cfg.datasets:
        if not list(dataset.processes):
            res.fail(f"{dataset.name}: no process attached")

    # Cross sections at the Run 3 centre-of-mass energy.
    #
    # SCOPE: only the processes DIRECTLY attached to a dataset are checked, not
    # their whole subtree. cmsdb defines many sub-processes that no sample
    # covers (HT bins, jet bins, hf/lf and decay splits), and columnflow's
    # normalization_weights explicitly `continue`s past any process without an
    # xsec at ecm. So a missing xsec on an unused child is harmless; a missing
    # xsec on a process that events are actually assigned to silently gives
    # those events a normalization weight of ZERO.
    ecm = cfg.campaign.ecm
    for dataset in cfg.datasets:
        if dataset.is_data:
            continue
        for process in dataset.processes:
            if ecm not in process.xsecs:
                res.fail(
                    f"dataset '{dataset.name}' -> process '{process.name}': no cross "
                    f"section at ecm={ecm}; normalization weight will be 0",
                )

    # Producers that REASSIGN process_id after selection (dy_producer rewrites it
    # to <base>_<njet>j_<hf|lf>) rely on child processes that this check cannot
    # see. Report them so their xsec status can be judged by eye.
    for dataset in cfg.datasets:
        if not dataset.has_tag("is_dy"):
            continue
        for process in dataset.processes:
            children = [c for c, _, _ in process.walk_processes(include_self=False)]
            no_xsec = [c.name for c in children if ecm not in c.xsecs]
            if no_xsec:
                res.info(
                    f"dataset '{dataset.name}': {len(no_xsec)} child process(es) lack an "
                    f"xsec at ecm={ecm}, e.g. {no_xsec[:4]}. Harmless if process_id is "
                    f"only reassigned AFTER normalization_weights runs -- verify the "
                    f"producer order in azh/production/default.py.",
                )

    # Signal grid completeness. 2024 ships no azh campaign, so absence there is
    # expected and reported as INFO rather than FAIL.
    try:
        from azh.config.signals import AZH_SIGNAL_PROCESSES
    except ImportError:
        res.warn("azh.config.signals not importable; skipping signal grid check")
        return

    present = [p for p in AZH_SIGNAL_PROCESSES if p in registered]
    missing = [p for p in AZH_SIGNAL_PROCESSES if p not in registered]

    if cfg.campaign.x.year == 2024:
        res.check(
            not present,
            "no signal processes registered, as expected for 2024",
            f"2024 config unexpectedly carries {len(present)} signal processes; "
            f"the campaign has no azh MC so these will fail to resolve",
        )
        return

    if missing:
        res.fail(
            f"{len(missing)}/{len(AZH_SIGNAL_PROCESSES)} signal processes missing, "
            f"e.g. {missing[:5]}",
        )
    else:
        res.ok(f"all {len(AZH_SIGNAL_PROCESSES)} signal processes registered")

    # A registered process with no dataset behind it yields an empty template.
    dataset_names = {d.name for d in cfg.datasets}
    no_dataset = [p for p in present if p not in dataset_names]
    if no_dataset:
        res.fail(
            f"{len(no_dataset)}/{len(present)} signal processes have no dataset. "
            f"Check whether `dataset_names` in config_run3.py lists any azh_* "
            f"entries at all -- registering the processes without the datasets "
            f"makes the signal unrunnable and leaves the `startswith(\"azh\")` "
            f"tagging branch dead. e.g. {no_dataset[:3]}",
        )


# --------------------------------------------------------------------------
# section 2: external files
# --------------------------------------------------------------------------

def iter_external_files(node, prefix=""):
    """Flatten the nested external_files DotDict into (key, path) pairs."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from iter_external_files(value, f"{prefix}.{key}" if prefix else key)
    else:
        path = external_path(node)
        if path:
            yield prefix, path


def check_external_files(cfg, res):
    res.context(cfg.name, "external files")

    for key, path in iter_external_files(cfg.x.external_files):
        if path.startswith(("http://", "https://")):
            # Not fetched: this runs on worker nodes with no outbound network,
            # and columnflow's BundleExternalFiles will fail loudly at task time.
            res.info(f"{key}: remote URL, not checked ({path})")
            continue
        if os.path.exists(path):
            res.ok(f"{key}: present")
        else:
            res.fail(f"{key}: MISSING at {path}")


# --------------------------------------------------------------------------
# section 3: correction keys
# --------------------------------------------------------------------------

def _check_keys(res, label, path, corr_name, key_specs):
    """
    Open one correction file and verify a correction and its category keys.

    *key_specs* maps an input name to the value the config uses. When the value
    is valid the check passes; when it is not, the FAIL message lists the keys
    that DO exist, so the fix is visible without opening the file by hand.
    """
    cset = load_correction_json(path)
    if cset is None:
        res.warn(f"{label}: could not read {path}")
        return

    corr = get_correction(cset, corr_name)
    if corr is None:
        available = correction_names(cset)
        res.fail(
            f"{label}: correction '{corr_name}' not in file. Available: "
            f"{available[:12]}{' ...' if len(available) > 12 else ''}",
        )
        return

    res.ok(f"{label}: correction '{corr_name}' found")

    for input_name, used_value in key_specs.items():
        if input_name not in input_names(corr):
            # Not an error. columnflow builds the argument list by iterating
            # `corrector.inputs` and looking each name up in its variable map,
            # so a configured value the corrector never asks for is simply
            # dropped. Run 3 muon_Z.json is already per-era, so it declares no
            # 'year' input and cfg.x.muon_sf_*_names[1] goes unused.
            res.info(
                f"{label}/{corr_name}: configured '{input_name}'='{used_value}' is "
                f"unused -- corrector inputs are {input_names(corr)}",
            )
            continue
        valid = category_keys(corr, input_name)
        if not valid:
            res.info(f"{label}/{corr_name}: input '{input_name}' is not categorical")
        elif used_value in valid:
            res.ok(f"{label}/{corr_name}: {input_name}='{used_value}' is valid")
        else:
            res.fail(
                f"{label}/{corr_name}: {input_name}='{used_value}' NOT valid. "
                f"Valid keys: {valid}",
            )


def check_corrections(cfg, res):
    res.context(cfg.name, "corrections")

    ext = cfg.x.external_files
    year = cfg.campaign.x.year

    # --- LUM: pileup -----------------------------------------------------
    pu_path = external_path(ext.get("pu_sf"))
    pu_name = cfg.x("pu_correction_name", None)
    cset = load_correction_json(pu_path) if pu_path else None
    if cset is None:
        res.warn(f"pileup: could not read {pu_path}")
    else:
        names = correction_names(cset)
        if pu_name:
            res.check(
                pu_name in names,
                f"pileup: '{pu_name}' found",
                f"pileup: '{pu_name}' not in file; available: {names}",
            )
        else:
            # No explicit name configured -> the code takes the only entry.
            res.check(
                len(names) == 1,
                f"pileup: single correction '{names[0] if names else None}', unambiguous",
                f"pileup: {len(names)} corrections in file ({names}) but no "
                f"cfg.x.pu_correction_name set; the wrong one may be picked",
            )
        # The systematic strings the producer passes.
        if names:
            corr = get_correction(cset, pu_name or names[0])
            for syst in ["nominal", "up", "down"]:
                valid = category_keys(corr, "weights")
                if valid and syst not in valid:
                    res.fail(f"pileup: systematic '{syst}' not valid; keys are {valid}")

    # --- MUO: ID / iso / trigger ----------------------------------------
    muon_path = external_path(ext.get("muon_sf"))
    for aux_key, label in [
        ("muon_sf_id_names", "muon ID"),
        ("muon_sf_iso_names", "muon iso"),
        ("muon_sf_trig_names", "muon trigger"),
    ]:
        names = cfg.x(aux_key, None)
        if not names:
            res.warn(f"{label}: cfg.x.{aux_key} not set")
            continue
        corr_name, era_key = names[0], names[1]
        # The era key is the single most-guessed string in the whole config
        # (README 2024 open items). This resolves it definitively.
        _check_keys(res, label, muon_path, corr_name, {"year": era_key})

    # The muon SF pT floor. weights.py hard-codes MUON_SF_PT_MIN = 15.0 and the
    # comment claims the JSON binning starts there; if a POG update moves it,
    # sub-threshold muons silently get SF=1 or correctionlib raises.
    cset = load_correction_json(muon_path) if muon_path else None
    id_names = cfg.x("muon_sf_id_names", None)
    if cset and id_names:
        corr = get_correction(cset, id_names[0])
        edges = binning_edges(corr, "pt")
        if edges:
            res.check(
                abs(edges[0] - 15.0) < 1e-6,
                f"muon ID: pT binning starts at {edges[0]}, matches MUON_SF_PT_MIN",
                f"muon ID: pT binning starts at {edges[0]}, but weights.py "
                f"hard-codes MUON_SF_PT_MIN = 15.0",
            )

    # --- EGM: reco / ID / trigger / scale+smearing -----------------------
    ele_path = external_path(ext.get("electron_sf"))
    for aux_key, label in [
        ("electron_sf_id_names", "electron ID"),
        ("electron_sf_mid_names", "electron reco 20-75"),
        ("electron_sf_loreco_names", "electron reco <20"),
    ]:
        names = cfg.x(aux_key, None)
        if not names:
            res.warn(f"{label}: cfg.x.{aux_key} not set")
            continue
        # (correction, era key, working point)
        _check_keys(
            res, label, ele_path, names[0],
            {"year": names[1], "WorkingPoint": names[2]},
        )

    trig_names = cfg.x("electron_sf_trig_names", None)
    if trig_names:
        # Electron-HLT-SF inputs are (year, ValType, Path, eta, pt) -- the third
        # config entry is the HLT path name, NOT a working point as it is for
        # Electron-ID-SF. azh/production/trigger_weights.py already calls it
        # positionally in that order.
        _check_keys(
            res, "electron trigger", external_path(ext.get("electron_sf_hlt")),
            trig_names[0], {"year": trig_names[1], "Path": trig_names[2]},
        )

    ss_names = cfg.x("electron_ss_names", None)
    if ss_names:
        ss_path = external_path(ext.get("electron_ss"))
        cset = load_correction_json(ss_path) if ss_path else None
        if cset is None:
            res.warn(f"electron S&S: could not read {ss_path}")
        else:
            available = correction_names(cset)
            for name in ss_names:
                res.check(
                    name in available,
                    f"electron S&S: '{name}' found",
                    f"electron S&S: '{name}' not in file; available: {available}",
                )

    # --- BTV: working points and SF sets ---------------------------------
    btag_path = external_path(ext.get("btag_sf_corr"))
    btag = cfg.x("btag_default", None)
    cset = load_correction_json(btag_path) if btag_path else None
    if cset is None:
        res.warn(f"btag: could not read {btag_path}")
    elif btag:
        available = correction_names(cset)
        res.info(f"btag: correction sets available: {available}")

        # The b-tag SF variation names are the open question from the
        # systematics work: the AN's Run 2 12-source list belongs to the DeepJet
        # SHAPE calibration and has no counterpart in the fixed-WP sets. Report
        # what the file actually offers so the correlation scheme can be chosen
        # from evidence rather than transcribed.
        sf_sets = [n for n in available if n.endswith(("_comb", "_light", "_mujets"))]
        for sf_set in sf_sets:
            corr = get_correction(cset, sf_set)
            systs = category_keys(corr, "systematic")
            wps = category_keys(corr, "working_point")
            res.info(
                f"btag/{sf_set}: systematics={systs or '<none>'} "
                f"working_points={wps or '<none>'}",
            )

        res.info(
            f"btag: config uses tagger '{btag.name}', column '{btag.column}', "
            f"medium WP = {btag.wp}",
        )

    # --- JME: JEC uncertainty sources ------------------------------------
    # The big one. config_run3.py:940 notes the Regrouped_* era spellings were
    # verified for 2022 only, and switching to JEC_SOURCES_REDUCED without
    # checking is a guaranteed wasted reprocess.
    jerc_path = external_path(ext.get("jet_jerc"))
    cset = load_correction_json(jerc_path) if jerc_path else None
    if cset is None:
        res.warn(f"JEC: could not read {jerc_path}")
    else:
        available = correction_names(cset)
        jec = cfg.x("jec", None)
        if jec:
            for source in jec.get("uncertainty_sources", []) or []:
                # Uncertainty entries are named <campaign>_<version>_<source>_<jettype>
                tail = f"_{source}_{jec.jet_type}"
                matches = [n for n in available if n.endswith(tail)]
                res.check(
                    bool(matches),
                    f"JEC source '{source}': found as {matches[0]}",
                    f"JEC source '{source}': no correction ending in "
                    f"'{tail}' in {os.path.basename(jerc_path)}",
                )

            # List everything available so the reduced set can be transcribed
            # from the file rather than from the AN.
            suffix = f"_{jec.jet_type}"
            regrouped = sorted({
                n.split("_Regrouped_")[1][: -len(suffix)]
                for n in available
                if "_Regrouped_" in n and n.endswith(suffix)
            })
            if regrouped:
                res.info(f"JEC: Regrouped_* sources available for {year}: {regrouped}")


# --------------------------------------------------------------------------
# section 4: shift wiring
# --------------------------------------------------------------------------

def check_shifts(cfg, res):
    """
    Self-consistency of the systematic machinery.

    Every failure here is silent at runtime: CreateHistograms sets
    missing_column_alias_strategy = "original", so a shift whose alias target
    does not exist falls back to nominal and produces a template identical to
    nominal with no warning.
    """
    res.context(cfg.name, "shifts")

    shifts = {s.name: s for s in cfg.shifts}
    res.info(f"{len(shifts)} shifts registered")

    # Up/down must come in pairs.
    for name in shifts:
        if name.endswith("_up"):
            partner = name[:-3] + "_down"
            if partner not in shifts:
                res.fail(f"shift '{name}' has no matching '{partner}'")

    # Ids must be unique, or order silently overwrites.
    by_id = defaultdict(list)
    for shift in cfg.shifts:
        by_id[shift.id].append(shift.name)
    for shift_id, names in by_id.items():
        if len(names) > 1:
            res.fail(f"shift id {shift_id} used by {names}")

    # Every weight in event_weights that declares shifts must have the varied
    # columns those shifts alias to, and the alias must target the column that
    # actually enters the weight (the normalized_* one, where applicable).
    kept = set(cfg.x("keep_columns", {}).get("cf.ReduceEvents", set()) or set())
    kept_str = {str(c) for c in kept}

    for weight, weight_shifts in (cfg.x("event_weights", None) or {}).items():
        if not weight_shifts:
            res.info(f"weight '{weight}': no shifts declared (nominal only)")
            continue
        for shift in weight_shifts:
            aliases = shift.get_aux("column_aliases", {}) or {}
            if not aliases:
                res.fail(
                    f"weight '{weight}' declares shift '{shift.name}' but that shift "
                    f"registers no column aliases, so it cannot vary anything",
                )

    # Selection-dependent shifts alias detector-level columns, which must
    # survive reduction or the shifted histogram silently reads nominal.
    for shift in cfg.shifts:
        if not shift.has_tag("selection_dependent"):
            continue
        for target in (shift.get_aux("column_aliases", {}) or {}).values():
            base = target.split(".")[0]
            if kept_str and not any(k.startswith(base) for k in kept_str):
                res.warn(
                    f"shift '{shift.name}' aliases to '{target}' but no keep_columns "
                    f"entry starts with '{base}'",
                )


# --------------------------------------------------------------------------
# section 5: leftovers
# --------------------------------------------------------------------------

def check_unverified(cfg, res):
    res.context(cfg.name, "unverified settings")
    entries = cfg.x("unverified_settings", []) or []
    if not entries:
        res.ok("no unverified settings remain")
        return
    res.warn(f"{len(entries)} setting(s) still marked unverified:")
    for entry in entries:
        res.warn(f"  - {entry}")


def check_lumi(cfg, res):
    res.context(cfg.name, "luminosity")
    lumi = cfg.x("luminosity", None)
    if lumi is None:
        res.fail("cfg.x.luminosity is not set")
        return
    res.info(f"L = {float(lumi.nominal):.0f} pb^-1")
    # The inference model builds one rate nuisance per named uncertainty, so an
    # empty set means the datacard silently gets no luminosity uncertainty.
    names = list(lumi.uncertainties)
    res.check(
        bool(names),
        f"luminosity uncertainties: {names}",
        "luminosity has no named uncertainties; the inference model will emit "
        "no lumi nuisance at all",
    )


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

DEFAULT_CONFIGS = [
    "config_2022pre",
    "config_2022post",
    "config_2023pre",
    "config_2023post",
    "config_2024",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS)
    parser.add_argument("--skip-external", action="store_true",
                        help="skip file-existence and correction-key checks "
                             "(use when /cvmfs is unavailable)")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="also print OK lines",
    )
    args = parser.parse_args(argv)

    # Imported here rather than at module scope so that --help works outside a
    # sandbox: building the analysis pulls in columnflow, order and cmsdb.
    from azh.config.analysis_azh_run3 import analysis_azh

    res = Results()

    for config_name in args.configs:
        try:
            cfg = analysis_azh.get_config(config_name)
        except Exception as e:
            res.context(config_name, "build")
            res.fail(f"could not load config: {type(e).__name__}: {e}")
            continue

        check_datasets(cfg, res)
        check_processes(cfg, res)
        check_lumi(cfg, res)
        check_shifts(cfg, res)
        check_unverified(cfg, res)

        if not args.skip_external:
            check_external_files(cfg, res)
            check_corrections(cfg, res)

    passed = res.report(verbose=args.verbose)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())