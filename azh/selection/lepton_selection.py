from typing import Tuple
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.selection import Selector, SelectionResult, selector
from azh.util import masked_sorted_indices

ak = maybe_import("awkward")


@selector(

    uses={
        "Electron.pt", "Electron.eta", "Electron.mvaIso_WP80",
        "Electron.mvaIso_WP90", "Electron.charge",
        "Muon.pt", "Muon.eta", "Muon.tightId", "Muon.looseId", "Muon.highPtId", "Muon.tkIsoId", "Muon.charge",
    },
    produces={
        "cutflow.n_ele", "cutflow.n_muo", "cutflow.n_ele_loose", "cutflow.n_muo_loose",
        "cutflow.n_ele_high", "cutflow.n_muo_high",
        "cutflow.muon1_pt", "cutflow.muon1_eta", "cutflow.muon2_pt", "cutflow.muon2_eta",
        "cutflow.electron1_pt", "cutflow.electron1_eta", "cutflow.electron2_pt", "cutflow.electron2_eta",
    },
    exposed=True,
)
def lepton_selection(
    self: Selector,
    events: ak.Array,
    **kwargs,
) -> Tuple[ak.Array, SelectionResult]:
    # lepton selection based on old UHH2 framework
    # https://github.com/UHH2/DiJetJERC/blob/ff98eebbd44931beb016c36327ab174fdf11a83f/src/AnalysisModule_DiJetTrg.cxx#L703
    # IDs in JME Nano https://cms-nanoaod-integration.web.cern.ch/integration/master-106X/mc102X_doc.html
    # mask for muons
    muo_mask = (
        (events.Muon.pt > 20) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.highPtId == 2) &
        (events.Muon.tkIsoId == 2)
    )

    muo_mask_high = (
        (events.Muon.pt > 35) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.highPtId == 2) &
        (events.Muon.tkIsoId == 2)
    )

    muo_mask_loose = (
        (events.Muon.pt > 20) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.looseId) &
        ((events.Muon.tkIsoId == 1) |
        (events.Muon.tkIsoId == 2))
    )

    # mask for electrons
    ele_mask = (
        (events.Electron.pt > 20) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaIso_WP80)
    )

    ele_mask_high = (
        (events.Electron.pt > 35) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaIso_WP80)
    )

    ele_mask_loose = (
        (events.Electron.pt > 20) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaIso_WP90)
    )

    events = set_ak_column(events, "cutflow.n_ele", ak.sum(ele_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_muo", ak.sum(muo_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_loose", ak.sum(ele_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_loose", ak.sum(muo_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_high", ak.sum(ele_mask_high, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_high", ak.sum(muo_mask_high, axis=1))

    # select only events with exactly 2 same-flavor OS loose leptons,
    # with at least one passing the high-pT threshold
    lep_sel = (
        (
            (events.cutflow.n_ele_loose == 2) &
            (events.cutflow.n_muo_loose == 0) &
            (events.cutflow.n_ele_high > 0)
        ) | (
            (events.cutflow.n_muo_loose == 2) &
            (events.cutflow.n_ele_loose == 0) &
            (events.cutflow.n_muo_high > 0)
        )
    )

    # i = 0
    # j = 0
    # print(events.Electron.pt>20)
    # print((abs(events.Electron.eta) < 2.4))
    # print( (events.Electron.pt > 20) &(abs(events.Electron.eta) < 2.4))
    # for n in range(100):
    #     if (events.cutflow.n_ele_test[n]>1 or events.cutflow.n_muo_test[n]>1):
    #         print(n)
    #         print((events.cutflow.n_ele[n] == 2) & (events.cutflow.n_ele_high[n] > 0 ) & (events.cutflow.n_ele_loose[n] == 2) & (events.cutflow.n_muo_loose[n] == 0))  # noqa
    #         print((events.cutflow.n_muo[n] == 2) & (events.cutflow.n_muo_high[n] > 0 ) & (events.cutflow.n_muo_loose[n] == 2) & (events.cutflow.n_ele_loose[n] == 0))  # noqa
    #         print("Ele:")
    #         print(events.Electron.pt[n])
    #         print(events.Electron.eta[n])
    #         print(events.Electron.mvaFall17V2Iso_WP80[n])
    #         print("Muo")
    #         print(events.Muon.pt[n])
    #         print(events.Muon.eta[n])
    #         print(events.Muon.tightId[n])
    #         print(events.Muon.tkIsoId[n])
    #         if events.cutflow.n_ele_test[n]>1:
    #             # print("An Electron!")
    #             i = i + 1
    #         if events.cutflow.n_muo_test[n]>1:
    #             # print("A Muon!")
    #             j = j + 1
    # print("Number of Ele surviving",i)
    # print("Number of Muo surviving",j)

    # for n in range(len(events.cutflow.n_ele_test)):
    #     if (lep_sel[n]):
    #         print(n)
    #         print("Ele:")
    #         print(events.Electron.pt[n])
    #         print(events.Electron.eta[n])
    #         print(events.Electron.mvaFall17V2Iso_WP80[n])
    #         print("Muo")
    #         print(events.Muon.pt[n])
    #         print(events.Muon.eta[n])
    #         print(events.Muon.tightId[n])
    #         if ((events.cutflow.n_ele[n] == 2) & (events.cutflow.n_ele_high[n] > 0 ) & (events.cutflow.n_ele_loose[n] == 2) & (events.cutflow.n_muo_loose[n] == 0)) :  # noqa
    #             print("An Electron!")
    #             i = i + 1
    #         if ((events.cutflow.n_muo[n] == 2) & (events.cutflow.n_muo_high[n] > 0 ) & (events.cutflow.n_muo_loose[n] == 2) & (events.cutflow.n_ele_loose[n] == 0)):  # noqa
    #             print("A Muon!")
    #             j = j + 1
    # print("Number of Ele surviving",i)
    # print("Number of Muo surviving",j)
    # for n in range(len(events.cutflow.n_ele)):
    #     # print(events.cutflow.n_ele[n])
    #     if (events.cutflow.n_ele[n]>1 or events.cutflow.n_muo[n]>1):
    #         print(n)
    #         print("N_ele:",events.cutflow.n_ele[n])
    #         print("N_muo:",events.cutflow.n_muo[n])
    #         print(events.Electron.pt[n])
    #         print(events.Electron.eta[n])
    #         print(events.Electron.mvaFall17V2Iso_WP80[n])
    #         print(events.Muon.pt[n])
    #         print(events.Muon.eta[n])
    #         print(events.Muon.tightId[n])
    ele_indices = masked_sorted_indices(ele_mask, events.Electron.pt)
    muo_indices = masked_sorted_indices(muo_mask, events.Muon.pt)

    ele_mask = ak.fill_none(ele_mask, False)
    muo_mask = ak.fill_none(muo_mask, False)

    lep_sel = ak.fill_none(lep_sel, False)

    ele = events.Electron[ele_indices]
    padded_ele = ak.pad_none(ele, 2)
    muo = events.Muon[muo_indices]
    padded_muo = ak.pad_none(muo, 2)

    os_sel = (ak.fill_none((padded_muo.charge[:, 0] != padded_muo.charge[:, 1]), False) | ak.fill_none((padded_ele.charge[:, 0] != padded_ele.charge[:, 1]), False))  # noqa
    lep_sel = lep_sel & os_sel
    for i in range(2):
        events = set_ak_column(events, f"cutflow.electron{i+1}_pt",
        ak.where((ak.is_none(padded_ele.pt[:, {i}][:, 0])), -100, padded_ele.pt[:, {i}][:, 0]))
        events = set_ak_column(events, f"cutflow.electron{i+1}_eta",
        ak.where((ak.is_none(padded_ele.eta[:, {i}][:, 0])), -100, padded_ele.eta[:, {i}][:, 0]))
        events = set_ak_column(events, f"cutflow.muon{i+1}_pt",
        ak.where((ak.is_none(padded_muo.pt[:, {i}][:, 0])), -100, padded_muo.pt[:, {i}][:, 0]))
        events = set_ak_column(events, f"cutflow.muon{i+1}_eta",
        ak.where((ak.is_none(padded_muo.eta[:, {i}][:, 0])), -100, padded_muo.eta[:, {i}][:, 0]))

    # build and return selection results plus new columns
    return events, SelectionResult(
        steps={
            "Lepton": lep_sel,
        },
        objects={
            "Electron": {
                "Electron": ele_indices,
            },
            "Muon": {
                "Muon": muo_indices,
            },
        },
        aux={
            "ele_mask": ele_mask,
            "n_central_eletons": ak.num(ele_indices),
            "muo_mask": muo_mask,
            "n_central_muons": ak.num(muo_indices),
        },
    )
