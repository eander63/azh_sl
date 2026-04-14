from typing import Tuple
from columnflow.util import maybe_import
from columnflow.columnar_util import set_ak_column
from columnflow.selection import Selector, SelectionResult, selector
# from azh.util import masked_sorted_indices

ak = maybe_import("awkward")


@selector(

    uses={
        "Electron.pt", "Electron.eta","Electron.phi","Electron.mass", "Electron.mvaIso_WP80",
        "Electron.mvaIso_WP90", "Electron.charge",
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.mass","Muon.tightId", "Muon.looseId", "Muon.highPtId", "Muon.tkIsoId", "Muon.charge",
    },
    produces={
        "cutflow.n_ele", "cutflow.n_muo", "cutflow.n_ele_loose",
        "cutflow.n_muo_loose", "cutflow.n_ele_high", "cutflow.n_muo_high",
    },
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

    ele_test = (
        (events.Electron.pt > 20) &
        (abs(events.Electron.eta) < 2.4) &
        (events.Electron.mvaIso_WP80)
    )
    muo_test = (
        (events.Muon.pt > 20) &
        (abs(events.Muon.eta) < 2.4) &
        (events.Muon.highPtId == 2) &
        (events.Muon.tkIsoId == 2)
    )
    events = set_ak_column(events, "cutflow.n_ele", ak.sum(ele_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_muo", ak.sum(muo_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_loose", ak.sum(ele_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_loose", ak.sum(muo_mask_loose, axis=1))
    events = set_ak_column(events, "cutflow.n_ele_high", ak.sum(ele_mask_high, axis=1))
    events = set_ak_column(events, "cutflow.n_muo_high", ak.sum(muo_mask_high, axis=1))

    m_z = 91.188

    # same-flavor OS pairs only (ee or mumu separately)
    def ossf_z_sel(collection, mask):
        pairs = ak.combinations(collection[mask], 2, fields=["l1", "l2"])
        os = pairs.l1.charge * pairs.l2.charge < 0
        m_inv = (pairs.l1 + pairs.l2).mass
        return ak.any(os & (abs(m_inv - m_z) <= 5), axis=1)

    ee_z_sel   = ossf_z_sel(events.Electron, ele_mask_loose)
    mumu_z_sel = ossf_z_sel(events.Muon,     muo_mask_loose)
    z_sel = ak.fill_none(ee_z_sel | mumu_z_sel, False)

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
