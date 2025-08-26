# coding: utf-8

"""
Producers to load trigger scale factors, wip
"""

from __future__ import annotations

from columnflow.production import Producer, producer
from columnflow.util import maybe_import, InsertableDict
from columnflow.columnar_util import set_ak_column

np = maybe_import("numpy")
ak = maybe_import("awkward")
hist = maybe_import("hist")

# produce trigger columns for debugging
@producer(
    produces={"trig_ids"},
    version=1,
)
def trigger(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Produces column filled for each event with the triggers triggering the event.
    This column can then be used to fill a Histogram where each bin corresponds to a certain trigger.
    """

    trigger_map = self.config_inst.x.trigger_map

    # TODO: check if trigger were fired by unprescaled L1 seed
    trig_ids = ak.Array([[trigger_map["All_Events"]]] * len(events))


    # add individual triggers
    for trigger in self.config_inst.x.triggers:
        trig_passed = ak.where(events.HLT[trigger.hlt_field], [[trigger_map[trigger.name]]], [[]])
        trig_ids = ak.concatenate([trig_ids, trig_passed], axis=1)

    trig_passed = ak.where(events.HLT["PFMET200_BeamHaloCleaned"], [[trigger_map["HLT_PFMET200_BeamHaloCleaned"]]], [[]])
    trig_ids = ak.concatenate([trig_ids, trig_passed], axis=1)

    print(trig_ids)

    events = set_ak_column(events, "trig_ids", trig_ids)

    return events


# initialize the trigger producer, triggers can be set in the trigger config
@trigger.init
def trigger_init(self: Producer) -> None:

    for trigger in self.config_inst.x("triggers", []):
        self.uses.add(f"HLT.{trigger.hlt_field}")

    self.uses.add("HLT.PFMETNoMu120_PFMHTNoMu120_IDTight")
    self.uses.add("HLT.PFMET200_BeamHaloCleaned")
    self.uses.add("HLT.PFHT500_PFMET100_PFMHT100_IDTight")
    self.uses.add("HLT.PFHT700_PFMET85_PFMHT85_IDTight") 
    self.uses.add("HLT.PFHT800_PFMET75_PFMHT75_IDTight")