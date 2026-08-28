"""
Pileup weight from the LUM correctionlib file (puWeights.json).

Replaces the profile-histogram pileup method. Reads the ``pu_sf`` external file
declared in ``cfg.x.external_files``, evaluates the true pileup per event, and
writes the ``pu_weight`` column. MC only -- data has no true pileup.

Structure mirrors the muon/electron calibrators: a main producer plus a
``requires`` (ask columnflow to bundle the external file) and a ``setup``
(open the JSON once and hand it to correctionlib).
"""

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from columnflow.util import InsertableDict, maybe_import

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    uses={"Pileup.nTrueInt"},
    produces={"pu_weight", "pu_weight_up", "pu_weight_down"},
    mc_only=True,
)
def pu_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Evaluate the LUM pileup weight for every event and store it as ``pu_weight``,
    together with the ``up``/``down`` variations obtained by shifting the
    minimum-bias cross section (AN-2022/158 Sec. 9.1: +-4.6% around 69.2 mb).
    The same puWeights.json carries all three, so this costs two extra
    correctionlib evaluations and no additional external file.
    """
    ntrue = ak.to_numpy(events.Pileup.nTrueInt).astype(np.float64)
    for postfix, syst in [("", "nominal"), ("_up", "up"), ("_down", "down")]:
        w = self.pu_corrector.evaluate(ntrue, syst)
        events = set_ak_column(
            events, f"pu_weight{postfix}", np.asarray(w, dtype=np.float32),
        )
    return events


@pu_weight.requires
def pu_weight_requires(self: Producer, reqs: dict) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles

    reqs["external_files"] = BundleExternalFiles.req(self.task)


@pu_weight.setup
def pu_weight_setup(
    self: Producer,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
) -> None:
    import correctionlib

    bundle = reqs["external_files"]
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.pu_sf.load(formatter="gzip").decode("utf-8"),
    )
    # Each era's puWeights.json contains exactly one correction (named after the
    # data-taking run range, e.g. "Collisions2022_355100_357900_eraBCD_...").
    # Grab it by the configured name if set, otherwise fall back to the sole key.
    name = self.config_inst.x("pu_correction_name", None)
    if name is None:
        keys = list(cset.keys())
        if len(keys) != 1:
            raise ValueError(
                f"expected exactly one correction in pu_sf, found {keys}; "
                "set cfg.x.pu_correction_name explicitly per config",
            )
        name = keys[0]
    self.pu_corrector = cset[name]


# ---------------------------------------------------------------------------
# NOTE: the up/down columns above are the *raw* pileup weights. What enters the
# event weight is 'normalized_pu_weight{,_up,_down}', produced by the
# normalized_weight_factory wrapper in azh/production/weights.py, which divides
# out the per-process sum so that a pileup variation changes the shape but not
# the total yield. That wrapper only picks up a variation if the matching
# 'sum_mc_weight_<col>_per_process' entry was booked in azh/selection/default.py.
# ---------------------------------------------------------------------------
