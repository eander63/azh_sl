"""
Default producer: leptons, Z candidate, analysis jets, categories, weights,
SR blinding.
"""

from columnflow.columnar_util import set_ak_column
from columnflow.config_util import get_shifts_from_sources
from columnflow.production import Producer, producer
from columnflow.production.categories import category_ids
from columnflow.production.normalization import normalization_weights
from columnflow.util import maybe_import

from azh.config.categories import add_categories_production
from azh.production.categories import catid_3l, catid_baseline
from azh.production.dy_producer import dy_producer
from azh.production.jets import analysis_jets
from azh.production.leptons import choose_lepton, three_lepton_info
from azh.production.prepare_objects import prepare_objects
from azh.production.weights import event_weight, weights
from azh.production.z_boson import z_boson

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    uses={
        category_ids, normalization_weights, weights, z_boson, choose_lepton, three_lepton_info,
        prepare_objects, analysis_jets, event_weight, catid_3l, catid_baseline,
        "PuppiMET.pt", "PuppiMET.phi", "process_id", "cutflow*",
    },
    produces={
        category_ids, normalization_weights, weights, z_boson, choose_lepton, three_lepton_info,
        analysis_jets, event_weight, "event_number", "process_id",
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    events = self[choose_lepton](events, **kwargs)
    events = self[three_lepton_info](events, **kwargs)
    events = self[prepare_objects](events, **kwargs)
    events = self[z_boson](events, **kwargs)
    events = self[analysis_jets](events, **kwargs)
    events = self[category_ids](events, **kwargs)

    # SR blinding: data events in 3l + baseline + >= 1 b-jet belong to NO
    # category, so they cannot reach any histogram (the region categorizers
    # alone would leave them in the parents 3l, 3l__2e, cat_incl, ...).
    if self.dataset_inst.is_data and self.config_inst.x("blind_sr_data", True):
        _, in_3l = self[catid_3l](events, **kwargs)
        _, in_base = self[catid_baseline](events, **kwargs)
        in_sr = in_3l & in_base & (events.n_bjet >= 1)
        keep = ak.broadcast_arrays(~in_sr, events.category_ids)[0]
        events = set_ak_column(events, "category_ids", events.category_ids[keep])

    if self.dataset_inst.is_mc:
        events = self[weights](events, **kwargs)
        events = self[event_weight](events, **kwargs)
        if self.dataset_inst.has_tag("is_dy"):
            events = self[dy_producer](events, **kwargs)
    events = set_ak_column(events, "event_number", events.event)
    return events


@default.init
def default_init(self: Producer, **kwargs) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.has_tag("is_dy"):
        self.uses.add(dy_producer)
        self.produces.add(dy_producer)

    # JES / JER / MET-unclustered shifts are implemented here, not by the
    # selector: registering them on the producer makes ProduceColumns (and
    # histogramming) the shift-local tasks, while Calibrate/Select/Reduce stay
    # nominal. See selection/jet_selection.py for why that is complete.
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        self.shifts |= {
            shift_inst.name
            for shift_inst in get_shifts_from_sources(self.config_inst, *self.config_inst.x.production_shift_sources)
        }

    # single entry point for the 3-axis scheme (multiplicity x flavor x region);
    # call_once_on_config makes this idempotent
    add_categories_production(self.config_inst)
