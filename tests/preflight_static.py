#!/usr/bin/env python
# coding: utf-8

"""
Static wiring check for the SR/CR plotting run.

Builds the analysis configs and inspects them. Runs no law task, reads no events
and opens no correction files, so it is safe to run before anything is
reprocessed. Every check prints what it found, so a FAIL can be verified by eye.

    source setup.sh
    source modules/columnflow/sandboxes/venv_columnar_dev.sh
    python tests/preflight_static.py                  # all five eras
    python tests/preflight_static.py config_2023pre   # one era

Exit code is 0 only if nothing FAILed.
"""

from __future__ import annotations

import os
import sys

CONFIGS = [
    "config_2022pre", "config_2022post", "config_2023pre", "config_2023post", "config_2024",
]

# categorizers that zero out data (see azh/production/categories.py)
BLINDING_CATEGORIZERS = {"catid_sr_1b", "catid_sr_2b"}
# categorizers that restrict to a data-safe region
SAFE_CATEGORIZERS = {"catid_wz_cr"}
# ttbar samples the (currently disabled) top pT reweighting may ever apply to
TTBAR_PREFIXES = ("tt_sl", "tt_dl", "tt_fh")
# DY bases dy_producer knows how to split
DY_BASES = ("dy_m50toinf", "dy_m10to50", "dy_m4to10")


class Report:

    def __init__(self):
        self.rows = {"FAIL": [], "WARN": [], "INFO": []}

    def add(self, kind, cfg, topic, msg):
        self.rows[kind].append(f"  [{cfg}] {topic}: {msg}")

    def fail(self, *a):
        self.add("FAIL", *a)

    def warn(self, *a):
        self.add("WARN", *a)

    def info(self, *a):
        self.add("INFO", *a)

    def dump(self):
        for kind in ("INFO", "WARN", "FAIL"):
            print(f"\n{'=' * 78}\n{kind}  ({len(self.rows[kind])})\n{'=' * 78}")
            print("\n".join(self.rows[kind]) or "  (none)")
        print(f"\nFAIL: {len(self.rows['FAIL'])}  WARN: {len(self.rows['WARN'])}")
        return 1 if self.rows["FAIL"] else 0


def selection_list(cat):
    sel = cat.selection
    return list(sel) if isinstance(sel, (list, tuple)) else [sel]


def walk_categories(cats):
    for c in cats:
        yield c
        yield from walk_categories(c.categories)


def iter_external_files(node, prefix=""):
    if isinstance(node, tuple):
        yield prefix, node[0]
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from iter_external_files(value, f"{prefix}.{key}" if prefix else key)


def xsec_13p6(process_inst):
    try:
        return process_inst.xsecs.get(13.6)
    except Exception:
        try:
            return process_inst.get_xsec(13.6)
        except Exception:
            return None


def max_rel_uncertainty(number):
    """Largest relative up/down uncertainty of a scinum Number, None if it has none."""
    try:
        uncs = dict(number.uncertainties)
        nominal = float(number.nominal)
    except Exception:
        return None
    if not uncs or not nominal:
        return None
    return max(max(abs(float(u)), abs(float(dn))) for u, dn in uncs.values()) / abs(nominal)


def check_config(cfg, rep):
    n = cfg.name

    # --- triggers ---------------------------------------------------------
    triggers = cfg.x("triggers", None)
    if triggers is None:
        rep.fail(n, "triggers", "cfg.x.triggers is not set -> SelectEvents cannot run")
    else:
        rep.info(n, "triggers", ", ".join(f"{t.name}{sorted(t.tags)}" for t in triggers))

    # --- luminosity -------------------------------------------------------
    lumi = cfg.x.luminosity
    rep.info(n, "luminosity", f"{lumi.nominal} /pb, uncertainties {dict(lumi.uncertainties)}")
    if cfg.x("channel_lumis", None):
        cl = cfg.x.channel_lumis
        if cl["muon"] != cl["nominal"] or cl["egamma"] != cl["nominal"]:
            rep.warn(n, "channel_lumi_weight", f"non-trivial per-channel lumi {cl} "
                     "(assigned by Z flavour, wrong for mixed-flavour 3l events)")

    # --- data datasets ----------------------------------------------------
    for d in (d for d in cfg.datasets if d.is_data):
        tags = [t for t in ("mu", "egamma") if d.has_tag(t)]
        keys = sorted(d.get_info("nominal").keys)
        if not tags:
            rep.fail(n, "data", f"{d.name} has neither 'mu' nor 'egamma' tag -> no trigger applies")
        elif len(tags) == 2:
            rep.info(n, "data", f"{d.name} tagged mu+egamma -> dropped by trigger_selection ({keys})")
        else:
            rep.info(n, "data", f"{d.name} [{tags[0]}] {keys}")

    # --- MC datasets, cross sections, tags --------------------------------
    for d in sorted((d for d in cfg.datasets if d.is_mc), key=lambda d: d.name):
        procs = list(d.processes)
        xs = {p.name: xsec_13p6(p) for p in procs}
        tags = sorted(t for t in ("is_ttbar", "is_dy", "no_lhe_weights") if d.has_tag(t))
        info = d.get_info("nominal")
        rep.info(n, "mc", f"{d.name}: {xs} tags={tags} n_files={info.n_files} keys={sorted(info.keys)}")
        for pname, value in xs.items():
            if value is None:
                rep.fail(n, "xsec", f"{d.name}: process {pname} has no 13.6 TeV xsec")
                continue
            rel = max_rel_uncertainty(value)
            if rel is None:
                rep.warn(n, "xsec", f"{d.name}: {pname} xsec has no uncertainty attached")
            elif rel < 1e-3:
                rep.warn(n, "xsec", f"{d.name}: {pname} largest relative uncertainty {rel:.1e} "
                         "-> looks like a generator (integration) value, not a theory prediction")
        if d.has_tag("is_ttbar") and not d.name.startswith(TTBAR_PREFIXES):
            rep.warn(n, "tags", f"{d.name} tagged is_ttbar but is not a ttbar sample")
        if d.has_tag("is_dy") and not d.name.startswith(DY_BASES):
            rep.fail(n, "tags", f"{d.name} tagged is_dy but dy_producer has no branch for it")

    # --- process nesting (double counting in stacked plots) ---------------
    names = [p.name for p in cfg.processes]
    for a in names:
        for b in names:
            if a != b and cfg.get_process(a).has_process(b):
                rep.warn(n, "processes", f"'{b}' is inside '{a}': plotting both double counts '{b}'")

    # --- weights <-> shifts <-> aliases -----------------------------------
    weight_shifts = {col: list(shifts) for col, shifts in cfg.x.event_weights.items()}
    for d in (d for d in cfg.datasets if d.is_mc):
        for col, shifts in d.x("event_weights", {}).items():
            weight_shifts.setdefault(col, [])
            for s in shifts:
                if s not in weight_shifts[col]:
                    weight_shifts[col].append(s)
            if col == "top_pt_weight":
                rep.warn(n, "weights", f"{d.name} still applies top_pt_weight")

    used = set()
    for col, shifts in sorted(weight_shifts.items()):
        if not shifts:
            rep.info(n, "weights", f"{col}: nominal only")
        for s in shifts:
            used.add(s.name)
            aliases = s.get_aux("column_aliases", {})
            if col not in aliases:
                rep.fail(n, "weights", f"{col}: shift {s.name} is declared but does not alias "
                         f"'{col}' (aliases: {aliases}) -> histogram identical to nominal")
            else:
                rep.info(n, "weights", f"{col}: {s.name} -> {aliases[col]}")

    for s in cfg.shifts:
        if s.name == "nominal":
            continue
        if s.has_tag("disjoint_from_nominal"):
            with_info = [d.name for d in cfg.datasets if s.name in d.info]
            if not with_info:
                rep.warn(n, "shifts", f"{s.name} is disjoint_from_nominal but no dataset has an "
                         "info for it -> unusable")
            continue
        if s.name in used:
            continue
        if s.has_tag("selection_dependent"):
            rep.info(n, "shifts", f"{s.name} (selection dependent): {s.get_aux('column_aliases', {})}")
        else:
            rep.warn(n, "shifts", f"{s.name} is registered but no event weight uses it")

    # --- categories and blinding ------------------------------------------
    # A category walk visits combined categories once per parent, so dedupe by name.
    cats = list({c.name: c for c in walk_categories(cfg.categories)}.values())
    unblinded = cfg.x.category_groups.get("unblinded", [])
    if not unblinded:
        rep.fail(n, "blinding", "category group 'unblinded' is empty")
    else:
        rep.info(n, "blinding", f"unblinded group: {unblinded}")
    blind = cfg.x("blind_sr_data", False)
    if blind:
        rep.info(n, "blinding", "blind_sr_data = True: SR data events are removed from every category in production")
    for c in sorted(cats, key=lambda c: c.id):
        sel = set(selection_list(c))
        safe = bool(sel & ({"catid_2l"} | SAFE_CATEGORIZERS))
        if c.name in unblinded and not safe:
            rep.fail(n, "blinding", f"{c.name} is in 'unblinded' but can contain SR events")
        if not blind and not safe and not sel & BLINDING_CATEGORIZERS:
            rep.warn(n, "blinding", f"{c.name} (id {c.id}) can contain SR data events and blind_sr_data is off")
    rep.info(n, "categories", ", ".join(f"{c.name}={c.id}" for c in sorted(cats, key=lambda c: c.id)))

    # --- b-tag efficiency grouping (btag.py:585 raises on unknown names) --
    btag_cfg = cfg.x("btag_wp_sf_config", None)
    if btag_cfg is not None:
        for d in (d for d in cfg.datasets if d.is_mc):
            group = btag_cfg.dataset_groups(d)
            if group is None:
                rep.info(n, "btag groups", f"{d.name}: no group, efficiency from its own stats")
                continue
            missing = [g for g in group if isinstance(g, str) and not cfg.has_dataset(g)]
            if missing:
                rep.fail(n, "btag groups", f"{d.name}: group names {missing} not in config -> "
                         "split_btag_wp_weights setup will raise")

    # --- external files on disk -------------------------------------------
    for key, path in iter_external_files(cfg.x.external_files):
        if "://" in path:
            continue
        if not os.path.exists(path):
            rep.fail(n, "external files", f"{key}: {path} does not exist")

    # --- datasets that cmsdb does not provide yet ---------------------------
    for name in cfg.x("missing_datasets", []):
        rep.fail(n, "datasets", f"required dataset {name} is not in the cmsdb campaign (see PREFLIGHT_CHANGES.md)")
    for msg in cfg.x("unverified_settings", []):
        rep.warn(n, "unverified", msg)

    # --- every shift source has a datacard correlation ---------------------
    corr = cfg.x("shift_correlations", {})
    sources = {s_.name.rsplit("_", 1)[0] for s_ in cfg.shifts if s_.name != "nominal"}
    for src in sorted(sources):
        if src not in corr:
            rep.fail(n, "correlations", f"shift source {src} has no entry in cfg.x.shift_correlations")
    for src in sorted(set(corr) - sources):
        rep.warn(n, "correlations", f"cfg.x.shift_correlations lists {src}, which is not a registered shift")

    # --- production-level shifts: aliased columns must survive reduction ---
    import fnmatch
    keep = set(cfg.x.keep_columns.get("cf.ReduceEvents", set()))
    for src in cfg.x("production_shift_sources", []):
        for d in ("up", "down"):
            shift = cfg.get_shift(f"{src}_{d}")
            for target in shift.get_aux("column_aliases", {}).values():
                if not any(fnmatch.fnmatch(target, pat) or target == pat for pat in keep):
                    rep.fail(n, "keep_columns", f"{shift.name}: alias target {target} is not kept after "
                             "reduction -> the shift silently falls back to nominal")

    # --- JEC config layout (columnflow deprecation warning) ---------------
    if "Jet" not in cfg.x.jec:
        rep.warn(n, "jec", "cfg.x.jec is not keyed by jet collection ('Jet'); columnflow "
                 "fallback will be removed")


def main(argv):
    from azh.config.analysis_azh_run3 import analysis_azh as ana

    rep = Report()
    for name in (argv or CONFIGS):
        check_config(ana.get_config(name), rep)
    return rep.dump()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
