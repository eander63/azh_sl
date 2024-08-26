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
        "m_h", "m_a", "del_m","n_jets", "n_bjets" 
    },
)
def higgs_reco(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    jets = events.Jet
    bjets = events.BJet
    # print("Jets", jets)
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
    light_jets = ak.pad_none(light_jets,6,axis=1)
    sorted_jets = ak.pad_none(sorted_jets,6,axis=1)

    h = ak.where((ak.num(events.Jet, axis=-1) == 5), ak.where((ak.num(events.BJet, axis=-1) > 2),sorted_jets[:, 0]+sorted_jets[:, 1]+sorted_jets[:,2]+sorted_jets[:,3]+sorted_jets[:,4],
        ak.where((ak.num(events.BJet, axis=-1) == 2),sorted_bjets[:, 0]+sorted_bjets[:, 1]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2],
        ak.where((ak.num(events.BJet, axis=-1) == 1),sorted_bjets[:, 0]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3],
        light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3]+light_jets[:,4]))),
        ak.where((ak.num(events.BJet, axis=-1) > 2),sorted_jets[:, 0]+sorted_jets[:, 1]+sorted_jets[:,2]+sorted_jets[:,3]+sorted_jets[:,4]+sorted_jets[:,5],
        ak.where((ak.num(events.BJet, axis=-1) == 2),sorted_bjets[:, 0]+sorted_bjets[:, 1]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3],
        ak.where((ak.num(events.BJet, axis=-1) == 1),sorted_bjets[:, 0]+light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3]+light_jets[:,4],
        light_jets[:,0]+light_jets[:,1]+light_jets[:,2]+light_jets[:,3]+light_jets[:,4]+light_jets[:,5]))))

    mass_h = h.mass
    mass_h = ak.where(np.isfinite(mass_h),mass_h, ak.full_like(mass_h, 0) )
    # print(h)
    # for i in range(100):
        # print("Now at", i)
        # print((ak.num(events.BJet, axis=-1))[i])
        # print("Bjets:")
        # for j in sorted_bjets[i]:
        #     print(j)
        # print("light jets:")
        # for j in light_jets[i]:
        #     print(j)
    #     print(h[i])
    # print(h.mass)

    n_jets = ak.num(events.Jet, axis=-1)
    n_bjets = ak.num(events.BJet, axis=-1)
    events = set_ak_column(events, "m_h", mass_h)
    events = set_ak_column(events, "n_jets", n_jets)
    events = set_ak_column(events, "n_bjets", n_bjets)

    z = events.Leptons[:, 0] + events.Leptons[:, 1]
    mass_z = z.mass
    mass_z = ak.where(np.isfinite(mass_z),mass_z, ak.full_like(mass_z, 0) )
    a = z + h
    mass_a = a.mass
    mass_a = ak.where(np.isfinite(mass_a),mass_a, ak.full_like(mass_a, 0) )
    del_m = mass_a - mass_h
    events = set_ak_column(events, "m_a", mass_a)
    events = set_ak_column(events, "del_m", del_m)
    # print(a)
    return events