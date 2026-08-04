"""
Trigger selection methods.
"""

from columnflow.selection import Selector, SelectionResult, selector
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column, optional_column as opt

np = maybe_import("numpy")
ak = maybe_import("awkward")


# trigger tags that define the primary-dataset groups used for overlap removal
MU_TAGS = {"single_mu", "di_mu"}
E_TAGS = {"single_e", "di_e"}


@selector(
    uses={
        "run",
        # nano columns
        "TrigObj.id", "TrigObj.pt", "TrigObj.eta", "TrigObj.phi", "TrigObj.filterBits",
    },
    produces={
        # new columns
        "trigger_ids",
    },
    exposed=True,
)
def trigger_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> tuple[ak.Array, SelectionResult]:
    """
    HLT trigger path selection with primary-dataset overlap removal.

    For data, an event can be written to more than one primary dataset (Muon,
    EGamma, MuonEG). Summing the PDs without a veto double-counts any event that
    fires both a muon and an electron trigger -- overwhelmingly mixed-flavour
    3-lepton events. We remove the overlap with a fixed PD priority:

        Muon PD   : keep if a muon trigger fired
        EGamma PD : keep if an electron trigger fired AND no muon trigger fired
        MuonEG PD : dropped (no cross-triggers are defined, so it carries no
                    unique acceptance; every muoneg event also fires a single/di
                    lepton path already covered by Muon/EGamma)

    MC is unchanged: it keeps the union (muon OR electron), i.e. exactly the set
    that the two data PDs now partition once each.
    """
    any_fired = False
    trigger_data = []
    trigger_ids = []

    # per-event OR of the muon-group and electron-group trigger decisions,
    # evaluated for *all* such triggers regardless of which PD we are running on,
    # so the EGamma-PD veto (~fired_mu) is computable. Start as scalar False and
    # broadcast up to an array on the first real decision.
    fired_mu = False
    fired_e = False

    # index of TrigObj's to repeatedly convert masks to indices
    index = ak.local_index(events.TrigObj)

    for trigger in self.config_inst.x.triggers:
        applies = trigger.applies_to_dataset(self.dataset_inst)
        # for data we still need the decision of non-applying triggers (e.g. muon
        # paths on the EGamma PD) to build the overlap veto; for MC every trigger
        # applies anyway.
        if not applies and self.dataset_inst.is_mc:
            continue

        # get bare decisions
        fired = events.HLT[trigger.hlt_field] == 1
        if trigger.run_range:
            fired = fired & (
                ((trigger.run_range[0] is None) | (trigger.run_range[0] <= events.run)) &
                ((trigger.run_range[1] is None) | (trigger.run_range[1] >= events.run))
            )

        # get trigger objects for fired events per leg
        leg_masks = []
        all_legs_match = True
        for leg in trigger.legs:
            # start with a True mask
            leg_mask = abs(events.TrigObj.id) >= 0
            # pdg id selection
            if leg.pdg_id is not None:
                leg_mask = leg_mask & (abs(events.TrigObj.id) == leg.pdg_id)
            # pt cut
            if leg.min_pt is not None:
                leg_mask = leg_mask & (events.TrigObj.pt >= leg.min_pt)
            # trigger bits match
            if leg.trigger_bits is not None:
                # OR across bits themselves, AND between all decision in the list
                for bits in leg.trigger_bits:
                    leg_mask = leg_mask & ((events.TrigObj.filterBits & bits) > 0)
            leg_masks.append(index[leg_mask])
            # at least one object must match this leg
            all_legs_match = all_legs_match & ak.any(leg_mask, axis=1)

        # final trigger decision (leg-matched)
        fired_and_all_legs_match = fired & all_legs_match

        # accumulate the PD-group decisions for overlap removal
        if trigger.tags & MU_TAGS:
            fired_mu = fired_mu | fired_and_all_legs_match
        if trigger.tags & E_TAGS:
            fired_e = fired_e | fired_and_all_legs_match

        # leg-matching bookkeeping and trigger ids only for triggers that actually
        # apply to this dataset (keeps downstream trigger-SF inputs unchanged)
        if applies:
            any_fired = any_fired | fired_and_all_legs_match
            trigger_data.append((trigger, fired_and_all_legs_match, leg_masks))
            ids = ak.where(fired_and_all_legs_match, np.float32(trigger.id), np.float32(np.nan))
            trigger_ids.append(ak.singletons(ak.nan_to_none(ids)))

    # store the fired trigger ids
    trigger_ids = ak.concatenate(trigger_ids, axis=1)
    events = set_ak_column(events, "trigger_ids", trigger_ids, value_type=np.int32)

    # make sure the group decisions are arrays even if a group had no triggers
    if not isinstance(fired_mu, ak.Array):
        fired_mu = ak.zeros_like(events.run, dtype=bool)
    if not isinstance(fired_e, ak.Array):
        fired_e = ak.zeros_like(events.run, dtype=bool)

    # ── build the trigger selection step with PD-priority overlap removal ──
    if self.dataset_inst.is_mc:
        trigger_step = fired_mu | fired_e
    else:
        has_mu = self.dataset_inst.has_tag("mu")
        has_egamma = self.dataset_inst.has_tag("egamma")
        if has_mu and not has_egamma:            # Muon PD
            trigger_step = fired_mu
        elif has_egamma and not has_mu:          # EGamma PD
            trigger_step = fired_e & ~fired_mu
        else:                                    # MuonEG / both-tagged -> drop
            trigger_step = ak.zeros_like(events.run, dtype=bool)

    trigger_step = ak.fill_none(trigger_step, False)

    return events, SelectionResult(
        steps={
            "trigger": trigger_step,
        },
        aux={
            "trigger_data": trigger_data,
        },
    )


@trigger_selection.init
def trigger_selection_init(self: Selector) -> None:
    if getattr(self, "dataset_inst", None) is None:
        return

    # load HLT columns for all triggers that apply; for DATA also load the
    # remaining trigger paths so the muon/electron overlap veto is computable on
    # every primary dataset (the HLT branches exist in NanoAOD regardless of PD).
    self.uses |= {
        opt(trigger.name)
        for trigger in self.config_inst.x.triggers
        if trigger.applies_to_dataset(self.dataset_inst) or self.dataset_inst.is_data
    }
