# coding: utf-8

"""
Categorizers

Structure mirrors B2G-24-002 Table 1, split across three axes so that the
lepton multiplicity is a category:

    catid_2l / catid_3l   lepton multiplicity + per-lepton pT thresholds
                          + 4th-lepton veto + Min(mll) + charge sum
    catid_2e / catid_2mu  flavor of the Z candidate
    catid_baseline        kinematics shared by all analysis regions
    catid_wz_cr / _sr_1b / _sr_2b   b-jet multiplicity (each includes baseline)

Note that catid_baseline is agnostic about multiplicity: the
2-vs-3 lepton split lives entirely on the ``catid_2l`` / ``catid_3l`` axis.
This is what lets a single store serve both the Z-peak validation
(2l__*, no baseline -> no MET/jet cuts) and the analysis
(3l__*__<region>, baseline applied).
"""

from __future__ import annotations

from columnflow.util import maybe_import
from columnflow.categorization import Categorizer, categorizer

np = maybe_import("numpy")
ak = maybe_import("awkward")


# --- B2G-24-002 Table 1 thresholds ----------------------------------------
Z_MASS = 91.188
Z_MASS_WINDOW = 25.0      # |m_ll - m_Z| < 25 GeV
MET_CUT = 40.0            # pT_miss > 40 GeV
N_JETS_MIN = 4            # >= 4 jets, pT > 15 GeV, |eta| < 4.7
MIN_MLL_CUT = 12.0        # Min(m_ll) > 12 GeV, all pairings
LEP_PT_1 = 25.0
LEP_PT_2 = 20.0
LEP_PT_3 = 15.0


def _require(events: ak.Array, *columns: str) -> None:
    """
    Fail if a required column is absent.

    Categorizers must not silently return an all-False mask when an input is
    missing: that yields an empty category with no error.
    Only top-level field names are checked (e.g. "cutflow", not
    "cutflow.n_bjet").
    """
    missing = [c for c in columns if c not in events.fields]
    if missing:
        raise ValueError(
            f"required column(s) {missing} not found. Check that "
            "three_lepton_info / z_boson run before category_ids in the "
            "producer chain, and that these columns survive keep_columns.",
        )

# ---------------------------------------------------------------------
# Multiplicity axis
# ---------------------------------------------------------------------

@categorizer(
    uses={"n_tight_leptons", "lep1_pt", "lep2_pt"},
    call_force=True,
)
def catid_2l(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """
    Dilepton validation region: exactly 2 tight leptons.

    No MET or jet requirement (those live in catid_baseline, which the 2l
    leaves deliberately do not include), so this keeps the full DY Z-peak
    statistics for lepton scale/smearing checks.

    Orthogonal to catid_3l by construction (== 2 vs == 3).
    """
    _require(events, "n_tight_leptons", "lep1_pt", "lep2_pt")

    mask = (
        (events.n_tight_leptons == 2) &
        (events.lep1_pt > LEP_PT_1) &
        (events.lep2_pt > LEP_PT_2)
    )
    return events, ak.fill_none(mask, False)


@categorizer(
    uses={
        "n_tight_leptons", "n_leptons_pt10", "charge_sum", "min_mll",
        "lep1_pt", "lep2_pt", "lep3_pt",
    },
    call_force=True,
)
def catid_3l(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """
    3-lepton analysis selection (B2G-24-002 Table 1, preselection block):

      - exactly 3 tight leptons
      - no additional isolated lepton above 10 GeV (4th-lepton veto).
        n_leptons_pt10 counts loose leptons, which is what the paper vetoes on
        -- a 4th lepton that is loose-but-not-tight still kills the event.
      - lepton pT > 25, 20, 15 GeV
      - Min(m_ll) > 12 GeV over ALL pairings (incl. different-flavor/same-sign)
      - |sum of lepton charges| == 1
    """
    _require(
        events,
        "n_tight_leptons", "n_leptons_pt10", "charge_sum", "min_mll",
        "lep1_pt", "lep2_pt", "lep3_pt",
    )

    mask = (
        (events.n_tight_leptons == 3) &
        (events.n_leptons_pt10 == 3) &
        (events.lep1_pt > LEP_PT_1) &
        (events.lep2_pt > LEP_PT_2) &
        (events.lep3_pt > LEP_PT_3) &
        (events.min_mll > MIN_MLL_CUT) &
        (abs(events.charge_sum) == 1)
    )
    return events, ak.fill_none(mask, False)

# ---------------------------------------------------------------------
# Shared kinematic baseline
# ---------------------------------------------------------------------

@categorizer(
    uses={"m_z", "MET.pt", "cutflow.n_jet_loose"},
    call_force=True,
)
def catid_baseline(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """
    B2G-24-002 "Base event selection", minus the lepton block and the b-jet
    count:

        |m_ll - m_Z| < 25 GeV
        pT_miss      > 40 GeV
        n_jet_loose >= 4        (pT > 15 GeV, |eta| < 4.7)

    The lepton requirements moved to catid_2l / catid_3l; the b-jet count is
    applied by the region categorizers below.
    """
    _require(events, "m_z", "MET", "cutflow")

    mask = (
        (abs(events.m_z - Z_MASS) < Z_MASS_WINDOW) &
        (events.MET.pt > MET_CUT) &
        (events.cutflow.n_jet_loose >= N_JETS_MIN)
    )
    return events, ak.fill_none(mask, False)


# ---------------------------------------------------------------------
# Region categorizers, blinded in the b >= 1 SRs.
# The WZ CR (0 b-jets) is unblinded.
# ---------------------------------------------------------------------

@categorizer(uses={catid_baseline, "cutflow.n_bjet"}, call_force=True)
def catid_sr_2b(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """>=2 b-jet signal region. BLINDED: MC only."""
    events, base = self[catid_baseline](events, **kwargs)
    mask = base & (events.cutflow.n_bjet >= 2)
    if self.dataset_inst.is_data:
        mask = ak.zeros_like(mask) > 0   # blind
    return events, mask


@categorizer(uses={catid_baseline, "cutflow.n_bjet"}, call_force=True)
def catid_sr_1b(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Exactly 1 b-jet signal region. BLINDED: MC only."""
    events, base = self[catid_baseline](events, **kwargs)
    mask = base & (events.cutflow.n_bjet == 1)
    if self.dataset_inst.is_data:
        mask = ak.zeros_like(mask) > 0   # blind
    return events, mask


@categorizer(uses={catid_baseline, "cutflow.n_bjet"}, call_force=True)
def catid_wz_cr(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """0 b-jet WZ control region. Data + MC (NOT blinded)."""
    events, base = self[catid_baseline](events, **kwargs)
    return events, base & (events.cutflow.n_bjet == 0)


# ---------------------------------------------------------------------
# Flavor axis (catid_2e / catid_2mu) is not defined here -- it lives in
# azh/selection/categories.py, which is registered in law.cfg's
# categorization_modules alongside this file. Categorizers are registered by
# name, so defining them in both places would collide.
# ---------------------------------------------------------------------
