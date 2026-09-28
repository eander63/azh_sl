"""
Analysis jets, built in production so the JES/JER variations are
production-level shifts.

ReduceEvents keeps the candidate jets of selection/jet_selection.py (|eta| < 2.5,
TightLepVeto, Delta R-cleaned, pT > 30 in at least one variation). Here the pT
cut is applied to Jet.pt as ProduceColumns sees it -- which, under a jec_* or
jer_* shift, is the aliased varied pT. Everything that depends on the jet
selection (n_jet, n_bjet, the AnaJet collection for plotting, and the b-tag SF
jet mask) is derived from analysis_jet_mask() so the definitions cannot drift.
"""

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from columnflow.util import maybe_import

from azh.selection.jet_selection import JET_PT_MIN

ak = maybe_import("awkward")
np = maybe_import("numpy")

ANA_JET_FIELDS = ("pt", "eta", "phi", "mass")


def analysis_jet_mask(events: ak.Array) -> ak.Array:
    """Analysis jets among the kept candidates: pT > 30 GeV (shift-aware via aliases)."""
    return ak.fill_none(events.Jet.pt > JET_PT_MIN, False)


@producer(
    uses={f"Jet.{f}" for f in ANA_JET_FIELDS},
    produces={"n_jet", "n_bjet", *{f"AnaJet.{f}" for f in ANA_JET_FIELDS}, "AnaJet.btag"},
)
def analysis_jets(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    btag = self.config_inst.x.btag_default
    mask = analysis_jet_mask(events)
    jets = events.Jet[mask]
    jets = jets[ak.argsort(jets.pt, axis=1, ascending=False)]

    events = set_ak_column(events, "n_jet", ak.num(jets.pt, axis=1))
    events = set_ak_column(events, "n_bjet", ak.sum(jets[btag.column] >= btag.wp, axis=1))
    for f in ANA_JET_FIELDS:
        events = set_ak_column(events, f"AnaJet.{f}", jets[f])
    events = set_ak_column(events, "AnaJet.btag", jets[btag.column])
    return events


@analysis_jets.init
def analysis_jets_init(self: Producer, **kwargs) -> None:
    self.uses.add(f"Jet.{self.config_inst.x.btag_default.column}")
