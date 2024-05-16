# Reconstruction of the heavy Higgs H
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from azh.production.leptons import choose_lepton

np = maybe_import("numpy")
ak = maybe_import("awkward")


@producer(
    uses={
        "Jet", "BJet"
    },
    produces={
        "m_h", 
    },
)
def higgs_reco(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    jets = events.Jet
    bjets = events.BJet
    print("Jets", jets)
    # for l in range(3):
    #     print(l)
    #     print(events.Leptons[l])
    #     print(events.Leptons[:, 0])
    #     print(events.Leptons[:, 1])
    index_jets = ak.argsort(jets.btagDeepFlavB, ascending = False, axis = -1)
    index_bjets = ak.argsort(bjets.btagDeepFlavB, ascending = False, axis = -1)
    sorted_jets = jets[index_jets]
    sorted_bjets = bjets[index_bjets]

    wp_med = self.config_inst.x.btag_working_points.deepjet.medium
    light_jets_mask = jets.btagDeepFlavB < wp_med
    light_jets = jets[light_jets_mask]

    sorted_bjets = ak.pad_none(sorted_bjets,2,axis=1)
    light_jets = ak.pad_none(light_jets,5,axis=1)

    h = ak.where((ak.num(events.BJet, axis=-1) >= 2),sorted_bjets[:, 0]+sorted_bjets[:, 1]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2],
        ak.where((ak.num(events.BJet, axis=-1) == 1),sorted_bjets[:, 0]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3],
        light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3]+light_jets[:,4]))


    print(h)
    print(h.mass)
    events = set_ak_column(events, "m_h", h.mass)
    return events