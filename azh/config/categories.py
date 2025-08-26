# coding: utf-8

"""
Definition of categories.

Categories are assigned a unique integer ID according to a fixed numbering
scheme, with digits/groups of digits indicating the different category groups:

"""

import law

from columnflow.util import maybe_import
# from columnflow.categorization import Categorizer, categorizer
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
        "label": "\n".join(
            cat.label for cat in categories.values()
        ),
    }


def skip_fn(categories: dict[str, od.Category]):
    """Custom function for skipping certain category combinations."""
    return False  # don't skip


@call_once_on_config()
def add_categories_selection(config: od.Config) -> None:
    add_lepton_categories(config)
    add_incl_cat(config)
    # add_categories_bjets(config)

# def add_categories(config: od.Config) -> None:
#     @categorizer(uses={"event"})
#     def cat_incl(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
#         # fully inclusive selection
#         return events, ak.ones_like(events.event) == 1

    # @categorizer(uses={"Jet.pt"})
    # def cat_2j(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    #     # two or more jets
    #     return events, ak.num(events.Jet.pt, axis=1) >= 2


@call_once_on_config()
def add_incl_cat(config: od.Config) -> None:

    cat_incl = config.add_category(  # noqa
        name="cat_incl",
        id=1,
        selection="catid_incl",
        label="Inclusive",
    )


@call_once_on_config()
def add_lepton_categories(config: od.Config) -> None:

    cat_2e = config.add_category(  # noqa
        name="2e",
        id=10,
        selection="catid_selection_2e",
        label="2 Electron",
    )

    cat_2mu = config.add_category(  # noqa
        name="2mu",
        id=20,
        selection="catid_selection_2mu",
        label="2 Muon",
    )


@call_once_on_config()
def add_categories_production(config: od.Config) -> None:
    """
    Adds categories to a *config*, that are typically produced in `ProduceColumns`.
    """

    #
    # switch existing categories to different production module
    #

    cat_2e = config.get_category("2e")
    cat_2e.selection = "catid_2e"

    cat_2mu = config.get_category("2mu")
    cat_2mu.selection = "catid_2mu"


@call_once_on_config()
def add_categories_mz(config: od.Config) -> None:
    """
    Adds categories to a *config*, that are typically produced in `ProduceColumns`.
    """

    #
    # switch existing categories to different production module
    #
    cat_SR = config.add_category(  # noqa
        name="SR",
        id=100,
        selection="catid_SR",
        label="In Z window",
    )

    cat_CR= config.add_category(  # noqa
        name="CR",
        id=200,
        selection="catid_CR",
        label="m(ll) sidebands",
    )


@call_once_on_config()
def add_categories_bjets(config: od.Config) -> None:
    """
    Adds categories to a *config*, that are typically produced in `ProduceColumns`.
    """

    #
    # switch existing categories to different production module
    #
    cat_SR = config.add_category(  # noqa
        name="2bjets",
        id=3000,
        selection="catid_2bjets",
        label=">=2 B-Jets",
    )

    cat_CR= config.add_category(  # noqa
        name="1bjets",
        id=2000,
        selection="catid_1bjets",
        label="1 B-Jets",
    )

    cat_CR= config.add_category(  # noqa
        name="0bjets",
        id=1000,
        selection="catid_0bjets",
        label="0 B-Jets",
    )


@call_once_on_config()
def add_categories_njets(config: od.Config) -> None:
    """
    Adds categories to a *config*, that are typically produced in `ProduceColumns`.
    """

    #
    # switch existing categories to different production module
    #

    cat_SR = config.add_category(  # noqa
        name="4jets",
        id=30000,
        selection="catid_4jets",
        label="4 Jets",
    )

    cat_SR = config.add_category(  # noqa
        name="5jets",
        id=10000,
        selection="catid_5jets",
        label="5 Jets",
    )

    cat_CR= config.add_category(  # noqa
        name="6jets",
        id=20000,
        selection="catid_6jets",
        label="6 or more Jets",
    )
    print("NJets")
    category_groups = {
        "lepton": [
            config.get_category(name)
            for name in ["2e", "2mu"]
        ],
        "z_mass": [
            config.get_category(name)
            for name in ["SR", "CR"]
        ],
        "b_jets": [
            config.get_category(name)
            for name in ["2bjets", "1bjets", "0bjets"]
        ],
        "jets": [
            config.get_category(name)
            for name in ["5jets", "6jets","4jets"]
        ],
    }
    create_category_combinations(config, category_groups, name_fn, kwargs_fn)

# category_groups = {
#     "lepton": [
#         config.get_category(name)
#         for name in ["2e", "2mu"]
#     ],
#     "mz": [
#         config.get_category(name)
#         for name in ["SR", "CR"]
#     ]
# }
