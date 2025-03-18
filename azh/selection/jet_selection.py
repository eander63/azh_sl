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
        "cutflow.n_jet", "cutflow.n_bjet",
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
    # DiJet jet selection
    # - require ...

    # assign local index to all Jets - stored after masks for matching
    # TODO: Drop for dijet ?
    events = set_ak_column(events, "Jet.local_index", ak.local_index(events.Jet))

    # jets
    # TODO: Correct jets
    # Selection by UHH2 framework
    # https://github.com/UHH2/DiJetJERC/blob/ff98eebbd44931beb016c36327ab174fdf11a83f/src/AnalysisModule_DiJetTrg.cxx#L692
    # IDs in NanoAOD https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD
    #  & JME NanoAOD https://cms-nanoaod-integration.web.cern.ch/integration/master-106X/mc102X_doc.html
    jet_mask = (
        (events.Jet.pt > 30) &
        (abs(events.Jet.eta) < 2.4) &
        # IDs in NanoAOD https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookNanoAOD
        (events.Jet.jetId == 6)  # 2: fail tight LepVeto and 6: pass tightLepVeto
    )
    jet_sel = ak.num(events.Jet[jet_mask]) >= 4

    events = set_ak_column(events, "cutflow.n_jet", ak.sum(jet_mask, axis=1))
    # btagging
    wp_med = self.config_inst.x.btag_working_points.deepjet.medium
    bjet_mask = jet_mask & (events.Jet.btagDeepFlavB >= wp_med)
    bjet_sel = ak.num(events.Jet[bjet_mask]) >= 2
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

    jet_sel = ak.fill_none(jet_sel, False)
    bjet_sel = ak.fill_none(bjet_sel, False)
    jet_mask = ak.fill_none(jet_mask, False)
    # build and return selection results plus new columns
    return events, SelectionResult(
        steps={
            "Jet": jet_sel,
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
