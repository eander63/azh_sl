"""
Test for the step-2 batch (pileup + scale + PDF + top pT).

The failure mode this guards against is a *silent* one: CreateHistograms sets
missing_column_alias_strategy = "original", so an alias pointing at a column that
was never produced falls back to nominal without warning, and normalized_weight_setup
drops any weight whose per-process sum was not booked. Both produce a shifted
histogram identical to nominal. So the three lists have to agree exactly:

  (a) alias targets registered in config_run3.py
  (b) weight columns listed in cfg.x.event_weights / dataset.x.event_weights
  (c) sum_mc_weight_<col> keys booked in selection/default.py

Alias formatting and shift lookup run against real order objects; the column
inventory is parsed out of the patched source files.
"""
import ast
import re
import sys
from pathlib import Path

import order as od

REPO = Path("/data/dust/user/eranders/AZHtt/azh_semileptonic")
CFG_SRC = (REPO / "azh/config/config_run3.py").read_text()
SEL_SRC = (REPO / "azh/selection/default.py").read_text()
PU_SRC = (REPO / "azh/production/pileup.py").read_text()
W_SRC = (REPO / "azh/production/weights.py").read_text()


def strip_comments(src):
    """Drop comment text so that explanatory notes naming an old symbol are not
    mistaken for live references to it."""
    return "\n".join(re.sub(r"#.*$", "", line) for line in src.splitlines())


CFG_CODE = strip_comments(CFG_SRC)

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# ---------------------------------------------------------------------------
# columns the producers actually emit
# ---------------------------------------------------------------------------
# pileup: read straight out of the patched producer's `produces`
pu_produces = set(re.search(r'produces=\{([^}]*)\}', PU_SRC).group(1).replace('"', '').split(", "))
pu_produces = {c.strip() for c in pu_produces if c.strip()}
check(
    pu_produces == {"pu_weight", "pu_weight_up", "pu_weight_down"},
    f"pileup producer emits {sorted(pu_produces)}",
)

# columnflow scale/pdf producers (verified against the fork):
#   murmuf_weights          -> {mur,muf}_weight{,_up,_down}
#   murmuf_envelope_weights -> murmuf_envelope_weight{,_up,_down}
#   pdf_weights             -> pdf_weight{,_up,_down}
raw_lhe_columns = {
    f"{base}_weight{postfix}"
    for base in ["mur", "muf", "murmuf_envelope", "pdf"]
    for postfix in ["", "_up", "_down"]
}
# normalized_weight_factory emits normalized_<col> for each of its inputs
normalized_columns = (
    {f"normalized_{c}" for c in raw_lhe_columns} |
    {f"normalized_{c}" for c in pu_produces}
)
# lepton SF and trigger columns from step 1, all emitting {,_up,_down}
lepton_columns = {
    f"{w}{postfix}"
    for w in [
        "electron_weight", "electron_mid_weight", "electron_loreco_weight",
        "electron_id_weight", "muon_id_weight", "muon_iso_weight",
        "electron_trig_weight", "muon_trig_weight",
    ]
    for postfix in ["", "_up", "_down"]
}
top_pt_columns = {"top_pt_weight", "top_pt_weight_up", "top_pt_weight_down"}
produced = normalized_columns | lepton_columns | top_pt_columns | raw_lhe_columns | pu_produces

# ---------------------------------------------------------------------------
# (c) sums booked in the selector
# ---------------------------------------------------------------------------
booked = {"pu_weight", "pu_weight_up", "pu_weight_down"} | raw_lhe_columns
check(
    'norm_weight_columns = ["pu_weight", "pu_weight_up", "pu_weight_down"]' in SEL_SRC,
    "selector no longer books the pileup sums the way this test expects",
)
check("sum_mc_weight_{column}" in SEL_SRC, "selector weight_map key format changed")
for col in booked:
    check(col in produced, f"selector books a sum for '{col}', which nothing produces")

# every normalized column must have its source sum booked, or it is dropped
for col in normalized_columns:
    src = col[len("normalized_"):]
    check(src in booked, f"'{col}' needs sum_mc_weight_{src}_per_process, not booked")

# ---------------------------------------------------------------------------
# (a) replay the alias registrations against real order objects
# ---------------------------------------------------------------------------
cfg = od.Config(name="test", id=1)


def add_aliases(shift_source, aliases, selection_dependent):
    for direction in ["up", "down"]:
        shift = cfg.get_shift(od.Shift.join_name(shift_source, direction))
        inject_shift = lambda s: re.sub(r"\{([^_])", r"{_\1", s).format(**shift.__dict__)  # noqa
        _aliases = {inject_shift(k): inject_shift(v) for k, v in aliases.items()}
        key = "column_aliases_selection_dependent" if selection_dependent else "column_aliases"
        shift.set_aux(key, shift.get_aux(key, {})).update(_aliases)


shift_ids = {
    "minbias_xs": 7, "top_pt": 9, "e_sf": 40, "e_trig_sf": 42,
    "muon": 51, "mu_trig_sf": 53, "mur": 201, "muf": 203,
    "murmuf_envelope": 205, "pdf": 207,
}
for source, sid in shift_ids.items():
    cfg.add_shift(name=f"{source}_up", id=sid, type="shape")
    cfg.add_shift(name=f"{source}_down", id=sid + 1, type="shape")

add_aliases("minbias_xs", {"normalized_pu_weight": "normalized_pu_weight_{direction}"}, False)
add_aliases("top_pt", {"top_pt_weight": "top_pt_weight_{direction}"}, False)
add_aliases("e_trig_sf", {"electron_trig_weight": "electron_trig_weight_{direction}"}, False)
add_aliases("mu_trig_sf", {"muon_trig_weight": "muon_trig_weight_{direction}"}, False)
add_aliases("e_sf", {
    w: f"{w}_{{direction}}"
    for w in ["electron_weight", "electron_mid_weight", "electron_loreco_weight",
              "electron_id_weight"]
}, False)
add_aliases("muon", {
    w: f"{w}_{{direction}}" for w in ["muon_id_weight", "muon_iso_weight"]
}, False)
for unc in ["mur", "muf", "murmuf_envelope", "pdf"]:
    add_aliases(unc, {f"normalized_{unc}_weight": f"normalized_{unc}_weight_" + "{direction}"}, False)

# every alias source column must be something a producer emits
for shift in cfg.shifts:
    for target, source in shift.x("column_aliases", {}).items():
        check(source in produced, f"{shift.name}: alias source '{source}' is never produced")
        check(target in produced, f"{shift.name}: alias target '{target}' is never produced")

# ---------------------------------------------------------------------------
# (b) event_weights entries in the patched config
# ---------------------------------------------------------------------------
config_level = set(re.findall(r'^\s+"(\w+)": get_shifts\(', CFG_SRC, re.MULTILINE))
for col in config_level:
    check(col in produced, f"cfg.x.event_weights has '{col}', which nothing produces")

check(
    'dataset.has_tag("is_ttbar")' in CFG_CODE and 'dataset.x("is_ttbar", False)' not in CFG_CODE,
    "dataset-level event_weights still guards on the aux instead of the tag",
)
check("murf_envelope" not in CFG_CODE, "stale 'murf_envelope' name still present in config")
check('prod_version = "v2"' in CFG_CODE, "prod_version not bumped; stats would collide with v1")

# scale/PDF must be dataset-level, not config-level (wz_pythia has no LHE weights)
for unc in ["mur", "muf", "murmuf_envelope", "pdf"]:
    check(
        f'"normalized_{unc}_weight"' not in CFG_CODE.split("for dataset in cfg.datasets")[0],
        f"normalized_{unc}_weight is config-level; would raise on no_lhe_weights datasets",
    )

# ---------------------------------------------------------------------------
# all touched files parse
# ---------------------------------------------------------------------------
for src, name in [(CFG_SRC, "config_run3.py"), (SEL_SRC, "selection/default.py"),
                  (PU_SRC, "pileup.py"), (W_SRC, "weights.py")]:
    try:
        ast.parse(src)
    except SyntaxError as e:
        failures.append(f"{name} does not parse: {e}")

print(f"checks run, {len(failures)} failure(s)")
for f in failures:
    print("  FAIL:", f)
sys.exit(1 if failures else 0)
