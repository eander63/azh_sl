# coding: utf-8

"""
Fixed working point b-tag scale factor weights with split light/heavy correction sets.

WHY THIS FILE EXISTS
--------------------
columnflow's :py:obj:`~columnflow.production.cms.btag.btag_wp_weights` implements the
BTV fixed-WP method correctly, but ``BTagWPSFConfig.correction_set`` is a single
string and the docstring points at a merged file (``UParTAK4_merged``). BTV ships
no merged set for any of the five Run 3 eras this analysis uses -- every
``btagging.json.gz`` from ``Run3-22CDSep23`` through ``Run3-24CDEReprocessing``
provides ``*_comb`` (b and c jets) and ``*_light`` (udsg jets) separately, verified
by ``tests/validate_configs.py``.

So this module keeps everything upstream does -- MC efficiency maps from the
tagging-count histogram, the per-WP scale factor algebra, the systematic
variations -- and replaces only the corrector lookup with a thin wrapper that
dispatches on jet flavour.

This supersedes the old fork-local ``split_btag_weights``, which was layered on
the *shape* method producer and had three defects worth recording:

  * a b-tag threshold of 0.3040 hardcoded in ``SplitCorrector.__call__`` with a
    ``TODO: move this to config``, while the analysis selects on
    ``cfg.x.btag_default.wp`` -- 0.245 / 0.2605 / 0.1917 / 0.1919 / 0.1272
    depending on era. The scale factors were therefore computed at a working
    point the selection never used, in every era.
  * tagging efficiencies read from a hardcoded absolute path in another user's
    scratch directory, binned in pT only, with no era dependence.
  * ``btag_uncs = {}``, so no systematic variations were ever produced, which is
    why ``cfg.x.event_weights["btag_weight"]`` is an empty list.

All three are fixed here by construction: the WPs come from the config, the
efficiencies are measured from this analysis' own selected jets per era, and the
variations come from :py:attr:`SplitBTagWPSFConfig.systs`.
"""

from __future__ import annotations

import dataclasses

import law

from columnflow.production import Producer
from columnflow.production.cms.btag import btag_wp_weights, BTagWPSFConfig
from columnflow.util import maybe_import, load_correction_set
from columnflow.types import Any

np = maybe_import("numpy")
ak = maybe_import("awkward")

logger = law.logger.get_logger(__name__)


# Systematic names supported by the BTV ``*_light`` correction sets.
#
# Verified identical across all five eras by tests/validate_configs.py. The
# ``*_comb`` sets carry many more (jes, jer, pileup, hdamp, topmass, type3,
# statistic, and era-dependent extras), which is the asymmetry AN-2022/158
# Table 22 reflects by separating CMS_btag_light_[year] from the correlated
# CMS_btag_bc_* nuisances.
LIGHT_SYSTEMATICS = frozenset({
    "central",
    "up", "down",
    "up_correlated", "down_correlated",
    "up_uncorrelated", "down_uncorrelated",
})


@dataclasses.dataclass
class SplitBTagWPSFConfig(BTagWPSFConfig):
    """
    :py:class:`BTagWPSFConfig` plus the name of the light-flavour correction set.

    ``correction_set`` (inherited) holds the **heavy** flavour set, so that the
    upstream setup function -- which we call via ``super()`` -- loads something
    valid before we wrap it.
    """

    # name of the udsg correction set, e.g. "particleNet_light" or "UParTAK4_light"
    correction_set_light: str = ""

    # systematics the light set understands; anything else falls back to
    # "central" for udsg jets (see SplitBTagWPCorrector.__call__)
    light_systematics: frozenset[str] = LIGHT_SYSTEMATICS

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.correction_set_light:
            raise ValueError(
                "SplitBTagWPSFConfig requires 'correction_set_light'; BTV provides no "
                "merged correction set for Run 3, so the udsg set must be named "
                "explicitly (e.g. 'particleNet_light')",
            )


class SplitBTagWPCorrector(object):
    """
    Presents two correctionlib correctors as one.

    ``btag_wp_weights`` calls its corrector as::

        self.btag_wp_sf_corrector(*(variable_map[inp.name] for inp in
                                    self.btag_wp_sf_corrector.inputs))

    so anything exposing ``inputs`` and ``__call__`` slots in. That is the same
    seam the old fork-local producer used; the difference is that everything
    around it is now upstream's tested fixed-WP implementation rather than a
    hand-rolled one.
    """

    def __init__(self, corrector_heavy, corrector_light, light_systematics):
        self.corrector_heavy = corrector_heavy
        self.corrector_light = corrector_light
        self.light_systematics = light_systematics

        # Both BTV sets declare the same input schema
        # (systematic, working_point, flavor, abseta, pt), so the heavy one can
        # speak for both. Verify rather than assume -- a schema change would
        # otherwise silently scramble the positional arguments.
        heavy_names = [inp.name for inp in corrector_heavy.inputs]
        light_names = [inp.name for inp in corrector_light.inputs]
        if heavy_names != light_names:
            raise ValueError(
                f"heavy and light b-tag correctors declare different inputs: "
                f"{heavy_names} vs {light_names}; the split corrector assumes they match",
            )
        self._inputs = corrector_heavy.inputs

        self.flavor_index = heavy_names.index("flavor")
        self.systematic_index = heavy_names.index("systematic")

    @property
    def inputs(self):
        return self._inputs

    def __call__(self, *args):
        flavor = args[self.flavor_index]
        systematic = args[self.systematic_index]

        # udsg is hadronFlavour 0; b and c are 5 and 4.
        light_mask = flavor == 0

        # Evaluate BOTH correctors over the FULL array and select afterwards,
        # rather than masking the inputs and stitching results back together.
        # The arrays here are jagged (upstream does ak.prod(..., axis=1) on the
        # result), so subset-and-reassemble would have to rebuild the layout by
        # hand -- easy to get subtly wrong, and the old producer did exactly
        # that. Evaluating twice costs a little CPU and no correctness.
        #
        # Each corrector only accepts its own flavour categories, so the flavor
        # argument is substituted before the call: heavy jets are presented to
        # the light corrector as flavour 0 and vice versa. Those values are then
        # discarded by the ak.where below.
        light_args = list(args)
        light_args[self.flavor_index] = ak.zeros_like(flavor)

        # The light sets carry only correlated/uncorrelated variations. For a
        # heavy-flavour systematic (jes, hdamp, topmass, ...) the physically
        # correct behaviour is for udsg jets not to move at all, so fall back to
        # the central value rather than raising.
        if systematic not in self.light_systematics:
            light_args[self.systematic_index] = "central"

        heavy_args = list(args)
        heavy_args[self.flavor_index] = ak.full_like(flavor, 5)

        sf_light = self.corrector_light(*light_args)
        sf_heavy = self.corrector_heavy(*heavy_args)

        return ak.where(light_mask, sf_light, sf_heavy)


# Derived producer. Only the corrector construction differs from upstream; the
# efficiency map, WP algebra, systematics loop and column declarations are all
# inherited.
split_btag_wp_weights = btag_wp_weights.derive(
    "split_btag_wp_weights",
    cls_dict={
        # this analysis stores the BTV file under "btag_sf_corr", not the
        # "btag_wp_sf_corr" upstream expects
        "get_btag_wp_file": (lambda self, external_files: external_files.btag_sf_corr),
        "get_btag_wp_sf_config": (lambda self: self.config_inst.x.btag_wp_sf_config),
    },
)


@split_btag_wp_weights.setup
def split_btag_wp_weights_setup(
    self: Producer,
    task: law.Task,
    reqs: dict[str, Any],
    inputs: dict[str, Any],
    reader_targets: law.util.InsertableDict,
    **kwargs,
) -> None:
    # Run upstream's setup first: it loads the heavy corrector, sums the tagging
    # count histograms over the dataset group, builds the efficiency map and
    # converts it to an evaluator, and fills convert_wp_str / sorted_wps.
    super(split_btag_wp_weights, self).setup_func(
        task=task,
        reqs=reqs,
        inputs=inputs,
        reader_targets=reader_targets,
        **kwargs,
    )

    # Now wrap the single corrector it built together with the light one.
    btag_file = self.get_btag_wp_file(reqs["external_files"].files)
    correction_set = load_correction_set(btag_file)

    self.btag_wp_sf_corrector = SplitBTagWPCorrector(
        corrector_heavy=self.btag_wp_sf_corrector,
        corrector_light=correction_set[self.cfg.correction_set_light],
        light_systematics=self.cfg.light_systematics,
    )

    logger.debug_once(
        f"split_btag_wp_weights_{self.config_inst.name}",
        f"split b-tag corrector: heavy='{self.cfg.correction_set}', "
        f"light='{self.cfg.correction_set_light}'",
    )
