# coding: utf-8

"""
Selection methods for AZH semileptonic.
"""

from operator import and_
from functools import reduce
from collections import defaultdict
from typing import Tuple

from columnflow.util import maybe_import
from columnflow.columnar_util import Route
from columnflow.config_util import get_shifts_from_sources

from columnflow.selection.stats import increment_stats
from columnflow.selection import Selector, SelectionResult, selector
from columnflow.selection.cms.met_filters import met_filters
from columnflow.selection.cms.json_filter import json_filter
from columnflow.selection.cms.jets import jet_veto_map

from columnflow.production.util import attach_coffea_behavior
from columnflow.production.cms.mc_weight import mc_weight
from azh.production.theory import pdf_hessian_weights, ps_weights
from columnflow.production.cms.scale import murmuf_weights, murmuf_envelope_weights
from azh.production.pileup import pu_weight
from columnflow.production.processes import process_ids

from azh.selection.jet_selection import jet_selection
from azh.calibration.corrections import ECAL_BADCRYSTAL_RUNS
from azh.selection.lepton_selection import lepton_selection
from azh.selection.trigger import trigger_selection
    # met categories included via add_categories_met
from columnflow.selection.cms.btag import fill_btag_wp_count_hists


np = maybe_import("numpy")
ak = maybe_import("awkward")


@selector(
    uses={
        process_ids, attach_coffea_behavior,
        mc_weight,
        jet_selection, lepton_selection,
        increment_stats, trigger_selection, pu_weight,
        fill_btag_wp_count_hists,
        murmuf_weights, murmuf_envelope_weights, pdf_hessian_weights, ps_weights,
        # Jet.<btag discriminator> comes in via jet_selection's own init,
        # which resolves the era-dependent column from cfg.x.btag_default
        "Jet.pt", "Jet.eta",
        "PuppiMET.pt",
        "Flag.ecalBadCalibFilter",
        met_filters, json_filter, jet_veto_map,
    },
    produces={
        process_ids, attach_coffea_behavior,
        mc_weight,
        jet_selection, lepton_selection,
        increment_stats, trigger_selection, pu_weight,
        murmuf_weights, murmuf_envelope_weights, pdf_hessian_weights, ps_weights,
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
    hists: dict,
    **kwargs,
) -> Tuple[ak.Array, SelectionResult]:

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
            # Hessian PDF + alpha_s (production/theory.py), not columnflow's
            # replica-style pdf_weights
            events = self[pdf_hessian_weights](events, **kwargs)
        if not self.dataset_inst.has_tag("no_ps_weights"):
            events = self[ps_weights](events, **kwargs)

    # ensure coffea behavior
    events = self[attach_coffea_behavior](events, **kwargs)

    # prepare the selection results that are updated at every step
    results = SelectionResult()

    # MET filters
    events, met_filters_results = self[met_filters](events, **kwargs)
    results += met_filters_results

    # ECAL bad calibration filter. Data in runs 362433-367144 are prompt reco
    # and use the JME bad-crystal veto (calibration/corrections.py) instead of
    # the stored flag; everything else uses the flag.
    ecal_ok = events.Flag.ecalBadCalibFilter
    if self.dataset_inst.is_data:
        lo, hi = ECAL_BADCRYSTAL_RUNS
        in_window = (events.run >= lo) & (events.run <= hi)
        ecal_ok = ak.where(in_window, ~events.ecal_badcrystal_veto, ecal_ok)
    results.steps["ecal_bad_calib"] = ak.fill_none(ecal_ok, False)

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
        if not self.dataset_inst.has_tag("no_ps_weights"):
            norm_weight_columns += [
                f"{base}_weight{postfix}"
                for base in ["isr", "fsr"]
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

    # Per-(pt, |eta|, flavour, WP) jet counts for the MC b-tagging efficiency
    # measurement (AN-2022/158 Sec. 4.5: eff_f(i,j) = N_f^btagged / N_f^total).
    # BTV requires analyses to derive these from their own selected jets; the
    # producer divides the per-WP bins by the "total" bin at setup time.
    # objects.Jet.Jet is the same index set ReduceEvents keeps, so the
    # efficiency is measured on exactly the jets the weight is applied to.
    if self.dataset_inst.is_mc:
        self[fill_btag_wp_count_hists](
            events,
            event_mask=results.event,
            # Boolean mask over the full Jet collection, not the index array in
            # results.objects.Jet.Jet. Upstream applies this before the event
            # mask (`events.Jet[jet_mask][event_mask]`, btag.py:72), so passing
            # indices selects the wrong jets and undercounts.
            jet_mask=results.aux["jet_mask"],
            hists=hists,
        )

    return events, results


@default.init
def default_init(
    self: Selector,
    **kwargs,
) -> None:
    """
    Declare the shifts that change the event selection.

    This has to live on the *selector*: SelectEvents and ReduceEvents set
    register_selector_shifts = True (columnflow tasks/selection.py,
    tasks/reduction.py), so only then do their local shift -- and hence the
    column aliases -- respond. The calibrators write every varied column in the
    nominal pass, so CalibrateEvents does not rerun per shift.

    Only the lepton momentum shifts are selection dependent. The JES/JER shifts
    are registered on the producer instead (production/default.py): no event or
    object cut at selection depends on the jet pT variation (jet_selection keeps
    every jet that passes pT > 30 in ANY variation), so they only need
    ProduceColumns to rerun.
    """
    if not getattr(self, "dataset_inst", None):
        return
    if self.dataset_inst.is_data:
        self.uses |= {"run", "ecal_badcrystal_veto"}
        return

    self.shifts |= {
        shift_inst.name
        for shift_inst in get_shifts_from_sources(self.config_inst, *self.config_inst.x.lepton_shift_sources)
    }
