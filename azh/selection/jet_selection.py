"""
Jet selection.

Keeps the CANDIDATE jets that ReduceEvents stores; the analysis jet definition
(pT > 30 GeV) is applied in production (production/jets.py), so that the JES
and JER variations only need ProduceColumns to rerun.

Candidate jets:
  * |eta| < 2.5 and jet ID TightLepVeto (Jet.jetId bit 2, which is AND-ed with
    tight; for NanoAOD v15 the bitmap is rebuilt in calibration/corrections.py)
  * Delta R >= 0.3 to every loose lepton (pT > 10), AN-2022/158 Sec. 4.4
  * pT > 30 GeV in AT LEAST ONE of: nominal, any JES source up/down, JER up/down.
    That is exactly the set of jets any shifted analysis selection can use, so
    keeping them loses nothing and makes the jet shifts production-level.

No event requirement is placed on jets (the step is always True), so the 2l
Drell-Yan region keeps its full statistics.

The nominal analysis-jet mask (candidates with nominal pT > 30) is returned as
aux["jet_mask"] for the b-tagging efficiency counts, and the nominal
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
JET_ETA_MAX = 2.5
LEPTON_DR_MIN = 0.3


def delta_r_clean(jets: ak.Array, leptons: ak.Array, dr_min: float) -> ak.Array:
    """True for jets with Delta R >= dr_min to all *leptons* (records with eta, phi)."""
    pairs = ak.cartesian([jets, leptons], axis=1, nested=True)
    j, lep = ak.unzip(pairs)
    dphi = (j.phi - lep.phi + np.pi) % (2 * np.pi) - np.pi
    dr = np.sqrt((j.eta - lep.eta) ** 2 + dphi ** 2)
    return ak.all(dr >= dr_min, axis=2)


@selector(
    uses={"Jet.{pt,eta,phi,jetId}", "Electron.{eta,phi}", "Muon.{eta,phi}"},
    produces={"cutflow.n_jet", "cutflow.n_bjet"},
    exposed=True,
)
def jet_selection(
    self: Selector,
    events: ak.Array,
    lepton_results: SelectionResult = None,
    **kwargs,
) -> tuple[ak.Array, SelectionResult]:
    jet = events.Jet

    # ID and acceptance (v12 bitmap: bit 1 tight, bit 2 tight lepton veto)
    base = (abs(jet.eta) < JET_ETA_MAX) & ((jet.jetId & 0b110) == 0b110)

    # Delta R cleaning against the loose leptons of lepton_selection
    if lepton_results is None:
        raise ValueError("jet_selection needs lepton_results (from lepton_selection) for the Delta R cleaning")
    ele = events.Electron[lepton_results.aux["ele_loose_mask"]]
    mu = events.Muon[lepton_results.aux["muo_loose_mask"]]
    leptons = ak.concatenate([
        ak.zip({"eta": ele.eta, "phi": ele.phi}),
        ak.zip({"eta": mu.eta, "phi": mu.phi}),
    ], axis=1)
    base = base & delta_r_clean(jet, leptons, LEPTON_DR_MIN)

    # largest pT over nominal and every variation the calibrator wrote
    pt_max = jet.pt
    for col in self.variation_columns:
        pt_max = np.maximum(pt_max, jet[col])
    candidate = ak.fill_none(base & (pt_max > JET_PT_MIN), False)

    # nominal analysis jets (b-tag efficiency counts and cutflow only)
    jet_mask = ak.fill_none(base & (jet.pt > JET_PT_MIN), False)
    btag = self.config_inst.x.btag_default
    bjet_mask = jet_mask & (jet[btag.column] >= btag.wp)
    events = set_ak_column(events, "cutflow.n_jet", ak.sum(jet_mask, axis=1))
    events = set_ak_column(events, "cutflow.n_bjet", ak.sum(bjet_mask, axis=1))

    return events, SelectionResult(
        steps={"Jet": ak.ones_like(ak.num(jet.pt), dtype=bool)},
        objects={"Jet": {"Jet": masked_sorted_indices(candidate, jet.pt)}},
        aux={"jet_mask": jet_mask},
    )


@jet_selection.init
def jet_selection_init(self: Selector, **kwargs) -> None:
    self.uses.add(f"Jet.{self.config_inst.x.btag_default.column}")
    # varied pT columns written by the calibrator (MC only)
    self.variation_columns = []
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        sources = self.config_inst.x.jec.Jet.uncertainty_sources
        self.variation_columns = [
            f"pt_jec_{src}_{d}" for src in sources for d in ("up", "down")
        ] + ["pt_jer_up", "pt_jer_down"]
        self.uses |= {f"Jet.{c}" for c in self.variation_columns}
