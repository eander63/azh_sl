# coding: utf-8

"""
Lepton selection.

Conservative: this defines only the loose superset of leptons that
survives ReduceEvents. Everything tunable -- the 25/20/15 pT thresholds, the
tight-ID counting, the 4th-lepton veto, Min(mll), the charge sum -- is applied
downstream as categories, so it can be changed without reprocessing.

What's fixed here (and costs a reprocess to change):

  * pT > 10 floor. Sits below the paper's 4th-lepton veto threshold
    (an additional lepton with pT > 10 GeV vetoes the event).
  * Electron acceptance |ScEta| < 2.5 with the ECAL crack 1.44-1.56 removed
    (B2G-24-002: electrons in the barrel/endcap transition are discarded).
    ScEta = Electron.eta + Electron.deltaEtaSC -- this is also the variable the
    EGM scale/smearing and ID scale factors are binned in.
  * Muon acceptance |eta| < 2.4.
  * Loose IDs (Electron mvaIso_WP90, Muon looseId + relIso < 0.25).
  * An OSSF pair must exist. Analysis-defining for a Z-based search, and it
    protects the downstream Z reconstruction from events with no valid pair.

Tight definitions (Electron mvaIso_WP80, Muon tightId + relIso < 0.15) are
computed downstream from the kept columns, not here.
"""

from typing import Tuple

from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.selection import Selector, SelectionResult, selector

from azh.util import masked_sorted_indices

ak = maybe_import("awkward")
np = maybe_import("numpy")


# --- fixed acceptance constants (changing these costs a reprocess) ----------
PT_FLOOR = 10.0           # below the paper's 4th-lepton veto (10 GeV)
ELE_ETA_MAX = 2.5
ELE_CRACK_LO = 1.44       # ECAL barrel/endcap transition, lower edge
ELE_CRACK_HI = 1.56       # ECAL barrel/endcap transition, upper edge
MUO_ETA_MAX = 2.4
MUO_ISO_LOOSE = 0.25


@selector(
    uses={
        # Electron
        "Electron.pt", "Electron.eta", "Electron.phi", "Electron.mass",
        "Electron.charge", "Electron.deltaEtaSC",
        "Electron.mvaIso_WP80", "Electron.mvaIso_WP90",
        # Muon
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.mass",
        "Muon.charge",
        "Muon.looseId", "Muon.tightId", "Muon.pfRelIso04_all",
    },
    produces={
        "cutflow.n_ele_loose", "cutflow.n_muo_loose", "cutflow.n_lep_loose",
        "cutflow.n_ele_tight", "cutflow.n_muo_tight", "cutflow.n_lep_tight",
        "cutflow.lep1_pt", "cutflow.lep2_pt", "cutflow.lep3_pt",
        "cutflow.lep1_eta", "cutflow.lep2_eta", "cutflow.lep3_eta",
    },
    exposed=True,
)
def lepton_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> Tuple[ak.Array, SelectionResult]:

    # ------------------------------------------------------------------
    # Electrons: acceptance on supercluster eta, with the ECAL crack removed
    # ------------------------------------------------------------------
    abs_eta_sc = abs(events.Electron.eta + events.Electron.deltaEtaSC)

    ele_acceptance = (
        (abs_eta_sc < ELE_ETA_MAX) &
        ~((abs_eta_sc > ELE_CRACK_LO) & (abs_eta_sc < ELE_CRACK_HI))
    )

    ele_loose_mask = (
        (events.Electron.pt > PT_FLOOR) &
        ele_acceptance &
        (events.Electron.mvaIso_WP90)
    )

    # tight = loose + WP80. Counted for cutflow only; the analysis-level count
    # is recomputed in production so the WP stays tunable.
    ele_tight_mask = ele_loose_mask & (events.Electron.mvaIso_WP80)

    # ------------------------------------------------------------------
    # Muons
    # ------------------------------------------------------------------
    muo_loose_mask = (
        (events.Muon.pt > PT_FLOOR) &
        (abs(events.Muon.eta) < MUO_ETA_MAX) &
        (events.Muon.looseId) &
        (events.Muon.pfRelIso04_all < MUO_ISO_LOOSE)
    )

    muo_tight_mask = (
        muo_loose_mask &
        (events.Muon.tightId) &
        (events.Muon.pfRelIso04_all < 0.15)
    )

    ele_loose_mask = ak.fill_none(ele_loose_mask, False)
    muo_loose_mask = ak.fill_none(muo_loose_mask, False)
    ele_tight_mask = ak.fill_none(ele_tight_mask, False)
    muo_tight_mask = ak.fill_none(muo_tight_mask, False)

    # ------------------------------------------------------------------
    # Counts (cutflow / monitoring)
    # ------------------------------------------------------------------
    n_ele_loose = ak.sum(ele_loose_mask, axis=1)
    n_muo_loose = ak.sum(muo_loose_mask, axis=1)
    n_ele_tight = ak.sum(ele_tight_mask, axis=1)
    n_muo_tight = ak.sum(muo_tight_mask, axis=1)

    events = set_ak_column(events, "cutflow.n_ele_loose", n_ele_loose)
    events = set_ak_column(events, "cutflow.n_muo_loose", n_muo_loose)
    events = set_ak_column(events, "cutflow.n_lep_loose", n_ele_loose + n_muo_loose)
    events = set_ak_column(events, "cutflow.n_ele_tight", n_ele_tight)
    events = set_ak_column(events, "cutflow.n_muo_tight", n_muo_tight)
    events = set_ak_column(events, "cutflow.n_lep_tight", n_ele_tight + n_muo_tight)

    # ------------------------------------------------------------------
    # Event-level floor: an OSSF pair must exist.
    # Implemented as "at least one positive AND one negative loose lepton of
    # the same flavor".
    # No pT ordering, no exact multiplicity -- those are categories.
    # ------------------------------------------------------------------
    n_ele_pos = ak.sum(ele_loose_mask & (events.Electron.charge > 0), axis=1)
    n_ele_neg = ak.sum(ele_loose_mask & (events.Electron.charge < 0), axis=1)
    n_muo_pos = ak.sum(muo_loose_mask & (events.Muon.charge > 0), axis=1)
    n_muo_neg = ak.sum(muo_loose_mask & (events.Muon.charge < 0), axis=1)

    has_ossf = (
        ((n_ele_pos >= 1) & (n_ele_neg >= 1)) |
        ((n_muo_pos >= 1) & (n_muo_neg >= 1))
    )
    lep_sel = ak.fill_none(has_ossf, False)

    # ------------------------------------------------------------------
    # Kept objects: the loose collections, pT-sorted.
    # Tightness is re-derived downstream from the kept ID columns, so
    # keep_columns must retain Electron.mvaIso_WP80, Muon.tightId and
    # Muon.pfRelIso04_all (it currently does).
    # ------------------------------------------------------------------
    ele_indices = masked_sorted_indices(ele_loose_mask, events.Electron.pt)
    muo_indices = masked_sorted_indices(muo_loose_mask, events.Muon.pt)

    # ------------------------------------------------------------------
    # Leading-3 flavor-merged lepton kinematics, for cutflow plots only.
    # ------------------------------------------------------------------
    lep_pt = ak.concatenate(
        [events.Electron.pt[ele_indices], events.Muon.pt[muo_indices]], axis=1,
    )
    lep_eta = ak.concatenate(
        [events.Electron.eta[ele_indices], events.Muon.eta[muo_indices]], axis=1,
    )
    order = ak.argsort(lep_pt, axis=1, ascending=False)
    lep_pt = ak.pad_none(lep_pt[order], 3)
    lep_eta = ak.pad_none(lep_eta[order], 3)

    for i in range(3):
        events = set_ak_column(
            events, f"cutflow.lep{i + 1}_pt",
            ak.fill_none(lep_pt[:, i], -100.0),
        )
        events = set_ak_column(
            events, f"cutflow.lep{i + 1}_eta",
            ak.fill_none(lep_eta[:, i], -100.0),
        )

    return events, SelectionResult(
        steps={
            "Lepton": lep_sel,
        },
        objects={
            "Electron": {
                "Electron": ele_indices,
            },
            "Muon": {
                "Muon": muo_indices,
            },
        },
        aux={
            "ele_loose_mask": ele_loose_mask,
            "muo_loose_mask": muo_loose_mask,
            "n_loose_electrons": ak.num(ele_indices),
            "n_loose_muons": ak.num(muo_indices),
        },
    )
