# coding: utf-8

"""
Producers related to event weights.
"""

from columnflow.production import Producer, producer
from azh.production.normalized_weights import normalized_weight_factory
from columnflow.columnar_util import set_ak_column, has_ak_column, Route

import law

logger = law.logger.get_logger(__name__)
from azh.production.btag import split_btag_wp_weights
from azh.production.jets import analysis_jet_mask
from columnflow.production.cms.electron import electron_weights, ElectronSFConfig
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.normalization import normalization_weights
from azh.production.theory import pdf_hessian_weights, ps_weights, lumi_weight
from columnflow.production.cms.scale import murmuf_weights, murmuf_envelope_weights
from azh.production.trigger_weights import trigger_weights
from azh.production.muon_sf import muon_sf_weights
from azh.production.pileup import pu_weight
from columnflow.util import maybe_import

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
            weight = weight * Route(column).apply(events)
        for column in self.dataset_inst.x("event_weights", []):
            if has_ak_column(events, column):
                weight = weight * Route(column).apply(events)
            else:
                logger.warning_once(
                    f"missing_dataset_weight_{column}",
                    f"weight '{column}' for dataset {self.dataset_inst.name} not found",
                )

    events = set_ak_column(events, "event_weight", weight)

    return events


electron_id_weights = electron_weights.derive("electron_id_weights", cls_dict={
    "weight_name": "electron_id_weight",
    "get_electron_config": (lambda self: ElectronSFConfig.new(self.config_inst.x.electron_sf_id_names)),
})

electron_mid_weights = electron_weights.derive("electron_mid_weights", cls_dict={
    "weight_name": "electron_mid_weight",
    "get_electron_config": (lambda self: ElectronSFConfig.new(self.config_inst.x.electron_sf_mid_names)),
})

electron_loreco_weights = electron_weights.derive("electron_loreco_weights", cls_dict={
    "weight_name": "electron_loreco_weight",
    "get_electron_config": (lambda self: ElectronSFConfig.new(self.config_inst.x.electron_sf_loreco_names)),
})

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
    weight_producers={murmuf_weights, murmuf_envelope_weights, pdf_hessian_weights},
    weight_names={
        f"{base}_weight{postfix}"
        for base in ("mur", "muf", "murmuf_envelope", "pdf")
        for postfix in ("", "_up", "_down")
    },
)

# Shape-only parton-shower ISR/FSR variations, normalized per process like the
# scale weights (the sums are booked in the selector).
normalized_ps_weights = normalized_weight_factory(
    producer_name="normalized_ps_weights",
    weight_producers={ps_weights},
    weight_names={f"{base}_weight{postfix}" for base in ("isr", "fsr") for postfix in ("", "_up", "_down")},
)


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

        electron_mask = ele_tight & (events.Electron.pt >= 75)
        electron_mask_mid = ele_tight & (events.Electron.pt >= 20) & (events.Electron.pt < 75)
        electron_mask_lo = ele_tight & (events.Electron.pt >= 10) & (events.Electron.pt < 20)

        events = self[electron_weights](events, electron_mask=electron_mask, **kwargs)
        events = self[electron_mid_weights](events, electron_mask=electron_mask_mid, **kwargs)
        events = self[electron_loreco_weights](events, electron_mask=electron_mask_lo, **kwargs)
        events = self[electron_id_weights](events, electron_mask=ele_tight, **kwargs)

        # muon ID / iso SFs with separate stat and syst variations
        # (production/muon_sf.py); tight muons above the SF binning floor
        events = self[muon_sf_weights](events, **kwargs)

        # compute trigger weights
        events = self[trigger_weights](events, **kwargs)

        # b-tag weights on the analysis jets (candidates with pT > 30; under a
        # JES/JER shift the aliased pT decides which jets count)
        events = self[split_btag_wp_weights](events, jet_mask=analysis_jet_mask(events), **kwargs)

        # compute normalization weights
        events = self[normalization_weights](events, **kwargs)

        # compute pu weights
        events = self[pu_weight](events, **kwargs)

        # normalize pu weight per process (produces 'normalized_pu_weight')
        events = self[normalized_pu_weight](events, **kwargs)

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
        if not self.dataset_inst.has_tag("no_ps_weights"):
            events = self[normalized_ps_weights](events, **kwargs)

        # luminosity as a weight shift, for plot uncertainty bands only
        events = self[lumi_weight](events, **kwargs)

    return events


@weights.init
def weights_init(
    self: Producer,
    **kwargs,
) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        # dynamically add dependencies if running on MC
        self.uses |= {
            # tight-ID columns, used to mask which leptons receive scale factors
            "Electron.mvaIso_WP80", "Muon.tightId", "Muon.pfRelIso04_all",
            electron_weights, electron_id_weights, electron_mid_weights, electron_loreco_weights,
            muon_sf_weights,
            normalization_weights, mc_weight, pu_weight, normalized_pu_weight, murmuf_envelope_weights, murmuf_weights,
            pdf_hessian_weights, normalized_scale_weights, normalized_ps_weights, lumi_weight,
            split_btag_wp_weights,
            trigger_weights,
        }
        self.produces |= {
            electron_weights, electron_id_weights, electron_mid_weights, electron_loreco_weights,
            muon_sf_weights,
            normalization_weights, mc_weight, pu_weight, normalized_pu_weight, murmuf_envelope_weights, murmuf_weights,
            pdf_hessian_weights, normalized_scale_weights, normalized_ps_weights, lumi_weight,
            split_btag_wp_weights,
            trigger_weights,
        }
