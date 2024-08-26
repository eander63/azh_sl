# coding: utf-8

"""
Selection methods defining categories based on selection step results.
"""

from __future__ import annotations

import law

from columnflow.util import maybe_import
from columnflow.categorization import Categorizer, categorizer
from columnflow.selection import SelectionResult
from columnflow.columnar_util import has_ak_column, optional_column

np = maybe_import("numpy")
ak = maybe_import("awkward")

z_mass = 91.188
mass_window = 5
# print("Zmass_cat")

@categorizer(uses={"event"}, call_force=True)
def catid_SR(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    # print("Hi")
    # print(events.m_z)
    # print((events.m_z >=  np.full_like(events.m_z, z_mass - mass_window) ) & (events.m_z <= np.full_like(events.m_z, z_mass + mass_window)))
    mask = ( events.m_z >=  np.full_like(events.m_z, z_mass - mass_window))  & (events.m_z <= np.full_like(events.m_z, z_mass + mass_window))
    # print("SR: ",mask)
    return events, mask

@categorizer(uses={"event"}, call_force=True)
def catid_CR(
    self: Categorizer, events: ak.Array, **kwargs,
) -> tuple[ak.Array, ak.Array]:
    mask = ( events.m_z <  np.full_like(events.m_z, z_mass - mass_window)) | ( events.m_z >  np.full_like(events.m_z, z_mass + mass_window))
    # print("CR: ",mask)
    return events, mask

@categorizer(uses={"BJet"}, call_force=True)
def catid_2bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = (ak.num(events.BJet, axis=-1) >= 2)
    return events, mask

@categorizer(uses={"BJet"}, call_force=True)
def catid_1bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = (ak.num(events.BJet, axis=-1) == 1)
    return events, mask

@categorizer(uses={"BJet"}, call_force=True)
def catid_0bjets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = (ak.num(events.BJet, axis=-1) == 0)
    return events, mask

@categorizer(uses={"Jet"}, call_force=True)
def catid_6jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = (ak.num(events.Jet, axis=-1) >= 6)
    return events, mask

@categorizer(uses={"Jet"}, call_force=True)
def catid_5jets(self: Categorizer, events: ak.Array, **kwargs) -> tuple[ak.Array, ak.Array]:
    mask = (ak.num(events.Jet, axis=-1) == 5)
    return events, mask