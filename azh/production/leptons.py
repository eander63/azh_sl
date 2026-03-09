# coding: utf-8

"""
Column producers related to leptons.
"""
from columnflow.production import Producer, producer
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column

ak = maybe_import("awkward")
np = maybe_import("numpy")
coffea = maybe_import("coffea")
maybe_import("coffea.nanoevents.methods.nanoaod")


@producer(
    uses={
        "category_ids",
        "Electron.pt", "Electron.eta", "Electron.phi", "Electron.mass",
        "Electron.pdgId",
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.mass",
        "Muon.pdgId",
    },
    produces={
        "Leptons.pt", "Leptons.eta", "Leptons.phi", "Leptons.mass",
        "Leptons.pdgId",
    },
)
def choose_lepton(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    """
    Choose either muon or electron as the main lepton per event
    based on `channel_id` information and write it to a new column
    `Lepton`.
    """

    # extract only LV columns
    muon = events.Muon[["pt", "eta", "phi", "mass", "pdgId"]]
    electron = events.Electron[["pt", "eta", "phi", "mass", "pdgId"]]
    is_2mu = ak.any(events.category_ids == 20, axis=1)
    is_2e = ak.any(events.category_ids == 10, axis=1)
    leptons = ak.concatenate([
        ak.mask(muon, is_2mu),
        ak.mask(electron, is_2e),
    ], axis=1)

    # attach lorentz vector behavior to lepton
    leptons = ak.with_name(leptons, "PtEtaPhiMLorentzVector")
    # commit lepton to events array
    events = set_ak_column(events, "Leptons", leptons)

    return events
