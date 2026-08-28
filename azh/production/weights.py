# coding: utf-8

"""
Producers related to event weights.
"""

from columnflow.production import Producer, producer
from azh.production.normalized_weights import normalized_weight_factory
from columnflow.columnar_util import set_ak_column, has_ak_column, Route
from columnflow.production.cms.btag import split_btag_weights
from columnflow.production.cms.electron import electron_weights
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.muon import muon_weights
from columnflow.production.normalization import normalization_weights
from columnflow.production.cms.pdf import pdf_weights
from columnflow.production.cms.scale import murmuf_weights, murmuf_envelope_weights
from azh.production.trigger_weights import trigger_weights
from azh.production.channel_lumi_weight import channel_lumi_weight
from azh.production.pileup import pu_weight
from columnflow.util import maybe_import

from azh.production.gen_top import top_pt_weight
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

electron_loreco_weights = electron_weights.derive("electron_loreco_weights", cls_dict={
    "weight_name": "electron_loreco_weight",
    "get_electron_config": (lambda self: self.config_inst.x.electron_sf_loreco_names),
})

muon_id_weights = muon_weights.derive("muon_id_weights", cls_dict={
    "weight_name": "muon_id_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_id_names),
})

# Lower edge of the muon_Z.json ID/iso pT binning. Muons below this get no
# ID/iso scale factor (weight 1) rather than an out-of-range corrector call.
# If the MUO POG JSON is ever revised to extend lower, verify with:
#   raw["corrections"][...]["data"] -> binning node with input "pt"
MUON_SF_PT_MIN = 15.0

normalized_pu_weight = normalized_weight_factory(
    producer_name="normalized_pu_weight",
    weight_producers={pu_weight},
)

# Shape-only scale and PDF variations (AN-2022/158 Sec. 9.1): the factory divides
# each weight by its per-process sum, so an up/down variation redistributes events
# across the template without changing the process yield. The normalization effect
# is already covered by the inclusive cross-section rate nuisances.
# Produces normalized_{mur,muf,murmuf_envelope,pdf}_weight{,_up,_down}.
normalized_scale_weights = normalized_weight_factory(
    producer_name="normalized_scale_weights",
    weight_producers={murmuf_weights, murmuf_envelope_weights, pdf_weights},
)

muon_iso_weights = muon_weights.derive("muon_iso_weights", cls_dict={
    "weight_name": "muon_iso_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_iso_names),
})

muon_reco_weights = muon_weights.derive("muon_reco_weights", cls_dict={
    "weight_name": "muon_reco_weight",
    "get_muon_config": (lambda self: self.config_inst.x.muon_sf_reco_names),
})

@producer
def weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Main event weight producer (e.g. MC generator, scale factors, normalization).
    """
    if self.dataset_inst.is_mc:
        # Kept leptons are the LOOSE collections (see lepton_selection):
        # electrons are mvaIso_WP90, muons are looseId + relIso < 0.25. Only the
        # tight subset enters the analysis selection, so only those get reco/ID
        # scale factors. In 3l this changes nothing--the 4th-lepton veto
        # already forces every kept lepton to be tight--but 2l has no loose
        # veto by design, so extra loose-not-tight leptons would otherwise
        # contribute spurious weight factors to the DY validation region.
        ele_tight = events.Electron.mvaIso_WP80
        mu_tight = events.Muon.tightId & (events.Muon.pfRelIso04_all < 0.15)

        electron_mask = ele_tight & (events.Electron.pt >= 75)
        electron_mask_mid = ele_tight & (events.Electron.pt >= 20) & (events.Electron.pt < 75)
        electron_mask_lo = ele_tight & (events.Electron.pt >= 10) & (events.Electron.pt < 20)

        events = self[electron_weights](events, electron_mask=electron_mask, **kwargs)
        events = self[electron_mid_weights](events, electron_mask=electron_mask_mid, **kwargs)
        events = self[electron_loreco_weights](events, electron_mask=electron_mask_lo, **kwargs)
        events = self[electron_id_weights](events, electron_mask=ele_tight, **kwargs)

        # compute muon weights
        # muon_Z.json ID/iso bins start at 15 GeV, NOT 10 as previously claimed
        # here (verified against Run3-22CDSep23-Summer22-NanoAODv12/muon_Z.json.gz:
        # NUM_TightID_DEN_TrackerMuons and NUM_TightPFIso_DEN_TightID both have pt
        # binning [15.0, inf]). PT_FLOOR in lepton_selection is 10, so tight muons
        # below 15 exist and used to make correctionlib raise "Index below bounds".
        #
        # Restricting rather than clamping is the physics-correct choice: the
        # analysis pT thresholds (25/20/15) are applied downstream as categories,
        # so no *selected* lepton is ever below 15 GeV. A sub-15 tight muon is
        # always an extra lepton, and giving it an efficiency correction adds a
        # spurious factor -- precisely what the tight-subset masking above exists
        # to avoid in the 2l regions, which have no loose veto.
        muon_mask_sf = mu_tight & (events.Muon.pt >= MUON_SF_PT_MIN)
        events = self[muon_id_weights](events, muon_mask=muon_mask_sf, **kwargs)
        events = self[muon_iso_weights](events, muon_mask=muon_mask_sf, **kwargs)
        
        # compute trigger weights
        events = self[trigger_weights](events, **kwargs)

        # apply per-channel luminosity correction
        events = self[channel_lumi_weight](events, **kwargs)

        # compute btag weights
        events = self[split_btag_weights](events, **kwargs)

        # # compute top pT weights (disabled for now)
        if self.dataset_inst.has_tag("is_ttbar"):
            events = self[top_pt_weight](events, **kwargs)

        # compute normalization weights
        events = self[normalization_weights](events, **kwargs)

        # compute pu weights
        events = self[pu_weight](events, **kwargs)

        # normalize pu weight per process (produces 'normalized_pu_weight')
        events = self[normalized_pu_weight](events, **kwargs)

        # Z pT reweighting (NLO DY modeling correction) — DISABLED
        # events = self[zpt_reweight](events, **kwargs)
        if not self.dataset_inst.has_tag("no_lhe_weights"):
            # NOTE: mur/muf/envelope/pdf weights are computed in the *selector*
            # (they have to be, so increment_stats can book their per-process
            # sums) and survive reduction via the 'mur_weight*', 'muf_weight*',
            # 'murmuf_envelope_weight*' and 'pdf_weight*' entries in
            # cfg.x.keep_columns. Recomputing them here is not just redundant, it
            # is impossible for PDF: LHEScaleWeight is kept after reduction but
            # LHEPdfWeight is not, so pdf_weights would raise
            # "did not receive any columns matching: LHEPdfWeight".
            #
            # normalized_scale_weights reads the kept columns directly. It only
            # falls back to re-running a weight producer when that producer's
            # *used* columns are present (normalized_weights.py:44-47), which
            # they are not here, so no fallback is attempted.
            events = self[normalized_scale_weights](events, **kwargs)

    return events


@weights.init
def weights_init(self: Producer) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        # dynamically add dependencies if running on MC
        self.uses |= {
            # tight-ID columns, used to mask which leptons receive scale factors
            "Electron.mvaIso_WP80", "Muon.tightId", "Muon.pfRelIso04_all",
            electron_weights, electron_id_weights, electron_mid_weights, electron_loreco_weights,
            muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, normalized_pu_weight, top_pt_weight, murmuf_envelope_weights, murmuf_weights,
            pdf_weights, normalized_scale_weights,
            # zpt_reweight,  # DISABLED
            split_btag_weights,
            trigger_weights, channel_lumi_weight,
        }
        self.produces |= {
            electron_weights, electron_id_weights, electron_mid_weights, electron_loreco_weights,
            muon_id_weights, muon_iso_weights,
            normalization_weights, mc_weight, pu_weight, normalized_pu_weight, top_pt_weight, murmuf_envelope_weights, murmuf_weights,
            pdf_weights, normalized_scale_weights,
            # zpt_reweight,  # DISABLED
            split_btag_weights,
            trigger_weights, channel_lumi_weight,
        }
