# coding: utf-8

"""
Producers for ML inputs
"""
import functools
import itertools

from columnflow.production import Producer, producer
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column


ak = maybe_import("awkward")
np = maybe_import("numpy")
coffea = maybe_import("coffea")
maybe_import("coffea.nanoevents.methods.nanoaod")

# use float32 type for ML input columns
set_ak_column_f32 = functools.partial(set_ak_column, value_type=np.float32)


@producer(
    uses={
        # AK4 jets
        "Jet.pt", "Jet.eta", "Jet.phi", "Jet.mass",
        "Jet.btagDeepFlavB",
        "Leptons",
        # MET
        "MET.pt", "MET.phi",
        "n_jets",
        "n_bjets",
        "m_a",
        "pt_z",
        "m_h",
        "del_m",
        "category_ids",
        "deltaR_b_z",
        "deltaPhi_MET_Jet1",
        "deltaPhi_MET_Jet2",
        "deltaPhi_MET_Jet3",
        "MET_ht",
        "m_z"
    },
    # produces={
    #     weights,
    #     # columns for ML inputs are set by the init function
    # },
)
def ml_inputs(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    # attach coffea behavior
    events = ak.Array(events, behavior=coffea.nanoevents.methods.nanoaod.behavior)

    # name of table to place ML variables in
    ns = self.ml_namespace
    # run dependencies
    # events = self[choose_lepton](events, **kwargs)

    # object arrays
    jet = ak.with_name(events.Jet, "Jet")
    Leptons = ak.with_name(events.Leptons, "PtEtaPhiMLorentzVector")
    met = events.MET
    # btag score for AK4 jets
    jet["btag"] = jet.btagDeepFlavB

    # jet/fatjet multiplicities
    events = set_ak_column(events, f"{ns}.n_jets", events.n_jets)
    events = set_ak_column(events, f"{ns}.n_bjets", events.n_bjets)
    events = set_ak_column(events, f"{ns}.del_m", events.del_m)
    events = set_ak_column(events, f"{ns}.m_a", events.m_a)
    events = set_ak_column(events, f"{ns}.m_h", events.m_h)
    events = set_ak_column(events, f"{ns}.pt_z", events.pt_z)
    events = set_ak_column(events, f"{ns}.m_z", events.m_z)
    events = set_ak_column(events, f"{ns}.category_ids", events.category_ids)
    events = set_ak_column(events, f"{ns}.deltaR_b_z", events.deltaR_b_z)
    events = set_ak_column(events, f"{ns}.deltaPhi_MET_Jet1", events.deltaPhi_MET_Jet1)
    events = set_ak_column(events, f"{ns}.deltaPhi_MET_Jet2", events.deltaPhi_MET_Jet2)
    events = set_ak_column(events, f"{ns}.deltaPhi_MET_Jet3", events.deltaPhi_MET_Jet3)
    events = set_ak_column(events, f"{ns}.MET_ht", events.MET_ht)

    # -- helper functions

    def set_vars(events, name, arr, n_max, attrs, default=-10.0):
        # pad to miminal length
        arr = ak.pad_none(arr, n_max)
        # extract fields
        for i, attr in itertools.product(range(1, n_max + 1), attrs):
            # print(f"{self.ml_namespace}.{name}_{attr}_{i}")
            value = ak.nan_to_none(getattr(arr[:, i - 1], attr))
            value = ak.fill_none(value, default)
            events = set_ak_column_f32(events, f"{self.ml_namespace}.{name}_{attr}_{i}", value)
        return events

    def set_vars_single(events, name, arr, attrs, default=-10.0):
        for attr in attrs:
            # print(name)
            # print(f"{self.ml_namespace}.{name}_{attr}")
            value = ak.nan_to_none(getattr(arr, attr))
            value = ak.fill_none(value, default)
            events = set_ak_column_f32(events, f"{self.ml_namespace}.{name}_{attr}", value)
        return events
    # AK4 jets
    events = set_vars(
        events, "jet", jet, n_max=6,
        attrs=("energy", "pt", "eta", "phi", "mass", "btag"),
    )

    # AK8 jets

    # Lepton
    events = set_vars(
        events, "Leptons", Leptons, n_max=2,
        attrs=("energy", "pt", "eta", "phi"),
    )
    

    # MET
    events = set_vars_single(
        events, "met", met,
        attrs=("pt", "phi"),
    )

    # weights
    # events = self[weights](events, **kwargs)

    return events


@ml_inputs.init
def ml_inputs_init(self: Producer) -> None:
    # put ML input columns in separate namespace/table
    self.ml_namespace = "MLInput"

    # store column names
    self.ml_columns = {
        "n_jets",
        "n_bjets",
        "m_h",
        "pt_z",
        "m_a",
        "del_m",
        "category_ids",
        "deltaR_b_z",
        "deltaPhi_MET_Jet1",
        "deltaPhi_MET_Jet2",
        "deltaPhi_MET_Jet3",
        "MET_ht",
        "m_z"
        
    } | {
        f"jet_{var}_{i + 1}"
        for var in ("energy", "pt", "eta", "phi", "mass", "btag")
        for i in range(6)
    } | {
        f"Leptons_{var}_{i + 1}"
        for var in ("energy", "pt", "eta", "phi")
        for i in range(2)
    } | {
        f"met_{var}"
        for var in ("pt", "phi")
    } 

    # declare produced columns
    self.produces |= {
        f"{self.ml_namespace}.{col}"
        for col in self.ml_columns
    }

    # add production categories to config
    if not self.config_inst.get_aux("has_categories_production", False):
        self.config_inst.x.has_categories_production = True

    # add ml variables to config
    if not self.config_inst.get_aux("has_variables_ml", False):
        # add_variables_ml(self.config_inst)
        self.config_inst.x.has_variables_ml = True