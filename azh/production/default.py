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
from azh.production.leptons import three_lepton_info
from azh.production.ml_inputs import ml_inputs
from azh.production.dy_producer import dy_producer
from azh.production.trigger import trigger
from azh.production.weights import weights, event_weight
from azh.config.categories import add_categories_mz
from azh.config.categories import add_categories_bjets
from azh.config.categories import add_categories_njets
from azh.config.categories import add_category_2l
from azh.config.categories import add_categories_3l
from azh.config.categories import add_categories_met
from azh.config.categories import add_categories_n1


ak = maybe_import("awkward")
coffea = maybe_import("coffea")
np = maybe_import("numpy")
maybe_import("coffea.nanoevents.methods.nanoaod")


@producer(
    uses={
        category_ids, normalization_weights, trigger,
        weights, z_boson, higgs_reco, choose_lepton, three_lepton_info, ml_inputs,
        prepare_objects, event_weight, "MET.pt","MET.phi","process_id","cutflow*",
    },
    produces={
        category_ids, normalization_weights, trigger,
        weights, z_boson, choose_lepton, three_lepton_info,
        higgs_reco, event_weight, "event_number","process_id",
    },
)
def default(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    # events = self[azh_quantities](events, **kwargs)
    # category ids
    # events = self[category_ids](events, **kwargs)
    events = self[choose_lepton](events, **kwargs)
    events = self[three_lepton_info](events, **kwargs)
    events = self[prepare_objects](events, **kwargs)
    events = self[z_boson](events, **kwargs)
    # from IPython import embed; embed()
    events = self[higgs_reco](events, **kwargs)
    events = self[category_ids](events, **kwargs)
    # events = self[trigger](events, **kwargs)
    # mc-only weights
    # from IPython import embed; embed()

    if self.dataset_inst.is_mc:
        # normalization weights
        # from IPython import embed; embed()
        events = self[weights](events, **kwargs)
        # from IPython import embed; embed()
        events = self[event_weight](events, **kwargs)
        # from IPython import embed; embed()
        if self.dataset_inst.has_tag("is_dy"):
            events = self[dy_producer](events, **kwargs)
    # deterministoc seeds
    # events = self[category_ids](events, **kwargs)
    #    #    # events = self[ml_inputs](events, **kwargs)
    #
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
    # #    # with open('/nfs/dust/cms/user/fischery/2HDM/AZH/azh/production/events_sorted.txt', 'w') as file:
    #     file.writelines(sorted_lines)

    events = set_ak_column(events, "event_number", events.event)
    # len_mask = events.event < 1584100
    # e_mask = (events.category_ids[:,1] == 23110)
    # m_mask = (events.category_ids[:,1] == 23120)
    # l_mask = e_mask | m_mask
    # event_mask = len_mask & l_mask
    # cut_cat = (abs((events.m_z-91.188))<5) & (ak.num(events.Jet.pt)>5) & (events.cutflow.n_bjet>1)
    #    #    #    #    #    #    #    #    # for i in range(len(events[event_mask])):
    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    #    # for i in nummern_liste[:100]:
    #     #    #     for j in range(len(events[len_mask])):
    #         #    #         found = False
    #         if i == events[len_mask][j].event:
    #    #             found = True
    #             if not ((events[len_mask][j].category_ids[1] == 23110) | (events[len_mask][j].category_ids[1] == 23120)): # noqa
    #    #    #    #             break
    #     if not found:
    #
    return events


@default.init
def default_init(self: Producer) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.has_tag("is_dy"):
        self.uses.add(dy_producer)
        self.produces.add(dy_producer)
    # add production categories to config
    # if not self.config_inst.get_aux("has_categories_production", False):
    add_categories_mz(self.config_inst)
    add_category_2l(self.config_inst)
    add_categories_bjets(self.config_inst)
    # add_categories_njets(self.config_inst)  # disabled: combo explosion -> ak.concatenate IndexError
    add_categories_3l(self.config_inst)
    add_categories_met(self.config_inst)
    # add_categories_n1(self.config_inst)
    # self.config_inst.x.has_categories_production = True
