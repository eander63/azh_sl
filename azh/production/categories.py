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
met_cut = 40
n_jets_min = 4

@categorizer(
    uses={"m_z", "pt_z", "MET.pt", "cutflow.n_jet_loose", "n_tight_leptons"},
    call_force=True,
)
def catid_baseline(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    """
    B2G-24-002 "Base event selection" table, minus the b-jet count.
        |m_ll - m_Z| < 25   (mass_window)
        pt_z >= 15          (pt_z_cut)
        MET  >  40          (met_cut)
        n_jet_loose >= 4    (n_jets_min)   [pT>15, |eta|<4.7 jets]
        exactly 2 tight leptons
    """
    if "m_z" not in events.fields or "pt_z" not in events.fields:
        return events, ak.zeros_like(events.event) > 0

    mask = (
        (abs(events.m_z - z_mass) < mass_window) &
        (events.pt_z >= pt_z_cut) &
        (events.MET.pt > met_cut) &
        (events.cutflow.n_jet_loose >= n_jets_min) &
        (events.n_tight_leptons == 2)
    )
    return events, ak.fill_none(mask, False)

# ---------------------------------------------------------------------
# Region categorizers, blinded in the b \geq 1 SRs.
# The WZ CR (0 b-jets) unblinded
# ---------------------------------------------------------------------

@categorizer(uses={catid_baseline, "cutflow.n_bjet"}, call_force=True)
def catid_sr_2b(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
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
