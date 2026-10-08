"""
Selection-level lepton momentum shifts (e_scale, e_smear, mu_scale, mu_resol).

These shifts change which leptons pass the pT floor, so they are applied right
before the lepton selection, by overwriting Electron.pt / Muon.pt with the varied
column written by calibration (calibration/corrections.py). They are NOT done
with column aliases: with an alias on a collection column, ReduceEvents wrote
the full, unfiltered Electron collection (every NanoAOD field, every electron)
for the shifted pass, and production then read electrons that were never
selected (pT down to 4.7 GeV, misaligned with the selection masks).
"""

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from columnflow.util import maybe_import

ak = maybe_import("awkward")

# shift source -> (collection, variation name of the calibration column)
LEPTON_SHIFTS = {
    "e_scale": ("Electron", "scale"),
    "e_smear": ("Electron", "smear"),
    "mu_scale": ("Muon", "scale"),
    "mu_resol": ("Muon", "resol"),
}


@producer(
    uses={"Electron.pt", "Muon.pt"} | {
        f"{coll}.pt_{var}_{d}" for coll, var in LEPTON_SHIFTS.values() for d in ("up", "down")
    },
    produces={"Electron.pt", "Muon.pt"},
)
def lepton_momentum_shift(self: Producer, events: ak.Array, task=None, **kwargs) -> ak.Array:
    """Replace the lepton pT by its varied version when the task runs a lepton shift (MC only)."""
    shift = getattr(task, "local_shift_inst", None)
    if shift is None or shift.is_nominal or shift.source not in LEPTON_SHIFTS:
        return events
    coll, var = LEPTON_SHIFTS[shift.source]
    return set_ak_column(events, f"{coll}.pt", events[coll][f"pt_{var}_{shift.direction}"])
