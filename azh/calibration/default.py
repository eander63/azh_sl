# coding: utf-8

"""
Composite calibrators for AZH. Orchestrators only: they import the
correction definitions from azh.calibration.corrections and run them in
order. The active default is skip_jecunc (see cfg.x.default_calibrator).
"""

from columnflow.calibration import Calibrator, calibrator
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.seeds import deterministic_seeds

from azh.calibration.corrections import (
    jet_energy,
    jet_lepton_cleaner,
    muon_scare,
    electron_ss,
)


@calibrator(
    uses={mc_weight, deterministic_seeds, jet_lepton_cleaner, jet_energy, muon_scare, electron_ss},
    produces={mc_weight, deterministic_seeds, jet_lepton_cleaner, jet_energy, muon_scare, electron_ss},
)
def skip_jecunc(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """ only uses jec_nominal for test purposes """
    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
        events = self[deterministic_seeds](events, **kwargs)
    events = self[jet_lepton_cleaner](events, **kwargs)
    events = self[jet_energy](events, **kwargs)
    events = self[muon_scare](events, **kwargs)
    events = self[electron_ss](events, **kwargs)

    return events
