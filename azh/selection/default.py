# coding: utf-8

"""
Selection methods for AZH semileptonic.
"""

from operator import and_
from functools import reduce
from collections import defaultdict
from typing import Tuple

from columnflow.util import maybe_import

from columnflow.selection.stats import increment_stats
from columnflow.selection import Selector, SelectionResult, selector
from columnflow.selection.cms.met_filters import met_filters
from columnflow.selection.cms.json_filter import json_filter
from columnflow.selection.cms.jets import jet_veto_map

from columnflow.production.util import attach_coffea_behavior
from columnflow.production.cms.mc_weight import mc_weight
from azh.production.pileup import pu_weight
from columnflow.production.processes import process_ids

from azh.selection.jet_selection import jet_selection
from azh.selection.lepton_selection import lepton_selection
from azh.selection.trigger import trigger_selection
    # met categories included via add_categories_met


np = maybe_import("numpy")
ak = maybe_import("awkward")


@selector(
    uses={
        process_ids, attach_coffea_behavior,
        mc_weight,
        jet_selection, lepton_selection,
        increment_stats, trigger_selection, pu_weight,
        # Jet.<btag discriminator> comes in via jet_selection's own init,
        # which resolves the era-dependent column from cfg.x.btag_default
        "Jet.pt", "Jet.eta",
        "PuppiMET.pt",
        met_filters, json_filter, jet_veto_map,
    },
    produces={
        process_ids, attach_coffea_behavior,
        mc_weight,
        jet_selection, lepton_selection,
        increment_stats, trigger_selection, pu_weight,
        met_filters, json_filter, jet_veto_map,
    },
    exposed=True,
    check_used_columns=False,
    check_produced_columns=False,
)
def default(
    self: Selector,
    events: ak.Array,
    stats: defaultdict,
    **kwargs,
) -> Tuple[ak.Array, SelectionResult]:

    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
        events = self[pu_weight](events, **kwargs)

    # ensure coffea behavior
    events = self[attach_coffea_behavior](events, **kwargs)

    # prepare the selection results that are updated at every step
    results = SelectionResult()

    # MET filters
    events, met_filters_results = self[met_filters](events, **kwargs)
    results += met_filters_results

    events, jet_veto_results = self[jet_veto_map](events, **kwargs)
    results += jet_veto_results

    # JSON filter (data-only)
    if self.dataset_inst.is_data:
        events, json_filter_results = self[json_filter](events, **kwargs)
        results += json_filter_results

    # lepton selection (2 OSSF leptons for Z candidate)
    events, results_lepton = self[lepton_selection](events, **kwargs)
    results += results_lepton

    # jet selection (≥4 loose jets + tight jets/b-jets defined)
    events, results_jet = self[jet_selection](events, **kwargs)
    results += results_jet

    # trigger selection
    events, results_trigger = self[trigger_selection](events, **kwargs)
    results += results_trigger

    # ── MET cut (paper Table 1: pT_miss > 40 GeV) ──
    # results.steps["MET"] = events.MET.pt > 40  # moved to category

    # ── Baseline: combine ALL selection steps ──
    results.event = reduce(and_, results.steps.values())
    results.event = ak.fill_none(results.event, False)

    # create process ids
    events = self[process_ids](events, **kwargs)

    weight_map = {
        "num_events": Ellipsis,
        "num_events_selected": results.event,
    }
    group_map = {}
    if self.dataset_inst.is_mc:
        weight_map = {
            **weight_map,
            "sum_mc_weight": (events.mc_weight, Ellipsis),
            "sum_mc_weight_selected": (events.mc_weight, results.event),
            "sum_mc_weight_pu_weight": (events.mc_weight * events.pu_weight, Ellipsis),
            "sum_mc_weight_pu_weight_selected": (events.mc_weight * events.pu_weight, results.event),
        }
        group_map = {
            "process": {
                "values": events.process_id,
                "mask_fn": (lambda v: events.process_id == v),
            },
        }
    events, results = self[increment_stats](
        events,
        results,
        stats,
        weight_map=weight_map,
        group_map=group_map,
        **kwargs,
    )

    return events, results
