# coding: utf-8

from typing import Tuple
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.selection import Selector, SelectionResult, selector
from azh.util import masked_sorted_indices

ak = maybe_import("awkward")


@selector(
    uses={"Jet.pt", "Jet.eta", "Jet.phi", "Jet.jetId", "Jet.btagDeepFlavB"},
    produces={
        "cutflow.n_jet", "cutflow.n_jet_loose", "cutflow.n_bjet",
        "cutflow.jet1_pt", "cutflow.jet2_pt", "cutflow.jet3_pt", "cutflow.jet4_pt",
        "cutflow.jet1_eta", "cutflow.jet2_eta", "cutflow.jet3_eta", "cutflow.jet4_eta",
    },
    exposed=True,
)
def jet_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> Tuple[ak.Array, SelectionResult]:

    # assign local index to all Jets
    events = set_ak_column(events, "Jet.local_index", ak.local_index(events.Jet))

    # ── Loose jets (paper Table 1: pT > 15 GeV, |eta| < 4.7) ──
    # Used only for the ≥4-jet multiplicity cut
    loose_jet_mask = (
        (events.Jet.pt > 15) &
        (abs(events.Jet.eta) < 4.7) &
        (events.Jet.jetId >= 2)  # at least tight
    )
    loose_jet_sel = ak.num(events.Jet[loose_jet_mask]) >= 2 # floor; >=4 is a category
    # also store a version that always passes (jet cut moved to categories)
    events = set_ak_column(events, "cutflow.n_jet_loose", ak.sum(loose_jet_mask, axis=1))

    # ── Tight jets (pT > 30 GeV, |eta| < 2.5, tightLepVeto) ──
    # Used for b-tagging and the main jet collection
    jet_mask = (
        (events.Jet.pt > 30) &
        (abs(events.Jet.eta) < 2.5) &
        (events.Jet.jetId == 6)  # tightLepVeto
    )
    events = set_ak_column(events, "cutflow.n_jet", ak.sum(jet_mask, axis=1))

    # ── B-tagging (medium DeepJet on tight jets) ──
    wp_med = self.config_inst.x.btag_working_points.deepjet.medium
    bjet_mask = jet_mask & (events.Jet.btagDeepFlavB >= wp_med)
    events = set_ak_column(events, "cutflow.n_bjet", ak.sum(bjet_mask, axis=1))

    jet_indices = masked_sorted_indices(jet_mask, events.Jet.pt)
    bjet_indices = masked_sorted_indices(bjet_mask, events.Jet.pt)

    jets = events.Jet[jet_indices]
    padded_jets = ak.pad_none(jets, 4)
    for i in range(4):
        events = set_ak_column(events, f"cutflow.jet{i+1}_pt",
        ak.where((ak.is_none(padded_jets.pt[:, {i}][:, 0])), -100, (padded_jets.pt[:, {i}][:, 0])))
        events = set_ak_column(events, f"cutflow.jet{i+1}_eta",
        ak.where((ak.is_none(padded_jets.eta[:, {i}][:, 0])), -100, (padded_jets.eta[:, {i}][:, 0])))

    loose_jet_sel = ak.fill_none(loose_jet_sel, False)
    jet_mask = ak.fill_none(jet_mask, False)

    # Selection step uses LOOSE jets (≥4 with pT>15, |eta|<4.7)
    return events, SelectionResult(
        steps={
            "Jet": loose_jet_sel,
        },
        objects={
            "Jet": {
                "Jet": jet_indices,
                "BJet": bjet_indices,
            },
        },
        aux={
            "jet_mask": jet_mask,
            "n_central_jets": ak.num(jet_indices),
        },
    )
