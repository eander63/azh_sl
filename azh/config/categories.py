# coding: utf-8

"""
Definition of categories.

Category IDs follow a fixed additive scheme so that combined categories get a
unique ID from the sum of their parts:

    flavor:  2e = 10,  2mu = 20
    region:  wz_cr = 4000,  sr_1b = 5000,  sr_2b = 6000

    -> combined leaves:  2e__wz_cr = 4010,  2mu__sr_2b = 6020,  etc.

    other standalone:  cat_incl = 1
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
    """Customization function for automatically generated combined categories."""
    return {
        "id": sum(cat.id for cat in categories.values()),
        "selection": [cat.selection for cat in categories.values()],
        "label": "\n".join(cat.label for cat in categories.values()),
    }


def skip_fn(categories: dict[str, od.Category]):
    """Custom function for skipping certain category combinations."""
    return False  # don't skip

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
    config.add_category(
        name="2e",
        id=10,
        selection="catid_selection_2e",
        label="2 Electron",
    )
    config.add_category(
        name="2mu",
        id=20,
        selection="catid_selection_2mu",
        label="2 Muon",
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
    Categories that depend on produced columns (m_z, pt_z, n_tight_leptons, ...).

    Rebinds the lepton categories to their PRODUCTION categorizers before the
    region combination is built, so the combined leaves freeze catid_2e/2mu
    (which read produced columns) rather than the selection-time
    catid_selection_2e/2mu.
    """
    add_lepton_categories(config)
    add_incl_cat(config)

    config.get_category("2e").selection = "catid_2e"
    config.get_category("2mu").selection = "catid_2mu"

    add_categories_regions(config)

@call_once_on_config()
def add_categories_regions(config: od.Config) -> None:
    """
    Analysis regions from the B2G-24-002 SR/CR table, split by lepton flavor.

        2e__wz_cr,  2mu__wz_cr    (0 b-jets,   data + MC)
        2e__sr_1b,  2mu__sr_1b    (1 b-jet,    MC only — blinded)
        2e__sr_2b,  2mu__sr_2b    (>=2 b-jets, MC only — blinded)

    Blinding lives in the categorizers (catid_sr_1b / catid_sr_2b), not here:
    data events fall out of the SRs structurally.
    """
    add_lepton_categories(config)

    config.add_category(name="wz_cr", id=4000, selection="catid_wz_cr", label="WZ CR (0b)")
    config.add_category(name="sr_1b", id=5000, selection="catid_sr_1b", label="1b SR")
    config.add_category(name="sr_2b", id=6000, selection="catid_sr_2b", label=r"$\geq$2b SR")

    category_groups = {
        "lepton": [config.get_category(n) for n in ["2e", "2mu"]],
        "region": [config.get_category(n) for n in ["wz_cr", "sr_1b", "sr_2b"]],
    }
    create_category_combinations(
        config,
        category_groups,
        name_fn=name_fn,
        kwargs_fn=kwargs_fn,
        skip_existing=False,
    )


