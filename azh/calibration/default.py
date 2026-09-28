"""
Composite calibrators for AZH. Orchestrators only: they import the
correction definitions from azh.calibration.corrections and run them in
order. The active default is skip_jecunc (see cfg.x.default_calibrator).
"""

from columnflow.calibration import Calibrator, calibrator
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.seeds import deterministic_seeds
from columnflow.util import maybe_import

ak = maybe_import("awkward")

from azh.calibration.corrections import (
    ecal_badcrystal_veto,
    electron_ss,
    jet_energy,
    jet_id_v15,
    met_unclustered_apply,
    met_unclustered_capture,
    muon_scare,
)


@calibrator(
    uses={mc_weight, deterministic_seeds, ecal_badcrystal_veto, jet_energy, muon_scare, electron_ss},
    produces={mc_weight, deterministic_seeds, ecal_badcrystal_veto, jet_energy, muon_scare, electron_ss},
)
def skip_jecunc(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Default calibrator (the name is historical: MC runs JEC *with* uncertainties).

    Order matters: everything that must see the untouched NanoAOD jets / MET
    (ECAL bad-crystal veto, MET unclustered capture) runs before jet_energy.
    """
    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
        events = self[deterministic_seeds](events, **kwargs)
        events = self[met_unclustered_capture](events, **kwargs)
    else:
        events = self[ecal_badcrystal_veto](events, **kwargs)
    if self.config_inst.x.jet_id.from_correctionlib:
        events = self[jet_id_v15](events, **kwargs)
    events = self[jet_energy](events, **kwargs)
    if self.dataset_inst.is_mc:
        events = self[met_unclustered_apply](events, **kwargs)
    events = self[muon_scare](events, **kwargs)
    events = self[electron_ss](events, **kwargs)
    return events


@skip_jecunc.init
def skip_jecunc_init(self: Calibrator, **kwargs) -> None:
    extra = set()
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        extra |= {met_unclustered_capture, met_unclustered_apply}
    if self.config_inst.x.jet_id.from_correctionlib:
        extra.add(jet_id_v15)
    self.uses |= extra
    self.produces |= extra
