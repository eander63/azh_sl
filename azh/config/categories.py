"""
Definition of categories.

Three orthogonal axes are combined:

    multiplicity:  2l = 100,  3l = 200
    flavor:        2e =  10,  2mu = 20
    region:        wz_cr = 4000,  sr_1b = 5000,  sr_2b = 6000

Combined-category IDs are the sum of their parts (tens/hundreds/thousands never
collide):

    2l__2e          = 110      (Z-peak validation, ee)
    3l__2mu         = 220      (analysis preselection, mumu Z)
    3l__wz_cr       = 4200     (flavor-inclusive WZ CR)
    3l__2e__sr_2b   = 6210     (analysis leaf)

    standalone:  cat_incl = 1

Regions are meaningful only for the 3-lepton analysis. Rather than build a
single multiplicity x flavor x region product and prune the 2l/bare-flavor
region combinations with skip_fn, we build THREE scoped 2-group products:

    (1) multiplicity x flavor
    (2) 3l x region                 (flavor-inclusive analysis regions)
    (3) (3l__flavor) x region       (analysis leaves)

Why not skip_fn: columnflow's create_category_combinations finds a leaf's
direct parents as *all* (n-1)-group sub-combinations and looks each up with
get_category() -- WITHOUT consulting skip_fn (see config_util.py). So skipping a
middle-layer node (e.g. 2e__wz_cr) removes a required parent of 3l__2e__wz_cr
and raises "unknown category". Building only valid 2-group products means every
parent exists by construction, and no region is ever paired with 2l.

The two modes:

  * VALIDATION -- ``2l__*`` categories do NOT include ``catid_baseline`` (no MET
    or jet cut). High-statistics DY sample for Z-peak / lepton-calibration.
  * ANALYSIS -- ``3l__*__<region>`` include ``catid_baseline`` via the region
    categorizers: the full B2G-24-002 selection.
"""

import law
import order as od
from columnflow.config_util import create_category_combinations
from columnflow.util import maybe_import

from azh.util import call_once_on_config

logger = law.logger.get_logger(__name__)

np = maybe_import("numpy")
ak = maybe_import("awkward")


def name_fn(categories: dict[str, od.Category]):
    """Join category names with '__' (parents already carry combined names)."""
    return "__".join(cat.name for cat in categories.values() if cat)


def kwargs_fn(categories: dict[str, od.Category]):
    """
    Build id / selection / label for a combined category.

    Selections are FLATTENED: a parent that is itself combined (e.g. 3l__2e)
    already carries a *list* selection, so we extend rather than nest -- columnflow
    ANDs a flat list of categorizer names, and a nested list would break it.
    """
    present = [cat for cat in categories.values() if cat]

    selection = []
    for cat in present:
        sel = cat.selection
        if isinstance(sel, (list, tuple)):
            selection.extend(sel)
        else:
            selection.append(sel)

    return {
        "id": sum(cat.id for cat in present),
        "selection": selection,
        "label": "\n".join(cat.label for cat in present if cat.label),
    }


# ---------------------------------------------------------------------
# Base categories (single-axis)
# ---------------------------------------------------------------------


@call_once_on_config()
def add_incl_cat(config: od.Config) -> None:
    config.add_category(
        name="cat_incl", id=1, selection="catid_incl", label="Inclusive"
    )


@call_once_on_config()
def add_lepton_categories(config: od.Config) -> None:
    """Flavor of the Z candidate (not the total lepton count)."""
    config.add_category(
        name="2e", id=10, selection="catid_selection_2e", label="Z → ee"
    )
    config.add_category(
        name="2mu", id=20, selection="catid_selection_2mu", label="Z → μμ"
    )


@call_once_on_config()
def add_multiplicity_categories(config: od.Config) -> None:
    """Total tight-lepton multiplicity: the validation/analysis switch."""
    config.add_category(name="2l", id=100, selection="catid_2l", label="2 leptons")
    config.add_category(name="3l", id=200, selection="catid_3l", label="3 leptons")


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
    Categories depending on produced columns. Rebinds the flavor categories to
    their PRODUCTION categorizers (which read produced columns) before the
    combinations are built.
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
    Build the analysis category lattice as three scoped 2-group products
    (see module docstring for why not a single 3-group product + skip_fn).
    """
    add_lepton_categories(config)
    add_multiplicity_categories(config)

    config.add_category(
        name="wz_cr", id=4000, selection="catid_wz_cr", label="WZ CR (0b)"
    )
    config.add_category(name="sr_1b", id=5000, selection="catid_sr_1b", label="1b SR")
    config.add_category(
        name="sr_2b", id=6000, selection="catid_sr_2b", label=r"$\geq$2b SR"
    )

    common = {"name_fn": name_fn, "kwargs_fn": kwargs_fn, "skip_existing": True}

    # (1) multiplicity x flavor  ->  2l__2e, 2l__2mu, 3l__2e, 3l__2mu
    create_category_combinations(
        config,
        {
            "multiplicity": [config.get_category(n) for n in ["2l", "3l"]],
            "flavor": [config.get_category(n) for n in ["2e", "2mu"]],
        },
        **common,
    )

    # (2) 3l x region  ->  3l__wz_cr, 3l__sr_1b, 3l__sr_2b  (flavor-inclusive)
    create_category_combinations(
        config,
        {
            "mult": [config.get_category("3l")],
            "region": [config.get_category(n) for n in ["wz_cr", "sr_1b", "sr_2b"]],
        },
        **common,
    )

    # (3) (3l__flavor) x region  ->  3l__2e__wz_cr, ... , 3l__2mu__sr_2b
    #     parents (3l__2e etc.) were created by call (1); regions are singles.
    create_category_combinations(
        config,
        {
            "mult_flavor": [config.get_category(n) for n in ["3l__2e", "3l__2mu"]],
            "region": [config.get_category(n) for n in ["wz_cr", "sr_1b", "sr_2b"]],
        },
        **common,
    )
