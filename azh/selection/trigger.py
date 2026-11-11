"""
Trigger selection: HLT decision with primary-dataset overlap removal.
"""

from columnflow.columnar_util import optional_column as opt
from columnflow.selection import SelectionResult, Selector, selector
from columnflow.util import maybe_import

np = maybe_import("numpy")
ak = maybe_import("awkward")


@selector(
    uses={"run"},
    exposed=True,
)
def trigger_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> tuple[ak.Array, SelectionResult]:
    """
    Single-lepton trigger OR (cfg.x.triggers) with PD overlap removal.

    The HLT decision is used directly. The previous TrigObj leg matching compared
    trigger objects to nothing offline, so it could only reject events that had
    fired; for the 2022/23 electron paths it rejected all of them (a v12
    filter bit that does not exist) and for the dilepton paths it rejected a
    different fraction in data and MC.

    MC keeps the union (muon OR electron trigger). Data removes the overlap with
    a fixed PD priority, so that summing all data datasets counts each event once:

        Muon / SingleMuon PD : keep if the muon trigger fired
        EGamma PD            : keep if the electron trigger fired AND the muon
                               trigger did not

    (SingleMuon covers 2022C runs 355862-356386, before the Muon PD existed; the
    two never overlap in runs.)
    """
    fired_mu = ak.zeros_like(events.run, dtype=bool)
    fired_e = ak.zeros_like(events.run, dtype=bool)

    for trigger in self.config_inst.x.triggers:
        # for data the decision of every trigger is needed for the overlap veto
        if self.dataset_inst.is_mc and not trigger.applies_to_dataset(self.dataset_inst):
            continue
        fired = events.HLT[trigger.hlt_field] == 1
        if trigger.run_range:
            lo, hi = trigger.run_range
            if lo is not None:
                fired = fired & (events.run >= lo)
            if hi is not None:
                fired = fired & (events.run <= hi)
        if "single_mu" in trigger.tags:
            fired_mu = fired_mu | fired
        if "single_e" in trigger.tags:
            fired_e = fired_e | fired

    if self.dataset_inst.is_mc:
        trigger_step = fired_mu | fired_e
    else:
        has_mu = self.dataset_inst.has_tag("mu")
        has_egamma = self.dataset_inst.has_tag("egamma")
        if has_mu and not has_egamma:
            trigger_step = fired_mu
        elif has_egamma and not has_mu:
            trigger_step = fired_e & ~fired_mu
        else:
            raise ValueError(
                f"data dataset {self.dataset_inst.name} must be tagged either 'mu' or 'egamma'",
            )

    return events, SelectionResult(
        steps={"trigger": ak.fill_none(trigger_step, False)},
    )


@trigger_selection.init
def trigger_selection_init(self: Selector, **kwargs) -> None:
    if getattr(self, "dataset_inst", None) is None:
        return
    # for data also load the paths of the other PD, for the overlap veto
    self.uses |= {
        opt(trigger.name)
        for trigger in self.config_inst.x.triggers
        if trigger.applies_to_dataset(self.dataset_inst) or self.dataset_inst.is_data
    }
