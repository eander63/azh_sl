# coding: utf-8
"""
Per-channel luminosity correction (era-aware).

Background (2022preEE motivation):
    The Muon primary dataset only existed starting Run2022C run 356426, so
    the muon channel sees less integrated lumi than the EGamma channel.
    Without correction MC overestimates muon-channel yields by ~6%.

For other eras the correction is generally close to (but not exactly) 1.0
since the Muon and EGamma PDs run end-to-end. The per-era effective lumi
values are read from ``cfg.x.channel_lumis``, populated in
``azh/config/config_run3.py``:

    cfg.x.channel_lumis = {
        "muon":    7448.0,   # muon-channel effective lumi /pb
        "egamma":  7989.5,   # ee-channel effective lumi   /pb
        "nominal": 7971.0,   # what cfg.x.luminosity is normalized to
    }

If the dict is absent the producer falls back to SF=1.0 on both channels
and prints a one-time warning.

Per-era brilcalc procedure (recommended):
    brilcalc lumi -c web -i <GOLDEN.json> --hltpath "HLT_IsoMu24*"   --byls
    brilcalc lumi -c web -i <GOLDEN.json> --hltpath "HLT_Ele30_WPTight_Gsf*" --byls
"""

from columnflow.production import Producer, producer
from columnflow.columnar_util import set_ak_column
from columnflow.util import maybe_import, InsertableDict

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    uses={"cutflow.n_muo_loose", "cutflow.n_ele_loose"},
    produces={"channel_lumi_weight"},
    mc_only=True,
)
def channel_lumi_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """Per-event channel-dependent lumi rescaling factor."""
    is_mumu = events.cutflow.n_muo_loose >= 2
    is_ee = events.cutflow.n_ele_loose >= 2

    weight = ak.ones_like(events.event, dtype=np.float32)
    weight = ak.where(is_mumu, np.float32(self.sf_muon), weight)
    weight = ak.where(is_ee,   np.float32(self.sf_electron), weight)

    events = set_ak_column(events, "channel_lumi_weight", weight)
    return events


@channel_lumi_weight.setup
def channel_lumi_weight_setup(
    self: Producer,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
) -> None:
    lumis = self.config_inst.x("channel_lumis", None)
    if not lumis:
        self.logger.warning_once(
            "channel_lumis_missing",
            f"cfg.x.channel_lumis is not set for config '{self.config_inst.name}'; "
            "channel_lumi_weight will fall back to SF=1.0 for both channels. "
            "Set it in config_run3.py or accept the bias.",
        )
        self.sf_muon = 1.0
        self.sf_electron = 1.0
        return

    nominal = float(lumis["nominal"])
    self.sf_muon     = float(lumis["muon"])   / nominal
    self.sf_electron = float(lumis["egamma"]) / nominal
