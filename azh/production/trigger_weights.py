"""
Event-level trigger scale factor for the single-lepton OR (IsoMu24 || Ele30).

Recipe (standard for multi-lepton final states, needs POG efficiencies, not
only SFs). With the per-lepton efficiencies of the path its flavour fires,

    P(event fires) = 1 - prod_i (1 - eps_i)

    SF_event = [1 - prod_i (1 - eps_data,i)] / [1 - prod_i (1 - eps_MC,i)]

over the selected tight leptons. Electrons use Electron-HLT-DataEff/-McEff
(path HLT_SF_Ele30_MVAiso80ID), muons the *_DATAeff/*_MCeff values of
NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight. Both POGs' DataEff/McEff ratios
reproduce their published SFs exactly (checked at several points, 2022 and 2024).

Leptons below the lower pT edge of the efficiency binning (25 GeV e, 26 GeV mu)
get eps = 0 in data and MC, so they contribute a factor 1.

Uncertainties reuse the POGs' validated SF uncertainties: the data efficiency is
varied as eps_data,var = eps_MC * SF_var (clipped to [0, 1]).
  * trigger_weight_e_trig_{up,down}:   EGM sfup / sfdown
  * trigger_weight_mu_trig_stat_*:     MUO nominal +- stat
  * trigger_weight_mu_trig_syst_*:     MUO nominal +- syst
(MUO's "systup" is NOT the combined uncertainty for this correction -- it
equals the nominal where syst = 0 -- so the stat and syst keys are used.)
"""

from columnflow.columnar_util import set_ak_column
from columnflow.production import Producer, producer
from law.util import InsertableDict
from columnflow.util import maybe_import

np = maybe_import("numpy")
ak = maybe_import("awkward")

E_PT_RANGE = (25.0, 499.9)   # EGM HLT efficiency binning, flow = error
MU_PT_RANGE = (26.0, 199.9)  # MUO IsoMu24 efficiency binning, flow = error
MU_ETA_MAX = 2.399           # MUO binning is signed eta in [-2.4, 2.4]

VARIATIONS = ("e_trig", "mu_trig_stat", "mu_trig_syst")


def _event_prob(eps: ak.Array) -> ak.Array:
    """P(at least one lepton fires) from jagged per-lepton efficiencies."""
    return 1.0 - ak.prod(1.0 - eps, axis=1)


@producer(
    uses={
        "Electron.{pt,eta,deltaEtaSC,mvaIso_WP80}",
        "Muon.{pt,eta,tightId,pfRelIso04_all}",
    },
    produces={
        "trigger_weight",
        *{f"trigger_weight_{v}_{d}" for v in VARIATIONS for d in ("up", "down")},
    },
    mc_only=True,
)
def trigger_weights(self: Producer, events: ak.Array, **kwargs) -> ak.Array:
    ele = events.Electron[events.Electron.mvaIso_WP80]
    mu = events.Muon[events.Muon.tightId & (events.Muon.pfRelIso04_all < 0.15)]

    # --- electrons -------------------------------------------------------
    e_eta = ele.eta + ele.deltaEtaSC if self.use_sc_eta else ele.eta
    e_counts = ak.num(ele.pt)
    e_pt = ak.to_numpy(ak.flatten(ele.pt)).astype(np.float64)
    e_eta = ak.to_numpy(ak.flatten(e_eta)).astype(np.float64)
    e_ok = e_pt >= E_PT_RANGE[0]
    e_ptc = np.clip(e_pt, *E_PT_RANGE)

    year, path = self.ele_year, self.ele_path

    def e_eval(corr, valtype):
        out = np.zeros_like(e_pt)
        if e_ok.any():
            out[e_ok] = corr.evaluate(year, valtype, path, e_eta[e_ok], e_ptc[e_ok])
        return out

    e_eff_mc = e_eval(self.ele_eff_mc, "nom")
    e_eff_data = e_eval(self.ele_eff_data, "nom")
    e_sf = {d: e_eval(self.ele_sf, f"sf{d}") for d in ("up", "down")}

    # --- muons -----------------------------------------------------------
    m_counts = ak.num(mu.pt)
    m_pt = ak.to_numpy(ak.flatten(mu.pt)).astype(np.float64)
    m_eta = np.clip(ak.to_numpy(ak.flatten(mu.eta)).astype(np.float64), -MU_ETA_MAX, MU_ETA_MAX)
    m_ok = m_pt >= MU_PT_RANGE[0]
    m_ptc = np.clip(m_pt, *MU_PT_RANGE)

    def m_eval(key):
        out = np.zeros_like(m_pt)
        if m_ok.any():
            out[m_ok] = self.mu_corr.evaluate(m_eta[m_ok], m_ptc[m_ok], key)
        return out

    m_eff_mc = m_eval("nominal_MCeff")
    m_eff_data = m_eval("nominal_DATAeff")
    m_sf = m_eval("nominal")
    m_stat = m_eval("stat")
    m_syst = m_eval("syst")

    # --- combine -----------------------------------------------------------
    def jag(e_vals, m_vals):
        return ak.concatenate([ak.unflatten(e_vals, e_counts), ak.unflatten(m_vals, m_counts)], axis=1)

    p_mc = _event_prob(jag(e_eff_mc, m_eff_mc))

    def event_sf(e_data, m_data):
        p_data = _event_prob(jag(np.clip(e_data, 0.0, 1.0), np.clip(m_data, 0.0, 1.0)))
        return ak.where(p_mc > 0, p_data / ak.where(p_mc > 0, p_mc, 1.0), 1.0)

    out = {"trigger_weight": event_sf(e_eff_data, m_eff_data)}
    for d, sign in (("up", 1.0), ("down", -1.0)):
        out[f"trigger_weight_e_trig_{d}"] = event_sf(e_eff_mc * e_sf[d], m_eff_data)
        out[f"trigger_weight_mu_trig_stat_{d}"] = event_sf(e_eff_data, m_eff_mc * (m_sf + sign * m_stat))
        out[f"trigger_weight_mu_trig_syst_{d}"] = event_sf(e_eff_data, m_eff_mc * (m_sf + sign * m_syst))

    for name, values in out.items():
        events = set_ak_column(events, name, ak.values_astype(values, np.float32))
    return events


@trigger_weights.requires
def trigger_weights_requires(self: Producer, task, reqs: dict, **kwargs) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(task)


@trigger_weights.setup
def trigger_weights_setup(
    self: Producer,
    task,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
    **kwargs,
) -> None:
    import correctionlib

    bundle = reqs["external_files"]

    cset_mu = correctionlib.CorrectionSet.from_string(
        bundle.files.muon_sf.load(formatter="gzip").decode("utf-8"),
    )
    self.mu_corr = cset_mu[self.config_inst.x.muon_sf_trig_names[0]]

    cset_e = correctionlib.CorrectionSet.from_string(
        bundle.files.electron_sf_hlt.load(formatter="gzip").decode("utf-8"),
    )
    sf_name, self.ele_year, self.ele_path = self.config_inst.x.electron_sf_trig_names
    self.ele_sf = cset_e[sf_name]
    self.ele_eff_data = cset_e["Electron-HLT-DataEff"]
    self.ele_eff_mc = cset_e["Electron-HLT-McEff"]

    # EGM's HLT file documents its input as "electron eta"; the other EGM SFs
    # are binned in supercluster eta. Configurable until EGM confirms.
    self.use_sc_eta = self.config_inst.x("electron_hlt_use_sc_eta", True)
