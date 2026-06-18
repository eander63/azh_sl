# coding: utf-8

"""
Selection methods defining categories based on selection step results.
"""

from __future__ import annotations

from columnflow.util import maybe_import
from columnflow.categorization import Categorizer, categorizer

np = maybe_import("numpy")
ak = maybe_import("awkward")

z_mass = 91.188
mass_window = 25
pt_z_cut = 15


@categorizer(uses={"cutflow.*"}, call_force=True)
def catid_2l(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Combined ee + mumu category for Z mass plots."""
    mask = (
        (
            (events.cutflow.n_ele_loose == 2) &
            (events.cutflow.n_muo_loose == 0) &
            (events.cutflow.n_ele_high > 0)
        ) | (
            (events.cutflow.n_muo_loose == 2) &
            (events.cutflow.n_ele_loose == 0) &
            (events.cutflow.n_muo_high > 0)
        )
    )
    return events, mask


@categorizer(uses={"event"}, call_force=True)
def catid_SR(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    if "m_z" not in events.fields or "pt_z" not in events.fields:
        return events, ak.zeros_like(events.event) > 0
    mask = (
        (events.m_z >= (z_mass - mass_window)) &
        (events.m_z <= (z_mass + mass_window)) &
        (events.pt_z >= pt_z_cut)
    )
    return events, mask


@categorizer(uses={"event"}, call_force=True)
def catid_CR(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    if "m_z" not in events.fields or "pt_z" not in events.fields:
        return events, ak.zeros_like(events.event) > 0
    mask = (
        ((events.m_z < (z_mass - mass_window)) | (events.m_z > (z_mass + mass_window))) &
        (events.m_z > 30) &
        (events.pt_z >= pt_z_cut)
    )
    return events, mask


# ── B-tag categories (using cutflow.n_bjet from jet_selection) ──

@categorizer(uses={"cutflow.n_bjet"}, call_force=True)
def catid_0bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_bjet == 0


@categorizer(uses={"cutflow.n_bjet"}, call_force=True)
def catid_1bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_bjet == 1


@categorizer(uses={"cutflow.n_bjet"}, call_force=True)
def catid_2bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_bjet >= 2


# ── Jet multiplicity categories ──

@categorizer(uses={"cutflow.n_jet_loose"}, call_force=True)
def catid_4jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_jet_loose == 4


@categorizer(uses={"cutflow.n_jet_loose"}, call_force=True)
def catid_5jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_jet_loose == 5


@categorizer(uses={"cutflow.n_jet_loose"}, call_force=True)
def catid_6jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    return events, events.cutflow.n_jet_loose >= 6
 
 
# ── Category: >=4 loose jets (replaces old selection cut) ──
 
@categorizer(uses={"cutflow.n_jet_loose"}, call_force=True)
def catid_geq4jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Events with >=4 loose jets (pT>15, |eta|<4.7)."""
    return events, events.cutflow.n_jet_loose >= 4
 
 
# ── 3-lepton categories ──
 
@categorizer(uses={"event"}, call_force=True)
def catid_3l(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """
    3-lepton selection (paper Table 1):
      - exactly 3 tight leptons (4th lepton veto)
      - |charge_sum| == 1
      - min(mll) > 12 GeV
    """
    for col in ("n_tight_leptons", "min_mll", "charge_sum"):
        if col not in events.fields:
            return events, ak.zeros_like(events.event) > 0
    mask = (
        (events.n_tight_leptons == 3)
        & (abs(events.charge_sum) == 1)
        & (events.min_mll > 12.0)
    )
    return events, mask
 
 
@categorizer(uses={"event"}, call_force=True)
def catid_2l_only(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Exactly 2 tight leptons (the existing 2L phase space)."""
    if "n_tight_leptons" not in events.fields:
        return events, ak.zeros_like(events.event) > 0
    return events, events.n_tight_leptons == 2


# ── MET categories ──

@categorizer(uses={"MET.pt"}, call_force=True)
def catid_met40(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Events passing MET > 40 GeV cut."""
    return events, events.MET.pt > 40


@categorizer(uses={"MET.pt"}, call_force=True)
def catid_nomet(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """Events with MET <= 40 GeV (below cut)."""
    return events, events.MET.pt <= 40


# ── N-1 categories ──
# Apply all baseline cuts EXCEPT one, to see the effect of each cut
# Uses >=1 jet and >=0 b-tag as baseline (not full SR) for sufficient statistics

@categorizer(uses={"cutflow.n_jet_loose"}, call_force=True)
def catid_n1_no_met(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """All baseline cuts except MET: >=1 loose jet."""
    mask = (events.cutflow.n_jet_loose >= 1)
    return events, mask


@categorizer(uses={"MET.pt"}, call_force=True)
def catid_n1_no_jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """All baseline cuts except jet multiplicity: MET > 40."""
    mask = (events.MET.pt > 40)
    return events, mask


@categorizer(uses={"MET.pt", "cutflow.n_jet_loose"}, call_force=True)
def catid_n1_no_btag(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """All baseline cuts except b-tag: MET > 40 AND >=1 loose jet."""
    mask = (events.MET.pt > 40) & (events.cutflow.n_jet_loose >= 1)
    return events, mask


@categorizer(uses={"MET.pt", "cutflow.n_jet_loose", "cutflow.n_bjet"}, call_force=True)
def catid_n1_all(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """All baseline cuts: MET > 40 AND >=1 loose jet AND >=1 b-jet."""
    mask = (events.MET.pt > 40) & (events.cutflow.n_jet_loose >= 1) & (events.cutflow.n_bjet >= 1)
    return events, mask
