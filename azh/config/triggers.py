"""
Trigger definitions for 2022-2024.

The analysis uses the single-lepton OR only, IsoMu24 || Ele30_WPTight, in every
era. Reasons (pre-flight studies, see PREFLIGHT_CHANGES.md):

  * it selects 99.64% of offline 3l events on ttZ MC; the dilepton paths add
    0.26% and have no POG scale factors, MuonEG cross triggers add < 0.1%;
  * EGM and MUO publish data and MC efficiencies for exactly these two paths,
    so the per-lepton event-level trigger SF (production/trigger_weights.py)
    covers every selected event;
  * IsoMu27 never fired without IsoMu24 on ttZ MC, so it is redundant.

The selection uses the HLT decision only. The legs below are NOT used by
selection/trigger.py; they document the TrigObj filter bits validated against
NanoAOD's own TrigObj_filterBits documentation and against the HLT decision
(eff = 1.000 in data and MC), for future offline-lepton trigger matching:

  v12 (2022/2023):  Ele30 -> bit 1 "1e (WPTight)"     (the old bit 19 does not exist in v12)
  v15 (2024):       Ele30 -> bit 18 "1e (HLT30WPTightGSfTrackIso)"
  all:              IsoMu24 -> bit 1 "Iso" AND bit 3 "1mu"
"""

import order as od

from azh.config.util import Trigger, TriggerLeg


def add_triggers(config: od.Config) -> None:
    """
    Register the single-lepton trigger OR on *config* (all Run 3 eras).
    """
    nano_v15 = config.campaign.x.year >= 2024
    ele30_bits = 2**18 if nano_v15 else 2**1

    config.x.triggers = od.UniqueObjectIndex(
        Trigger,
        [
            Trigger(
                name="HLT_IsoMu24",
                id=101,
                legs=[
                    # documentation only, see module docstring
                    TriggerLeg(pdg_id=13, min_pt=24.0, trigger_bits=[2**1, 2**3]),
                ],
                applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or dataset_inst.has_tag("mu")),
                tags={"single_mu"},
            ),
            Trigger(
                name="HLT_Ele30_WPTight_Gsf",
                id=201,
                legs=[
                    # documentation only, see module docstring
                    TriggerLeg(pdg_id=11, min_pt=30.0, trigger_bits=ele30_bits),
                ],
                applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or dataset_inst.has_tag("egamma")),
                tags={"single_e"},
            ),
        ],
    )
