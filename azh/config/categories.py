# coding: utf-8

"""
Definition of categories.

Three orthogonal axes are combined:

    multiplicity:  2l = 100,  3l = 200
    flavor:        2e =  10,  2mu = 20
    region:        wz_cr = 4000,  sr_1b = 5000,  sr_2b = 6000

Category IDs follow a fixed additive scheme so a combined category's ID is the
sum of its parts (tens / hundreds / thousands never collide):

    2l__2e          = 110      (Z-peak validation, ee)
    3l__2mu         = 220      (analysis preselection, mumu Z)
    3l__wz_cr       = 4200     (flavor-inclusive WZ CR)
    3l__2e__sr_2b   = 6210     (analysis leaf)

    standalone:  cat_incl = 1

The two modes:

  * VALIDATION -- 2l__* categories do NOT include catid_baseline, so no
    MET or jet-multiplicity requirement is applied. This is the high-statistics
    DY sample used for Z-peak / lepton-calibration checks.
  * ANALYSIS -- 3l__*__<region> categories DO include catid_baseline
    (via the region categorizers), giving the full B2G-24-002 selection.

Regions are only meaningful for the 3-lepton analysis; skip_fn drops any
combination pairing a region with 2l or with no multiplicity at all.
"""

import law

from columnflow.util import maybe_import
from columnflow.config_util import create_category_combinations
from azh.util import call_once_on_config

import order as od

logger = law.logger.get_logger(__name__)

np = maybe_import("numpy")
ak = maybe_import("awkward")


def name_fn(categories: dict[str, od.Category]):
    """Naming function for automatically generated combined categories."""
    return "__".join(cat.name for cat in categories.values() if cat)


def kwargs_fn(categories: dict[str, od.Category]):
    """
    Customization function for automatically generated combined categories.

    NOTE: with three groups, create_category_combinations also emits
    partial combinations in which a group is absent (``None``). Every
    comprehension below must therefore filter with ``if cat`` -- without it,
    None.id raises as soon as a third axis is added.
    """
    present = [cat for cat in categories.values() if cat]
    return {
        "id": sum(cat.id for cat in present),
        "selection": [cat.selection for cat in present],
        "label": "\n".join(cat.label for cat in present),
    }


def skip_fn(categories: dict[str, od.Category]):
    """
    Skip combinations that are not physically meaningful.

    The SR/CR split is defined by the paper only for the 3-lepton final state,
    so a region is kept only when it is combined with the 3l multiplicity.
    This drops both 2l__<region> and bare <flavor>__<region>.
    """
    multiplicity = categories.get("multiplicity")
    region = categories.get("region")

    if region is not None:
        if multiplicity is None or multiplicity.name != "3l":
            return True  # skip

    return False


# ---------------------------------------------------------------------
# Base categories (single-axis)
# ---------------------------------------------------------------------

@call_once_on_config()
def add_incl_cat(config: od.Config) -> None:
    config.add_category(
        name="cat_incl",
        id=1,
        selection="catid_incl",
        label="Inclusive",
    )


@call_once_on_config()
def add_lepton_categories(config: od.Config) -> None:
    """Flavor of the Z candidate (not the total lepton count)."""
    config.add_category(
        name="2e",
        id=10,
        selection="catid_selection_2e",
        label="Z → ee",
    )
    config.add_category(
        name="2mu",
        id=20,
        selection="catid_selection_2mu",
        label="Z → μμ",
    )


@call_once_on_config()
def add_multiplicity_categories(config: od.Config) -> None:
    """
    Total tight-lepton multiplicity -- the switch between validation and
    analysis mode.
    """
    config.add_category(
        name="2l",
        id=100,
        selection="catid_2l",
        label="2 leptons",
    )
    config.add_category(
        name="3l",
        id=200,
        selection="catid_3l",
        label="3 leptons",
    )


# ---------------------------------------------------------------------
# Selection-time categories (used in SelectEvents)
# ---------------------------------------------------------------------

@call_once_on_config()
def add_categories_selection(config: od.Config) -> None:
    add_lepton_categories(config)
    add_incl_cat(config)


# ---------------------------------------------------------------------
# Production-time categories (used in ProduceColumns)
# ---------------------------------------------------------------------

@call_once_on_config()
def add_categories_production(config: od.Config) -> None:
    """
    Categories that depend on produced columns (m_z, pt_z, n_tight_leptons,
    min_mll, charge_sum, lepN_pt, ...).

    Rebinds the flavor categories to their PRODUCTION categorizers before the
    combinations are built, so the combined leaves freeze catid_2e/catid_2mu
    (which read produced columns) rather than the selection-time
    catid_selection_2e/catid_selection_2mu.
    """
    add_lepton_categories(config)
    add_incl_cat(config)
    add_multiplicity_categories(config)

    config.get_category("2e").selection = "catid_2e"
    config.get_category("2mu").selection = "catid_2mu"

    add_categories_regions(config)


@call_once_on_config()
def add_categories_regions(config: od.Config) -> None:
    """
    Analysis regions from the B2G-24-002 SR/CR table, combined with lepton
    flavor and multiplicity.

    Leaves produced (after skip_fn):

        validation      2l__2e,  2l__2mu
        preselection    3l__2e,  3l__2mu
        flavor-incl.    3l__wz_cr,  3l__sr_1b,  3l__sr_2b
        analysis        3l__2e__wz_cr,  3l__2mu__wz_cr,
                        3l__2e__sr_1b,  3l__2mu__sr_1b,
                        3l__2e__sr_2b,  3l__2mu__sr_2b

    Blinding lives in the categorizers (catid_sr_1b / catid_sr_2b), not here:
    data events fall out of the SRs structurally.
    """
    add_lepton_categories(config)
    add_multiplicity_categories(config)

    config.add_category(name="wz_cr", id=4000, selection="catid_wz_cr", label="WZ CR (0b)")
    config.add_category(name="sr_1b", id=5000, selection="catid_sr_1b", label="1b SR")
    config.add_category(name="sr_2b", id=6000, selection="catid_sr_2b", label=r"$\geq$2b SR")

    category_groups = {
        "multiplicity": [config.get_category(n) for n in ["2l", "3l"]],
        "flavor": [config.get_category(n) for n in ["2e", "2mu"]],
        "region": [config.get_category(n) for n in ["wz_cr", "sr_1b", "sr_2b"]],
    }
    create_category_combinations(
        config,
        category_groups,
        name_fn=name_fn,
        kwargs_fn=kwargs_fn,
        skip_fn=skip_fn,
        skip_existing=False,
    )
