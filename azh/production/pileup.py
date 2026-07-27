# coding: utf-8

"""
Pileup weight from the LUM correctionlib file (puWeights.json).

Replaces the profile-histogram pileup method. Reads the ``pu_sf`` external file
declared in ``cfg.x.external_files``, evaluates the true pileup per event, and
writes the ``pu_weight`` column. MC only -- data has no true pileup.

Structure mirrors the muon/electron calibrators: a main producer plus a
``requires`` (ask columnflow to bundle the external file) and a ``setup``
(open the JSON once and hand it to correctionlib).
"""

from columnflow.production import Producer, producer
from columnflow.util import maybe_import, InsertableDict
from columnflow.columnar_util import set_ak_column

ak = maybe_import("awkward")
np = maybe_import("numpy")


@producer(
    uses={"Pileup.nTrueInt"},
    produces={"pu_weight"},
    mc_only=True,
)
def pu_weight(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Evaluate the LUM pileup weight (nominal) for every event and store it as
    ``pu_weight``.
    """
    ntrue = ak.to_numpy(events.Pileup.nTrueInt).astype(np.float64)
    w = self.pu_corrector.evaluate(ntrue, "nominal")
    events = set_ak_column(events, "pu_weight", np.asarray(w, dtype=np.float32))
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
# NOTE: up/down (minbias_xs) variations are one step away when you wire
# systematics -- the same JSON already carries them:
#
#   w_up   = self.pu_corrector.evaluate(ntrue, "up")
#   w_down = self.pu_corrector.evaluate(ntrue, "down")
#
# add "pu_weight_up"/"pu_weight_down" to `produces` and set the columns.
# ---------------------------------------------------------------------------
