# coding: utf-8

"""
Selection methods defining categories based on selection step results.
"""

from __future__ import annotations

# import law

from columnflow.util import maybe_import
from columnflow.categorization import Categorizer, categorizer
# from columnflow.selection import SelectionResult
# from columnflow.columnar_util import has_ak_column, optional_column

np = maybe_import("numpy")
ak = maybe_import("awkward")



@categorizer(uses={"event"}, call_force=True)
def catid_incl(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = ak.ones_like(events.event) > 0
    return events, mask


@categorizer(uses={"event"}, call_force=True)
def catid_selection_2e(
    self: Categorizer, events: ak.Array, **kwargs,
) -> tuple[ak.Array, ak.Array]:
    mask = events.cutflow.n_ele_loose >= 2
    # print("ele selections mask", mask)
    return events, mask


@categorizer(uses={"event"}, call_force=True)
def catid_selection_2mu(
    self: Categorizer, events: ak.Array, **kwargs,
) -> tuple[ak.Array, ak.Array]:
    mask = events.cutflow.n_muo_loose >= 2
    # print("muo mask", mask)
    return events, mask


@categorizer(uses={"Electron.pt", "Muon.pt", "cutflow.*"}, call_force=True)
def catid_2e(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    # "Z is an ee pair": >=2 loose electrons with >=1 high-pT leg, matching the
    # loosened baseline. The exact 2-vs-3 lepton count is the separate nlep axis.
    mask = events.cutflow.n_ele_loose >= 2
    return events, mask


@categorizer(uses={"Electron.pt", "Muon.pt", "cutflow.*"}, call_force=True)
def catid_2mu(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    # "Z is a mumu pair": >=2 loose muons with >=1 high-pT leg, matching the
    # loosened baseline. The exact 2-vs-3 lepton count is the separate nlep axis.
    mask = events.cutflow.n_muo_loose >= 2
    return events, mask
