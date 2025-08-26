"""
Definition of triggers
"""

import order as od

from azh.config.util import Trigger, TriggerLeg

# 2016 triggers as per AN of CMS-HIG-20-010 (AN2018_121_v11-1)

def add_triggers_2022(config: od.Config) -> None:
    """
    Adds all triggers to a *config*. For the conversion from filter names to trigger bits, see
    https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/triggerObjects_cff.py.
    Electron Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTRunIIISummary
    Muon Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/MuonHLT2022
    """
    config.x.triggers = od.UniqueObjectIndex(Trigger, [
   
        #
        # vbf
        #
        Trigger(
            name="HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8",
            id=102,
            legs=[
                TriggerLeg(
                    pdg_id=13,
                    min_pt=25.0,
                    trigger_bits=8 + 32 + 4096,
                ),
                TriggerLeg(
                    pdg_id=13,
                    min_pt=25.0,
                    trigger_bits=8 + 32 + 4096,
                ),
                # # additional leg infos for vbf jets
                # TriggerLeg(
                #     min_pt=115.0,
                #     # filter names:
                #     # The filters are applied to the lepton
                #     # Taking the loosest filter for the Jets with the pt cut
                #     trigger_bits=1,
                # ),
                # TriggerLeg(
                #     min_pt=40.0,
                #     # filter names:
                #     # The filters are applied to the lepton
                #     trigger_bits=1,
                # ),
            ],
            # applies_to_dataset=(lambda dataset_inst: dataset_inst.is_data and config.has_tag("pre")),
            tags={"di_mu"},
        ),

        Trigger(
            name="HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL",
            id=202,
            legs=[
                TriggerLeg(
                    pdg_id=11,
                    min_pt=24.0,
                    trigger_bits=2**4 + 2**0,
                ),
                TriggerLeg(
                    pdg_id=11,
                    min_pt=13.0,
                    trigger_bits=2**4 + 2**0,
                ),
            ],
            tags={"di_e"},
        ),
    ])

    # mapping of trigger columns
    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 1,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 2,
        "HLT_PFMETNoMu120_PFMHTNoMu120_IDTight": 3,
        "HLT_PFMET200_BeamHaloCleaned": 4,
        "HLT_PFHT500_PFMET100_PFMHT100_IDTight": 5,
        "HLT_PFHT700_PFMET85_PFMHT85_IDTight": 6, 
        "HLT_PFHT800_PFMET75_PFMHT75_IDTight": 7,
    }

def add_triggers_2023(config: od.Config) -> None:
    """
    Adds all triggers to a *config*. For the conversion from filter names to trigger bits, see
    https://github.com/cms-sw/cmssw/blob/master/PhysicsTools/NanoAOD/python/triggerObjects_cff.py.
    Electron Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/EgHLTRunIIISummary
    Muon Trigger: https://twiki.cern.ch/twiki/bin/view/CMS/MuonHLT2022
    """
    config.x.triggers = od.UniqueObjectIndex(Trigger, [
   
        #
        # vbf
        #
        Trigger(
            name="HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8",
            id=102,
            legs=[
                TriggerLeg(
                    pdg_id=13,
                    min_pt=25.0,
                    trigger_bits=8 + 32 + 4096,
                ),
                TriggerLeg(
                    pdg_id=13,
                    min_pt=25.0,
                    trigger_bits=8 + 32 + 4096,
                ),
                # # additional leg infos for vbf jets
                # TriggerLeg(
                #     min_pt=115.0,
                #     # filter names:
                #     # The filters are applied to the lepton
                #     # Taking the loosest filter for the Jets with the pt cut
                #     trigger_bits=1,
                # ),
                # TriggerLeg(
                #     min_pt=40.0,
                #     # filter names:
                #     # The filters are applied to the lepton
                #     trigger_bits=1,
                # ),
            ],
            # applies_to_dataset=(lambda dataset_inst: dataset_inst.is_data and config.has_tag("pre")),
            tags={"di_mu"},
        ),

        Trigger(
            name="HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL",
            id=202,
            legs=[
                TriggerLeg(
                    pdg_id=11,
                    min_pt=24.0,
                    trigger_bits=2**4 + 2**0,
                ),
                TriggerLeg(
                    pdg_id=11,
                    min_pt=13.0,
                    trigger_bits=2**4 + 2**0,
                ),
            ],
            tags={"di_e"},
        ),
    ])

    # mapping of trigger columns
    config.x.trigger_map = {
        "All_Events": 0,
        "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8": 1,
        "HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL": 2,
        "HLT_PFMETNoMu120_PFMHTNoMu120_IDTight": 3,
        "HLT_PFMET200_BeamHaloCleaned": 4,
        "HLT_PFHT500_PFMET100_PFMHT100_IDTight": 5,
        "HLT_PFHT700_PFMET85_PFMHT85_IDTight": 6, 
        "HLT_PFHT800_PFMET75_PFMHT75_IDTight": 7,
    }