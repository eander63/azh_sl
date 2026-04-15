# coding: utf-8
"""
Per-channel luminosity correction.

The Muon primary dataset only existed starting Run2022C run 356426, so the
muon channel sees less integrated luminosity than the electron channel:
  - Muon (C+D, runs 356426-357900): 7448 pb^-1
  - EGamma (C+D full):              7989 pb^-1
  - Config nominal lumi:            7971 pb^-1

This producer applies a multiplicative weight on muon-channel events to scale
their MC normalization to the actual muon-channel lumi, leaving electron-channel
events at the config-nominal lumi (close enough at 0.2% off).

Reference: brilcalc with golden JSON Cert_Collisions2022_355100_362760_Golden.json
"""

from columnflow.production import Producer, producer
from columnflow.columnar_util import set_ak_column
from columnflow.util import maybe_import

ak = maybe_import("awkward")
np = maybe_import("numpy")


# computed values (verified by brilcalc 2026-04-15):
LUMI_MUON_C_PLUS_D = 7448.0       # /pb, Muon PD, runs 356426-357900
LUMI_EGAMMA_C_PLUS_D = 7989.5     # /pb, EGamma PD, runs 355862-357900
LUMI_CONFIG_NOMINAL = 7971.0      # /pb, what cfg.x.luminosity is set to

# scale factors (data_lumi / config_nominal)
SF_MUON_CHANNEL = LUMI_MUON_C_PLUS_D / LUMI_CONFIG_NOMINAL          # ~0.9344
SF_ELECTRON_CHANNEL = LUMI_EGAMMA_C_PLUS_D / LUMI_CONFIG_NOMINAL    # ~1.0023


@producer(
    uses={"cutflow.n_muo_loose", "cutflow.n_ele_loose"},
    produces={"channel_lumi_weight"},
    mc_only=True,
)
def channel_lumi_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Per-event channel-dependent lumi rescaling factor.
    Identifies the channel from lepton-pair multiplicity and applies the
    appropriate rescaling so MC matches the true integrated lumi of each PD.
    """
    is_mumu = events.cutflow.n_muo_loose >= 2
    is_ee = events.cutflow.n_ele_loose >= 2

    weight = ak.ones_like(events.event, dtype=np.float32)
    weight = ak.where(is_mumu, np.float32(SF_MUON_CHANNEL), weight)
    weight = ak.where(is_ee,   np.float32(SF_ELECTRON_CHANNEL), weight)

    events = set_ak_column(events, "channel_lumi_weight", weight)
    return events
