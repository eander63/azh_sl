"""
Definition of triggers
"""

import order as od

from azh.config.util import Trigger, TriggerLeg


def add_triggers_2022(config: od.Config) -> None:
    """
    Adds all triggers to a *config*. For the conversion from filter names to trigger bits, see
    https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/triggerObjects_cff.py.
    Electron Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTRunIIISummary
    Muon Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/MuonHLT2022
    """
    config.x.triggers = od.UniqueObjectIndex(
        Trigger,
        [
            # Single muon — primary trigger for Z→μμ
            # Bit 1 (value 2): Iso filter (hltL3crIso*IsoFiltered), covers HLT_IsoMu24
            Trigger(
                name="HLT_IsoMu24",
                id=101,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=26.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            # Bit 1 (value 2): Iso filter, covers HLT_IsoMu27
            Trigger(
                name="HLT_IsoMu27",
                id=103,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=29.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            # Single electron — primary trigger for Z→ee
            # Bit 19 (value 2**19): hltEle30WPTightGsfTrackIsoFilter
            Trigger(
                name="HLT_Ele30_WPTight_Gsf",
                id=201,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=32.0,
                        trigger_bits=2**19,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"single_e"},
            ),
            # Di-muon — supplemental for lower-pT muon pairs
            # Bit 0 (value 1): TrkIsoVVL filter
            Trigger(
                name="HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8",
                id=102,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=18.0,
                        trigger_bits=1,
                    ),
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=10.0,
                        trigger_bits=1,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"di_mu"},
            ),
            # Di-electron — supplemental
            # Bit 0 (value 2**0): CaloIdL_TrackIdL_IsoVL leg 1
            # Bit 5 (value 2**5): CaloIdL_TrackIdL_IsoVL leg 2
            Trigger(
                name="HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL",
                id=202,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=24.0,
                        trigger_bits=2**0,
                    ),
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=13.0,
                        trigger_bits=2**5,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"di_e"},
            ),
        ],
    )

    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_IsoMu24": 1,
        "HLT_IsoMu27": 2,
        "HLT_Ele30_WPTight_Gsf": 3,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 4,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 5,
    }


def add_triggers_2023(config: od.Config) -> None:
    """
    Adds all triggers to a *config*. For the conversion from filter names to trigger bits, see
    https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/triggerObjects_cff.py.
    Electron Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTRunIIISummary
    Muon Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/MuonHLT2022
    """
    config.x.triggers = od.UniqueObjectIndex(
        Trigger,
        [
            # Single muon — primary trigger for Z→μμ
            Trigger(
                name="HLT_IsoMu24",
                id=101,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=26.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            Trigger(
                name="HLT_IsoMu27",
                id=103,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=29.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            # Single electron — primary trigger for Z→ee
            Trigger(
                name="HLT_Ele30_WPTight_Gsf",
                id=201,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=32.0,
                        trigger_bits=2**19,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"single_e"},
            ),
            # Di-muon — supplemental
            Trigger(
                name="HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8",
                id=102,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=18.0,
                        trigger_bits=1,
                    ),
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=10.0,
                        trigger_bits=1,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"di_mu"},
            ),
            # Di-electron — supplemental
            Trigger(
                name="HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL",
                id=202,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=24.0,
                        trigger_bits=2**0,
                    ),
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=13.0,
                        trigger_bits=2**5,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"di_e"},
            ),
        ],
    )

    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_IsoMu24": 1,
        "HLT_IsoMu27": 2,
        "HLT_Ele30_WPTight_Gsf": 3,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 4,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 5,
    }


def add_triggers_2024(config: od.Config) -> None:
    """
    Adds all triggers to a *config* for the 2024 (Run3Summer24) era.
    The campaign is NanoAOD v15; repacked the electron ``TrigObj.filterBits``
    relative to v12. The muon bits (TrkIsoVVL = 1, Iso = 2) are stable across
    v12/v14/v15; the electron bits below are not the same numbers as in
    ``add_triggers_2022`` / ``add_triggers_2023`` for that reason.

    Bit reference for v15:
    https://github.com/cms-sw/cmssw/blob/CMSSW_15_0_X/PhysicsTools/NanoAOD/python/triggerObjects_cff.py

    VERIFY BEFORE TRUSTING EFFICIENCIES: the two electron entries marked below
    were derived from the v15 filter table, not measured. A wrong bit does not
    raise -- it silently drops or keeps the wrong objects. Cross-check by
    plotting the trigger-matching efficiency vs. offline pT on a small run and
    confirming the turn-on sits at the expected threshold.
    """
    config.x.triggers = od.UniqueObjectIndex(
        Trigger,
        [
            # Single muon — primary trigger for Z→μμ
            # Bit 1 (value 2): Iso filter. Unchanged v12 → v15.
            Trigger(
                name="HLT_IsoMu24",
                id=101,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=26.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            # Bit 1 (value 2): Iso filter. Unchanged v12 → v15.
            Trigger(
                name="HLT_IsoMu27",
                id=103,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=29.0,
                        trigger_bits=2,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"single_mu"},
            ),
            # Single electron — primary trigger for Z→ee
            # VERIFY. v15 introduced a dedicated bit 18 (value 2**18) for
            # hltEle30WPTightGsfTrackIsoFilter ("SingleEle_HLT30WPTightGSfTrackIso").
            # The 2**19 used for 2022/23 is a *different* filter in v15
            # (VBFWPTightGsfTrackIso), so it must not be carried over verbatim.
            Trigger(
                name="HLT_Ele30_WPTight_Gsf",
                id=201,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=32.0,
                        trigger_bits=2**18,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"single_e"},
            ),
            # Di-muon — supplemental
            # Bit 0 (value 1): TrkIsoVVL filter. Unchanged v12 → v15.
            Trigger(
                name="HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8",
                id=102,
                legs=[
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=18.0,
                        trigger_bits=1,
                    ),
                    TriggerLeg(
                        pdg_id=13,
                        min_pt=10.0,
                        trigger_bits=1,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("mu")
                    )
                ),
                tags={"di_mu"},
            ),
            # Di-electron — supplemental
            # VERIFY. Leg 1 keeps bit 0 (CaloIdLTrackIdLIsoVL, unchanged v12 → v15).
            # Leg 2 uses v15 "DiElectronLeg2" = 2**5. Note this is numerically the
            # same value as the 2022/23 config uses, but for a different reason:
            # in v12, 2**5 is the MuEle filter, and DiElectron is a single bit 2**4.
            Trigger(
                name="HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL",
                id=202,
                legs=[
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=24.0,
                        trigger_bits=2**4,
                    ),
                    TriggerLeg(
                        pdg_id=11,
                        min_pt=13.0,
                        trigger_bits=2**5,
                    ),
                ],
                applies_to_dataset=(
                    lambda dataset_inst: (
                        dataset_inst.is_mc or dataset_inst.has_tag("egamma")
                    )
                ),
                tags={"di_e"},
            ),
        ],
    )

    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_IsoMu24": 1,
        "HLT_IsoMu27": 2,
        "HLT_Ele30_WPTight_Gsf": 3,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 4,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 5,
    }
