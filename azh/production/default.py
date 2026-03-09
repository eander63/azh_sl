# coding: utf-8

"""
Column production methods related to higher-level features.
"""


from columnflow.production import Producer, producer
from columnflow.production.categories import category_ids
from columnflow.production.normalization import normalization_weights
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
# from columnflow.production.cms.btag import btag_weights

# from azh.production.azh_quantities import azh_quantities
from azh.production.z_boson import z_boson
from azh.production.higgs_reco import higgs_reco
from azh.production.prepare_objects import prepare_objects
from azh.production.leptons import choose_lepton
from azh.production.ml_inputs import ml_inputs
from azh.production.dy_producer import dy_producer
from azh.production.trigger import trigger
from azh.production.weights import weights, event_weight
from azh.config.categories import add_categories_mz
from azh.config.categories import add_categories_bjets
from azh.config.categories import add_categories_njets


ak = maybe_import("awkward")
coffea = maybe_import("coffea")
np = maybe_import("numpy")
maybe_import("coffea.nanoevents.methods.nanoaod")


@producer(
    uses={
        category_ids, normalization_weights,dy_producer, trigger,
        weights, z_boson, higgs_reco, choose_lepton, ml_inputs,
        prepare_objects, event_weight, "MET.pt","MET.phi","process_id","cutflow*",
    },
    produces={
        category_ids, normalization_weights,dy_producer, trigger,
        weights, z_boson, choose_lepton,
        higgs_reco, event_weight, "event_number","process_id",
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    print("WELCOME TO THE DEFAULT PRODUCER")
    # events = self[azh_quantities](events, **kwargs)
    # category ids
    # events = self[category_ids](events, **kwargs)
    events = self[choose_lepton](events, **kwargs)
    events = self[prepare_objects](events, **kwargs)
    events = self[z_boson](events, **kwargs)
    # from IPython import embed; embed()
    # events = self[higgs_reco](events, **kwargs)
    events = self[category_ids](events, **kwargs)
    # events = self[trigger](events, **kwargs)
    # mc-only weights
    # from IPython import embed; embed()

    if self.dataset_inst.is_mc:
        # normalization weights
        print("NWeights BEfore: ", events.mc_weight)
        # from IPython import embed; embed()
        events = self[weights](events, **kwargs)
        # from IPython import embed; embed()
        events = self[event_weight](events, **kwargs)
        # from IPython import embed; embed()
        # print("Weights: ", events.event_weight)
        # print("Normalized Weights: ", events.normalization_weight)
    if self.dataset_inst.has_tag("is_dy"):
        pass
        events = self[dy_producer](events, **kwargs)
    # deterministoc seeds
    # events = self[category_ids](events, **kwargs)
    # print(events.category_ids)
    # print(events.category_ids)
    # events = self[ml_inputs](events, **kwargs)
    # print(events.category_ids)

    # not_passed = ~passed
    # event_id = event_id[not_passed]
    # event_mask = np.isin(events.event, event_id)

    # with open('/nfs/dust/cms/user/fischery/2HDM/AZH/azh/production/events.txt', 'r') as file:
    #     lines = file.readlines()
    # sorted_lines = sorted(
    #     [line for line in lines if len(line.split()) >= 2],  # Zeilen mit mindestens 2 Spalten
    #     key=lambda line: int(line.split()[0])
    # )
    # nummern_liste = [int(line.split()[0]) for line in sorted_lines if len(line.split()) >= 1]
    # # print(nummern_liste)
    # with open('/nfs/dust/cms/user/fischery/2HDM/AZH/azh/production/events_sorted.txt', 'w') as file:
    #     file.writelines(sorted_lines)

    # print(len(events))
    events = set_ak_column(events, "event_number", events.event)
    # len_mask = events.event < 1584100
    # e_mask = (events.category_ids[:,1] == 23110)
    # m_mask = (events.category_ids[:,1] == 23120)
    # l_mask = e_mask | m_mask
    # event_mask = len_mask & l_mask
    # cut_cat = (abs((events.m_z-91.188))<5) & (ak.num(events.Jet.pt)>5) & (events.cutflow.n_bjet>1)
    # print(events.category_ids)
    # print("Total: ",len(events))
    # print("SR Lepton: ",len(events[l_mask]))
    # print("SR Lepton?: ",len(events[cut_cat]))
    # print("SR Ele:", len(events[e_mask]))
    # print("SR M:",len(events[m_mask]))
    # print(len(events[event_mask]))
    # print("Number of events found:", len(events[event_mask]))
    # for i in range(len(events[event_mask])):
    #     print("_____________________________________")
    #     print("Event Number ", (events[event_mask][i].event))
    #     print("Jet 1 pt ", (events[event_mask].Jet[:,0][i].pt))
    #     print("Jet 1 eta ", (events[event_mask].Jet[:,0][i].eta))
    #     print("Jet 2 pt ", (events[event_mask].Jet[:,1][i].pt))
    #     print("Jet 2 eta ", (events[event_mask].Jet[:,1][i].eta))
    #     print("Jet 3 pt ", (events[event_mask].Jet[:,2][i].eta))
    #     print("Jet 4 pt ", (events[event_mask].Jet[:,3][i].eta))
    #     print("Jet 5 eta ", (events[event_mask].Jet[:,4][i].eta))
    #     print("Lepton 1 pt ", (events[event_mask].Leptons[:,0][i].pt))
    #     print("Lepton 1 eta ", (events[event_mask].Leptons[:,0][i].eta))
    #     print("Lepton 2 pt ", (events[event_mask].Leptons[:,1][i].pt))
    #     print("Lepton 1 eta ", (events[event_mask].Leptons[:,1][i].eta))
    #     print("Number of electrons ", (events[event_mask][i].cutflow.n_ele))
    #     print("Number of muons ", (events[event_mask][i].cutflow.n_muo))
    #     print("Number of jets ", (events[event_mask][i].cutflow.n_jet))
    #     print("Number of b jets ", (events[event_mask][i].cutflow.n_bjet))
    #     print("Weight ", (events[event_mask][i].mc_weight))
    #     print("Ele Weight ", (events[event_mask][i].electron_weight))
    #     print("Norm Weight ", (events[event_mask][i].event_weight))
    #     print("Z mass ", (events[event_mask][i].m_z))
    #     print("Cat ", (events[event_mask][i].category_ids))
    # for i in nummern_liste[:100]:
    #     # print(i)
    #     for j in range(len(events[len_mask])):
    #         # print(events[len_mask][j].event)
    #         found = False
    #         if i == events[len_mask][j].event:
    #             print(i)
    #             found = True
    #             if not ((events[len_mask][j].category_ids[1] == 23110) | (events[len_mask][j].category_ids[1] == 23120)): # noqa
    #                 print("Not in category mu or e")
    #                 print(i)
    #                 print(events[len_mask][j].category_ids)
    #             break
    #     if not found:
    #         print("Didnt find event:", i)

    return events


@default.init
def default_init(self: Producer) -> None:
    # add production categories to config
    # if not self.config_inst.get_aux("has_categories_production", False):
    add_categories_mz(self.config_inst)
    # add_categories_bjets(self.config_inst)
    # add_categories_njets(self.config_inst)
    # self.config_inst.x.has_categories_production = True
