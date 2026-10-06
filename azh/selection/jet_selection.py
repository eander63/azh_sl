"""
Jet selection.

Works on CandJet (calibration/corrections.py): jets with |eta| < 2.5, TightLepVeto
and pT > 30 GeV in the nominal or any JES/JER variation, in events that can pass
the preselection. Here only the Delta R >= 0.3 cleaning against the loose
leptons (AN-2022/158 Sec. 4.4) is applied; the analysis jet definition
(pT > 30 GeV on the possibly shifted pT) is applied in production
(production/jets.py), so the JES and JER variations only need ProduceColumns to
rerun.

No event requirement is placed on jets (the step is always True), so the 2l
Drell-Yan region keeps its full statistics.

The nominal analysis-jet mask (cleaned candidates with nominal pT > 30) is
returned as aux["jet_mask"] for the b-tagging efficiency counts, and the nominal
multiplicities as cutflow.n_jet / cutflow.n_bjet (cutflow only; categories use
the production-level n_jet / n_bjet).
"""

from columnflow.columnar_util import set_ak_column
from columnflow.selection import SelectionResult, Selector, selector
from columnflow.util import maybe_import

from azh.util import masked_sorted_indices

ak = maybe_import("awkward")
np = maybe_import("numpy")

JET_PT_MIN = 30.0
LEPTON_DR_MIN = 0.3


def delta_r_clean(jets: ak.Array, leptons: ak.Array, dr_min: float) -> ak.Array:
    """True for jets with Delta R >= dr_min to all *leptons* (records with eta, phi)."""
    pairs = ak.cartesian([jets, leptons], axis=1, nested=True)
    j, lep = ak.unzip(pairs)
    dphi = (j.phi - lep.phi + np.pi) % (2 * np.pi) - np.pi
    dr = np.sqrt((j.eta - lep.eta) ** 2 + dphi ** 2)
    return ak.all(dr >= dr_min, axis=2)


@selector(
    uses={"CandJet.{pt,eta,phi}", "Electron.{eta,phi}", "Muon.{eta,phi}"},
    produces={"cutflow.n_jet", "cutflow.n_bjet"},
    exposed=True,
)
def jet_selection(
    self: Selector,
    events: ak.Array,
    lepton_results: SelectionResult = None,
    **kwargs,
) -> tuple[ak.Array, SelectionResult]:
    jet = events.CandJet

    if lepton_results is None:
        raise ValueError("jet_selection needs lepton_results (from lepton_selection) for the Delta R cleaning")
    ele = events.Electron[lepton_results.aux["ele_loose_mask"]]
    mu = events.Muon[lepton_results.aux["muo_loose_mask"]]
    leptons = ak.concatenate([
        ak.zip({"eta": ele.eta, "phi": ele.phi}),
        ak.zip({"eta": mu.eta, "phi": mu.phi}),
    ], axis=1)
    candidate = ak.fill_none(delta_r_clean(jet, leptons, LEPTON_DR_MIN), False)

    # nominal analysis jets (b-tag efficiency counts and cutflow only)
    jet_mask = ak.fill_none(candidate & (jet["pt"] > JET_PT_MIN), False)
    btag = self.config_inst.x.btag_default
    bjet_mask = jet_mask & (jet[btag.column] >= btag.wp)
    events = set_ak_column(events, "cutflow.n_jet", ak.sum(jet_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_bjet", ak.sum(bjet_mask, axis=1))

    return events, SelectionResult(
        steps={"Jet": ak.ones_like(ak.num(jet["pt"]), dtype=bool)},
        objects={"CandJet": {"CandJet": masked_sorted_indices(candidate, jet["pt"])}},
        aux={"jet_mask": jet_mask},
    )


@jet_selection.init
def jet_selection_init(self: Selector, **kwargs) -> None:
    self.uses.add(f"CandJet.{self.config_inst.x.btag_default.column}")
