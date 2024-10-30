# coding: utf-8

"""
Producers related to event weights.
"""

from columnflow.production import Producer, producer
from columnflow.columnar_util import set_ak_column, has_ak_column, Route
from columnflow.production.cms.btag import split_btag_weights
from columnflow.production.cms.electron import electron_weights
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.muon import muon_weights
from columnflow.production.normalization import normalization_weights
from columnflow.production.cms.pileup import pu_weight
from columnflow.util import maybe_import

from azh.production.gen_top import top_pt_weight
# from azh.production.gen_top import gen_parton_top
# from azh.production.normalized_weights import normalized_weight_factory

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    produces={"event_weight"},
    mc_only=True,
)
def event_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Producer that calculates the 'final' event weight (as done in cf.CreateHistograms)
    """
    weight = ak.Array(np.ones(len(events)))
    if self.dataset_inst.is_mc:
        for column in self.config_inst.x.event_weights:
            if (self.dataset_inst.has_tag("is_ttbar") or (column != "top_pt_weight")):
                weight = weight * Route(column).apply(events)
        for column in self.dataset_inst.x("event_weights", []):
            if ((self.dataset_inst.has_tag("is_ttbar")) or (column != "top_pt_weight")):
                if has_ak_column(events, column):
                    weight = weight * Route(column).apply(events)
                else:
                    self.logger.warning_once(
                        f"missing_dataset_weight_{column}",
                        f"weight '{column}' for dataset {self.dataset_inst.name} not found",
                    )

    events = set_ak_column(events, "event_weight", weight)

    return events


electron_id_weights = electron_weights.derive("electron_id_weights", cls_dict={
    "weight_name": "electron_id_weight",
    "get_electron_config": (lambda self: self.config_inst.x.electron_sf_id_names),
})

electron_mid_weights = electron_weights.derive("electron_mid_weights", cls_dict={
    "weight_name": "electron_mid_weight",
    "get_electron_config": (lambda self: self.config_inst.x.electron_sf_mid_names),
})

muon_id_weights = muon_weights.derive("muon_id_weights", cls_dict={
    "weight_name": "muon_id_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_id_names),
})

muon_iso_weights = muon_weights.derive("muon_iso_weights", cls_dict={
    "weight_name": "muon_iso_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_iso_names),
})

# normalized_pu_weights = normalized_weight_factory(
#     producer_name="normalized_pu_weights",
#     weight_producers={pu_weight},
# )


@producer
def weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Main event weight producer (e.g. MC generator, scale factors, normalization).
    """
    if self.dataset_inst.is_mc:
        # compute electron weights
        electron_mask = (events.Electron.pt >= 75)
        electron_mask_mid = ((events.Electron.pt < 75) & (events.Electron.pt < 20))

        events = self[electron_weights](events, electron_mask=electron_mask, **kwargs)
        events = self[electron_mid_weights](events, electron_mask=electron_mask_mid, **kwargs)
        events = self[electron_id_weights](events, **kwargs)

        # compute muon weights
        # events = self[muon_weights](events, **kwargs)
        events = self[muon_id_weights](events, **kwargs)
        events = self[muon_iso_weights](events, **kwargs)

        # compute btag weights
        events = self[split_btag_weights](events, **kwargs)

        # # compute top pT weights (disabled for now)
        if self.dataset_inst.has_tag("is_ttbar"):
            # events = self[gen_parton_top](events, **kwargs)
            events = self[top_pt_weight](events, **kwargs)

        # compute normalization weights
        events = self[normalization_weights](events, **kwargs)

        # compute pu weights
        events = self[pu_weight](events, **kwargs)

    return events


@weights.init
def weights_init(self: Producer) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        # dynamically add dependencies if running on MC
        self.uses |= {
            split_btag_weights, electron_weights, electron_id_weights, electron_mid_weights, muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, top_pt_weight,  # normalized_pu_weights,

        }
        self.produces |= {
            split_btag_weights, electron_weights, electron_id_weights, electron_mid_weights, muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, top_pt_weight,  # normalized_pu_weights,
        }
