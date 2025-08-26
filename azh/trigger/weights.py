# coding: utf-8
"""
custom weight producer to apply trigger masks in histogram step
"""

import law

from columnflow.util import maybe_import, InsertableDict
from columnflow.weight import WeightProducer, weight_producer
from columnflow.config_util import get_shifts_from_sources
from columnflow.columnar_util import Route
from columnflow.weight.all_weights import all_weights

np = maybe_import("numpy")
ak = maybe_import("awkward")

logger = law.logger.get_logger(__name__)

@weight_producer(
    mc_only=False,
    uses={all_weights},
    mask_fn=None,
    mask_columns=None,
)
def base(self: WeightProducer, events: ak.Array, **kwargs) -> ak.Array:
    """
    WeightProducer that applies the trigger masks to the events.
    """
    if self.mask_fn:
        events = events[self.mask_fn(events)]

    if self.dataset_inst.is_data:
        return events, ak.Array(np.ones(len(events), dtype=np.float32))

    events, weights = self[all_weights](events, **kwargs)

    return events, weights

@base.init
def base_init(self: WeightProducer) -> None:
    
    if not getattr(self, "config_inst"):
        return
    
    if self.mask_columns:
        for col in self.mask_columns:
            self.uses.add(col)


ref_trigger = base.derive("ref_trigger", cls_dict={
    "mask_fn": lambda self, events: events.HLT.PFMETNoMu120_PFMHTNoMu120_IDTight,
    "mask_columns": ["HLT.PFMETNoMu120_PFMHTNoMu120_IDTight"],
})