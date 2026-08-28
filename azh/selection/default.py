
"""
Selection methods for AZH semileptonic.
"""

from collections import defaultdict
from functools import reduce
from operator import and_

from columnflow.columnar_util import Route
from columnflow.config_util import get_shifts_from_sources
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.pdf import pdf_weights
from columnflow.production.cms.scale import murmuf_envelope_weights, murmuf_weights
from columnflow.production.processes import process_ids
from columnflow.production.util import attach_coffea_behavior
from columnflow.selection import SelectionResult, Selector, selector
from columnflow.selection.cms.jets import jet_veto_map
from columnflow.selection.cms.json_filter import json_filter
from columnflow.selection.cms.met_filters import met_filters
from columnflow.selection.stats import increment_stats
from columnflow.util import maybe_import

from azh.production.pileup import pu_weight
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
        murmuf_weights, murmuf_envelope_weights, pdf_weights,
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
        murmuf_weights, murmuf_envelope_weights, pdf_weights,
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
) -> tuple[ak.Array, SelectionResult]:

    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
        events = self[pu_weight](events, **kwargs)
        # Scale and PDF weights have to be computed *here*, not only in
        # cf.ProduceColumns, because increment_stats below needs their
        # per-process sums to build the shape-only normalized variants.
        # Datasets tagged 'no_lhe_weights' (the pythia dibosons) carry no
        # LHEScaleWeight/LHEPdfWeight branch at all, so they are skipped and
        # simply get no scale/PDF nuisance.
        if not self.dataset_inst.has_tag("no_lhe_weights"):
            events = self[murmuf_weights](events, **kwargs)
            events = self[murmuf_envelope_weights](events, **kwargs)
            events = self[pdf_weights](events, **kwargs)

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
        }
        # Every column listed here gets a 'sum_mc_weight_<col>_per_process' entry,
        # which is exactly the key normalized_weight_setup looks up before it will
        # build 'normalized_<col>'. A weight missing from this list silently gets
        # no normalized variant and therefore no nuisance -- see
        # azh/production/normalized_weights.py.
        norm_weight_columns = ["pu_weight", "pu_weight_up", "pu_weight_down"]
        if not self.dataset_inst.has_tag("no_lhe_weights"):
            norm_weight_columns += [
                f"{base}_weight{postfix}"
                for base in ["mur", "muf", "murmuf_envelope", "pdf"]
                for postfix in ["", "_up", "_down"]
            ]
        for column in norm_weight_columns:
            weight_map[f"sum_mc_weight_{column}"] = (
                events.mc_weight * Route(column).apply(events), Ellipsis,
            )
            weight_map[f"sum_mc_weight_{column}_selected"] = (
                events.mc_weight * Route(column).apply(events), results.event,
            )
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


@default.init
def default_init(self: Selector) -> None:
    """
    Declare the JEC/JER shifts this selector implements.

    This has to live on the *selector*, not the calibrator: SelectEvents and
    ReduceEvents set register_selector_shifts = True (columnflow
    tasks/selection.py:57, tasks/reduction.py:54), while register_calibrators_shifts
    is False everywhere. Only a task that implements a shift gets
    local_shift = <shift>, and the column aliases are read from local_shift_inst
    (tasks/selection.py:150, tasks/reduction.py:110).

    Declaring these on the calibrator instead makes the shift resolve globally
    (shift=jec_Total_up) but leaves local_shift=nominal at SelectEvents, so the
    nominal Jet.pt is read and the shifted histogram comes out bit-identical to
    nominal -- with no warning, because missing_column_alias_strategy is
    "original".

    Note the jec calibrator never inspects shift_inst: it writes every
    Jet.pt_jec_<source>_<dir> column in one pass. So CalibrateEvents does not
    need to rerun per shift, and should stay at nominal.
    """
    if not getattr(self, "dataset_inst", None) or self.dataset_inst.is_data:
        return

    sources = self.config_inst.x.jec.get("uncertainty_sources") or []
    shift_sources = [f"jec_{source}" for source in sources] + ["jer"]
    self.shifts |= {
        shift_inst.name
        for shift_inst in get_shifts_from_sources(self.config_inst, *shift_sources)
    }
