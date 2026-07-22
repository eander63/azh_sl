# coding: utf-8

"""
Column production methods related to higher-level features.
"""


from columnflow.production import Producer, producer
from columnflow.production.categories import category_ids
from columnflow.production.normalization import normalization_weights
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
# from columnflow.production.cms.btag import btag_weights

from azh.production.z_boson import z_boson
from azh.production.higgs_reco import higgs_reco
from azh.production.prepare_objects import prepare_objects
from azh.production.leptons import choose_lepton
from azh.production.leptons import three_lepton_info
from azh.production.dy_producer import dy_producer
from azh.production.weights import weights, event_weight
from azh.config.categories import add_categories_production


ak = maybe_import("awkward")
coffea = maybe_import("coffea")
np = maybe_import("numpy")
maybe_import("coffea.nanoevents.methods.nanoaod")


@producer(
    uses={
        category_ids, normalization_weights,
        weights, z_boson, higgs_reco, choose_lepton, three_lepton_info,
        prepare_objects, event_weight, "MET.pt","MET.phi","process_id","cutflow*",
    },
    produces={
        category_ids, normalization_weights,
        weights, z_boson, choose_lepton, three_lepton_info,
        higgs_reco, event_weight, "event_number","process_id",
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    # category ids
    events = self[choose_lepton](events, **kwargs)
    events = self[three_lepton_info](events, **kwargs)
    events = self[prepare_objects](events, **kwargs)
    events = self[z_boson](events, **kwargs)
    events = self[higgs_reco](events, **kwargs)
    events = self[category_ids](events, **kwargs)
    # mc-only weights
    if self.dataset_inst.is_mc:
        # normalization weights
        events = self[weights](events, **kwargs)
        events = self[event_weight](events, **kwargs)
        if self.dataset_inst.has_tag("is_dy"):
            events = self[dy_producer](events, **kwargs)
    events = set_ak_column(events, "event_number", events.event)
    return events


@default.init
def default_init(self: Producer) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.has_tag("is_dy"):
        self.uses.add(dy_producer)
        self.produces.add(dy_producer)
    # single entry point for the 3-axis scheme (multiplicity x flavor x region);
    # call_once_on_config makes this idempotent
    add_categories_production(self.config_inst)
    
