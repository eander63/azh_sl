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
from columnflow.production.cms.scale import murmuf_weights, murmuf_envelope_weights
from azh.production.trigger_weights import trigger_weights
from azh.production.channel_lumi_weight import channel_lumi_weight
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


@producer(
    uses={"pt_z"},
    produces={"zpt_weight"},
    mc_only=True,
)
def zpt_reweight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Z pT reweighting to correct NLO DY modeling deficiency at 5-15 GeV.
    PLACEHOLDER: derive bin weights from v3 data/MC ratio in pt_z.
    Set all weights to 1.0 until you have the real values.
    """
    # Derived from v3 data/MC ratio in pt_z_fine (inclusive, all 22 datasets)
    pt_bins = np.array([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 23, 26, 30, 35, 40, 50, 60, 100], dtype=np.float32)
    wt_vals = np.array([1.0122, 0.9431, 0.9144, 0.9531, 1.0157, 1.0734, 1.1036, 1.1138, 1.1090, 1.0926, 1.0779, 1.0472, 1.0073, 0.9771, 0.9625, 0.9677, 0.9835, 1.0], dtype=np.float32)

    pt = ak.to_numpy(events.pt_z)
    idx = np.clip(np.searchsorted(pt_bins, pt) - 1, 0, len(wt_vals) - 1)
    w = ak.Array(wt_vals[idx])

    events = set_ak_column(events, "zpt_weight", ak.values_astype(w, np.float32))
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

muon_reco_weights = muon_weights.derive("muon_reco_weights", cls_dict={
    "weight_name": "muon_reco_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_reco_names),
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
        # all post-reduction electrons already pass the tight ID selection
        ele_all = ak.ones_like(events.Electron.pt, dtype=bool)
        electron_mask = (events.Electron.pt >= 75)
        electron_mask_mid = (events.Electron.pt >= 20) & (events.Electron.pt < 75)

        events = self[electron_weights](events, electron_mask=electron_mask, **kwargs)
        events = self[electron_mid_weights](events, electron_mask=electron_mask_mid, **kwargs)
        events = self[electron_id_weights](events, electron_mask=ele_all, **kwargs)

        # compute muon weights
        # events = self[muon_weights](events, **kwargs)
        # events = self[muon_reco_weights](events, **kwargs)  # disabled: not needed for TightID
        events = self[muon_id_weights](events, **kwargs)
        events = self[muon_iso_weights](events, **kwargs)

        # compute trigger weights
        events = self[trigger_weights](events, **kwargs)

        # apply per-channel luminosity correction
        events = self[channel_lumi_weight](events, **kwargs)

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

        # Z pT reweighting (NLO DY modeling correction) — DISABLED
        # events = self[zpt_reweight](events, **kwargs)
        if not self.dataset_inst.has_tag("no_lhe_weights"):
            events = self[murmuf_weights](events, **kwargs)
            events = self[murmuf_envelope_weights](events, **kwargs)

    return events


@weights.init
def weights_init(self: Producer) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        # dynamically add dependencies if running on MC
        self.uses |= {
            electron_weights, electron_id_weights, electron_mid_weights,
            muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, top_pt_weight, murmuf_envelope_weights, murmuf_weights,
            # zpt_reweight,  # DISABLED
            split_btag_weights,
            trigger_weights, channel_lumi_weight,
        }
        self.produces |= {
            electron_weights, electron_id_weights, electron_mid_weights,
            muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, top_pt_weight, murmuf_envelope_weights, murmuf_weights,
            # zpt_reweight,  # DISABLED
            split_btag_weights,
            trigger_weights, channel_lumi_weight,
        }
