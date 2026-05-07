from columnflow.calibration import Calibrator, calibrator
from columnflow.calibration.cms.jets import jets
from columnflow.production.cms.mc_weight import mc_weight
from columnflow.production.cms.seeds import deterministic_seeds
from columnflow.util import maybe_import, InsertableDict
from columnflow.columnar_util import set_ak_column

from azh.calibration.jets import jet_energy, jet_lepton_cleaner

ak = maybe_import("awkward")
np = maybe_import("numpy")


@calibrator(
    uses={mc_weight, deterministic_seeds, jets},
    produces={mc_weight, deterministic_seeds, jets},
)
def default(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
    events = self[deterministic_seeds](events, **kwargs)
    events = self[jets](events, **kwargs)

    return events


# ---------------------------------------------------------------------------
# MuonScaRe (Rochester-like) momentum scale & smearing calibrator
#
# Data:  pt_corr = (pt + a_data) * m_data
# MC:    pt_corr = (pt + a_mc)   * m_mc,  then extra gaussian smearing
#        using k_mc and the Crystal Ball sigma from cb_params/poly_params.
#
# JSON: muon_scalesmearing.json.gz
# Evaluators: m_data, a_data, m_mc, a_mc, k_data, k_mc, cb_params, poly_params
# ---------------------------------------------------------------------------
@calibrator(
    uses={
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.charge",
        "Muon.nTrackerLayers", "event", "luminosityBlock",
    },
    produces={"Muon.pt"},
)
def muon_scare(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Apply MuonScaRe momentum scale and smearing corrections.
    Official MuonPOG formula from muonscarekit:
      Scale: pt_corr = 1 / (M/pt + charge*A)  [applied to data AND MC]
      Resol: pt_corr = pt * (1 + k * sigma * cb_rndm)  [MC only]
    """
    from scipy.special import erfinv, erf

    muons = events.Muon
    flat_pt     = ak.to_numpy(ak.flatten(muons.pt))
    flat_eta    = ak.to_numpy(ak.flatten(muons.eta))
    flat_phi    = ak.to_numpy(ak.flatten(muons.phi))
    flat_charge = ak.to_numpy(ak.flatten(muons.charge))
    counts      = ak.num(muons.pt, axis=1)

    # --- Scale correction (data AND MC) ---
    dtmc = "data" if self.dataset_inst.is_data else "mc"
    m = self.corr_sets["m_" + dtmc].evaluate(flat_eta, flat_phi, "nom")
    a = self.corr_sets["a_" + dtmc].evaluate(flat_eta, flat_phi, "nom")

    corrected_pt = 1.0 / (m / flat_pt + flat_charge * a)

    # --- Resolution smearing (MC only) ---
    if self.dataset_inst.is_mc:
        flat_nl = ak.to_numpy(ak.flatten(muons.nTrackerLayers)).astype(np.float64)
        flat_abseta = np.abs(flat_eta)

        # Extra smearing factor k = sqrt(k_data^2 - k_mc^2) if k_data > k_mc, else 0
        k_data = self.corr_sets["k_data"].evaluate(flat_abseta, "nom")
        k_mc   = self.corr_sets["k_mc"].evaluate(flat_abseta, "nom")
        k = np.where(k_mc < k_data, np.sqrt(k_data**2 - k_mc**2), 0.0)

        # Resolution sigma = poly(pt): p0 + p1*pt + p2*pt^2
        p0 = self.corr_sets["poly_params"].evaluate(flat_abseta, flat_nl, 0)
        p1 = self.corr_sets["poly_params"].evaluate(flat_abseta, flat_nl, 1)
        p2 = self.corr_sets["poly_params"].evaluate(flat_abseta, flat_nl, 2)
        sigma = np.maximum(p0 + p1 * corrected_pt + p2 * corrected_pt**2, 0.0)

        # Crystal Ball random number via inverse CDF
        # Get uniform random from RandomSmearing evaluator (deterministic)
        evt_flat = ak.to_numpy(ak.flatten(
            ak.ones_like(muons.pt, dtype=np.int64) * events.event[:, np.newaxis]
        )).astype(np.float64)
        lumi_flat = ak.to_numpy(ak.flatten(
            ak.ones_like(muons.pt, dtype=np.int64) * events.luminosityBlock[:, np.newaxis]
        )).astype(np.float64)
        u = self.corr_sets["RandomSmearing"].evaluate(evt_flat, lumi_flat, flat_phi)

        # CB parameters
        cb_mean  = self.corr_sets["cb_params"].evaluate(flat_abseta, flat_nl, 0)
        cb_sigma = self.corr_sets["cb_params"].evaluate(flat_abseta, flat_nl, 1)
        cb_n     = self.corr_sets["cb_params"].evaluate(flat_abseta, flat_nl, 2)
        cb_alpha = self.corr_sets["cb_params"].evaluate(flat_abseta, flat_nl, 3)

        # Crystal Ball inverse CDF
        fa = np.abs(cb_alpha)
        sqrtPiOver2 = np.sqrt(np.pi / 2.0)
        sqrt2 = np.sqrt(2.0)
        ex = np.exp(-fa * fa / 2)
        n_cb = cb_n
        A_cb = (n_cb / fa) ** n_cb * ex
        C1 = n_cb / fa / (n_cb - 1) * ex
        D1 = 2 * sqrtPiOver2 * erf(fa / sqrt2)
        N_cb = 1.0 / cb_sigma / (D1 + 2 * C1)
        Ns = N_cb * cb_sigma
        NC = Ns * C1
        B_cb = n_cb / fa - fa
        C_tot = (D1 + 2 * C1) / C1
        D_tot = (D1 + 2 * C1) / 2
        F_cb = 1 - fa * fa / n_cb
        G_cb = cb_sigma * n_cb / fa
        k_cb = 1.0 / (n_cb - 1)

        cdfMa = NC  # CDF at m - alpha*s (simplified)
        cdfPa = NC * C_tot - NC  # CDF at m + alpha*s (simplified)

        # Compute CDF at m-a*s and m+a*s properly
        # d = -alpha => cdf region 1
        cdfMa = NC / np.power(np.maximum(F_cb - cb_sigma * (-fa) / G_cb, 1e-10), n_cb - 1)
        # d = +alpha => cdf region 2
        cdfPa = NC * (C_tot - np.power(np.maximum(F_cb + cb_sigma * fa / G_cb, 1e-10), 1 - n_cb))

        # Inverse CDF
        c1 = u < cdfMa
        c2 = u > cdfPa
        c3 = ~c1 & ~c2

        rndm = np.zeros_like(u)
        # u < cdfMa (left tail)
        safe_ratio1 = np.maximum(NC / np.where(c1, u, 1.0), 1e-10)
        rndm = np.where(c1, cb_mean + G_cb * (F_cb - safe_ratio1 ** k_cb), rndm)
        # u > cdfPa (right tail)
        safe_ratio2 = np.maximum(C_tot - np.where(c2, u, 0.0) / NC, 1e-10)
        rndm = np.where(c2, cb_mean - G_cb * (F_cb - safe_ratio2 ** (-k_cb)), rndm)
        # cdfMa <= u <= cdfPa (core gaussian)
        rndm = np.where(c3, cb_mean - sqrt2 * cb_sigma * erfinv((D_tot - u / Ns) / sqrtPiOver2), rndm)

        # Apply smearing
        corrected_pt = corrected_pt * (1.0 + k * sigma * rndm)

    # Boundary protection: only correct 26 < pt < 200 GeV
    corrected_pt = np.where(flat_pt > 200, flat_pt, corrected_pt)
    corrected_pt = np.where(flat_pt < 26, flat_pt, corrected_pt)
    # Sanity: reject wild corrections
    ratio = corrected_pt / flat_pt
    corrected_pt = np.where((ratio > 2) | (ratio < 0.1) | (corrected_pt < 0), flat_pt, corrected_pt)
    corrected_pt = np.where(np.isnan(corrected_pt), flat_pt, corrected_pt)

    events = set_ak_column(events, "Muon.pt",
                           ak.unflatten(corrected_pt.astype(np.float32), counts))
    return events


@muon_scare.requires
def muon_scare_requires(self: Calibrator, reqs: dict) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(self.task)


@muon_scare.setup
def muon_scare_setup(self: Calibrator, reqs: dict, inputs: dict,
                     reader_targets: InsertableDict) -> None:
    bundle = reqs["external_files"]
    import correctionlib
    correctionlib.highlevel.Correction.__call__ = correctionlib.highlevel.Correction.evaluate
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.muon_scalesmearing.load(formatter="gzip").decode("utf-8"),
    )
    self.corr_sets = {name: cset[name] for name in cset}


# ---------------------------------------------------------------------------
# EGM electron scale (data) & smearing (MC) calibrator
#
# Data:  pt_corr = pt * Scale(valtype, gain, run, eta, r9, et)
# MC:    sigma = Smearing(valtype, eta, r9)
#        pt_corr = pt * (1 + sigma * gauss)
#
# JSON: electronSS.json.gz
# Evaluators: Scale, Smearing
# ---------------------------------------------------------------------------
@calibrator(
    uses={
        "Electron.pt", "Electron.eta", "Electron.r9",
        "Electron.seedGain", "run",
    },
    produces={"Electron.pt"},
)
def electron_ss(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Apply EGM electron scale (data) and extra smearing (MC).
    Fixes ee channel mass tilt and resolution.
    """
    ele = events.Electron
    flat_pt   = ak.to_numpy(ak.flatten(ele.pt))
    flat_eta  = ak.to_numpy(ak.flatten(ele.eta))
    flat_r9   = ak.to_numpy(ak.flatten(ele.r9))
    flat_gain = ak.to_numpy(ak.flatten(ele.seedGain)).astype(np.int32)
    counts    = ak.num(ele.pt, axis=1)

    if self.dataset_inst.is_data:
        # broadcast run number to per-electron
        run_per_event = ak.to_numpy(events.run).astype(np.float64)
        flat_run = ak.to_numpy(ak.flatten(
            ak.ones_like(ele.pt) * run_per_event[:, np.newaxis],
        ))

        scale = self.corr_scale.evaluate(
            "total_correction", flat_gain, flat_run, flat_eta, flat_r9, flat_pt,
        )
        corrected_pt = flat_pt * scale
    else:
        # MC: smearing
        sigma = self.corr_smearing.evaluate("rho", flat_eta, flat_r9)
        rng = np.random.default_rng(
            seed=int(ak.sum(events.event[:100])) % 2**31 + 1,
        )
        u = rng.normal(0.0, 1.0, size=len(flat_pt))
        corrected_pt = flat_pt * (1.0 + sigma * u)

    corrected_pt = np.maximum(corrected_pt, 0.0).astype(np.float32)
    events = set_ak_column(events, "Electron.pt",
                           ak.unflatten(corrected_pt, counts))
    return events


@electron_ss.requires
def electron_ss_requires(self: Calibrator, reqs: dict) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(self.task)


@electron_ss.setup
def electron_ss_setup(self: Calibrator, reqs: dict, inputs: dict,
                      reader_targets: InsertableDict) -> None:
    bundle = reqs["external_files"]
    import correctionlib
    correctionlib.highlevel.Correction.__call__ = correctionlib.highlevel.Correction.evaluate
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.electron_ss.load(formatter="gzip").decode("utf-8"),
    )
    self.corr_scale    = cset["Scale"]
    self.corr_smearing = cset["Smearing"]


# ---------------------------------------------------------------------------
# Composite calibrators
# ---------------------------------------------------------------------------
@calibrator(
    uses={mc_weight, deterministic_seeds, jet_lepton_cleaner, jet_energy, muon_scare, electron_ss},
    produces={mc_weight, deterministic_seeds, jet_lepton_cleaner, jet_energy, muon_scare, electron_ss},
)
def skip_jecunc(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """ only uses jec_nominal for test purposes """
    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
        events = self[deterministic_seeds](events, **kwargs)
    events = self[jet_lepton_cleaner](events, **kwargs)
    events = self[jet_energy](events, **kwargs)
    events = self[muon_scare](events, **kwargs)
    events = self[electron_ss](events, **kwargs)

    return events


@calibrator(
    uses={mc_weight, deterministic_seeds, jet_energy},
    produces={mc_weight, deterministic_seeds, jet_energy},
)
def skip_jecunc_wo_cleaner(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """ only uses jec_nominal for test purposes """
    if self.dataset_inst.is_mc:
        events = self[mc_weight](events, **kwargs)
    events = self[deterministic_seeds](events, **kwargs)
    events = self[jet_energy](events, **kwargs)

    return events
