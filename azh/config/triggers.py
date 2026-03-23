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
    config.x.triggers = od.UniqueObjectIndex(Trigger, [

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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("egamma")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("egamma")),
            tags={"di_e"},
        ),
    ])

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
    config.x.triggers = od.UniqueObjectIndex(Trigger, [

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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("egamma")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("mu")),
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
            applies_to_dataset=(lambda dataset_inst: dataset_inst.is_mc or
                dataset_inst.has_tag("egamma")),
            tags={"di_e"},
        ),
    ])

    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_IsoMu24": 1,
        "HLT_IsoMu27": 2,
        "HLT_Ele30_WPTight_Gsf": 3,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 4,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 5,
    }
