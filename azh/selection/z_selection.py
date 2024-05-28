from typing import Tuple
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.selection import Selector, SelectionResult, selector
from azh.util import masked_sorted_indices

ak = maybe_import("awkward")


@selector(

    uses={
        "Electron.pt", "Electron.eta", "Electron.mvaFall17V2Iso_WP80", "Electron.mvaFall17V2Iso_WP90", "Electron.phi", "Electron.mass",
        "Muon.pt", "Muon.eta", "Muon.tightId", "Muon.looseId", "Muon.phi", "Muon.mass"
    },
    produces={"cutflow.n_ele", "cutflow.n_muo", "cutflow.n_ele_loose", "cutflow.n_muo_loose", "cutflow.n_ele_high", "cutflow.n_muo_high"},
    exposed=True,
)
def z_selection(
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
        (events.Muon.tightId)
    )

    muo_mask_high = (
        (events.Muon.pt > 35) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.tightId)
    )

    muo_mask_loose = (
        (events.Muon.pt > 20) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.looseId)
    )

    # mask for electrons
    ele_mask = (
        (events.Electron.pt > 20) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaFall17V2Iso_WP80)
    )

    ele_mask_high = (
        (events.Electron.pt > 35) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaFall17V2Iso_WP80)
    )

    ele_mask_loose = (
        (events.Electron.pt > 20) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaFall17V2Iso_WP90)
    )

    events = set_ak_column(events, "cutflow.n_ele", ak.sum(ele_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_muo", ak.sum(muo_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_loose", ak.sum(ele_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_loose", ak.sum(muo_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_high", ak.sum(ele_mask_high, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_high", ak.sum(muo_mask_high, axis=1))

    m_z = 90


    loose_leptons = ak.concatenate([
        events.Electron[ele_mask_loose] * 1,
        events.Muon[muo_mask_loose] * 1,
    ], axis=1)

    lepton_pairs = ak.combinations(loose_leptons, 2)
    l1, l2 = ak.unzip(lepton_pairs)
    lepton_pairs["m_inv"] = (l1 + l2).mass
    z_sel = ak.any((abs(lepton_pairs.m_inv - m_z ) <= 10), axis=1)


    # build and return selection results plus new columns
    return events, SelectionResult(
        steps={
            "z_sel": z_sel,
        },
        objects={

        },
        aux={
        },
    )
