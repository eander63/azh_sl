# coding: utf-8

"""
Calibration corrections: value-changing corrections applied before
selection/reduction. This module holds the definitions only; the composite
calibrators that sequence them are in azh/calibration/default.py.

Contents:
  - jec_nominal, jet_energy       nominal JEC (+ JER for MC)
  - jet_lepton_cleaner            remove overlapping-lepton energy from jets
  - muon_scare                    MuonScaRe momentum scale & smearing
  - electron_ss                   EGM electron scale & smearing
"""

from columnflow.calibration import Calibrator, calibrator
from columnflow.calibration.cms.jets import jec, jer
from columnflow.util import maybe_import, InsertableDict
from columnflow.production.util import attach_coffea_behavior
from columnflow.columnar_util import set_ak_column

from azh.util import lv_xyzt, lv_mass

ak = maybe_import("awkward")
np = maybe_import("numpy")

# ===========================================================================
# Jet energy: nominal JEC (+ JER for MC)
# ===========================================================================
jec_nominal = jec.derive("jec_nominal", cls_dict={"uncertainty_sources": []})

@calibrator
def jet_energy(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Common calibrator for Jet energy corrections, applying nominal JEC for data, and JEC with
    uncertainties plus JER for MC. Information about used and produced columns and dependent
    calibrators is added in a custom init function below.
    """
    if self.dataset_inst.is_mc:
        # TODO: for testing purposes, only run jec_nominal for now
        events = self[jec_nominal](events, **kwargs)
        events = self[jer](events, **kwargs)
    else:
        events = self[jec_nominal](events, **kwargs)

    return events


@jet_energy.init
def jet_energy_init(self: Calibrator) -> None:
    # add standard jec and jer for mc, and only jec nominal for dta
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        # TODO: for testing purposes, only run jec_nominal for now
        self.uses |= {jec_nominal, jer}
        self.produces |= {jec_nominal, jer}
    else:
        self.uses |= {jec_nominal}
        self.produces |= {jec_nominal}


# ===========================================================================
# Jet-lepton cleaning
# ===========================================================================
@calibrator(
    uses={
        "Electron.pt", "Electron.eta", "Electron.phi", "Electron.mass",
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.mass",
        "Jet.pt", "Jet.eta", "Jet.phi", "Jet.mass", "Jet.rawFactor",
        # index of electrons/muons matched to jets
        "Jet.muonIdx1", "Jet.muonIdx2", "Jet.electronIdx1", "Jet.electronIdx2",
        # PF energy fractions
        "Jet.chEmEF", "Jet.muEF",
        attach_coffea_behavior,
    },
    produces={
        "Jet.pt", "Jet.eta", "Jet.phi", "Jet.mass", "Jet.rawFactor",
        "Jet.chEmEF", "Jet.muEF",
    },
)
def jet_lepton_cleaner(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Calibrator to clean jet four-vectors from contributions from nearby leptons.
    """
    # load coffea behaviors for simplified arithmetic with vectors
    events["Electron"] = ak.with_name(events.Electron, "PtEtaPhiMLorentzVector")
    events["Muon"] = ak.with_name(events.Muon, "PtEtaPhiMLorentzVector")
    events["Jet"] = ak.with_name(events.Jet, "PtEtaPhiMLorentzVector")

    # revert JEC for jet pt and jet mass, set correction factor to 0
    events = set_ak_column(events, "Jet.pt", events.Jet.pt * (1 - events.Jet.rawFactor))
    events = set_ak_column(events, "Jet.mass", events.Jet.mass * (1 - events.Jet.rawFactor))
    events = set_ak_column(events, "Jet.rawFactor", 0)

    # build jet lorentz vectors
    jet_lv = lv_xyzt(events.Jet)

    # indices of leptons matched to a jet (None if no matched lepton)
    idx_e1 = ak.mask(events.Jet.electronIdx1, events.Jet.electronIdx1 >= 0)
    idx_e2 = ak.mask(events.Jet.electronIdx2, events.Jet.electronIdx2 >= 0)
    idx_m1 = ak.mask(events.Jet.muonIdx1, events.Jet.muonIdx1 >= 0)
    idx_m2 = ak.mask(events.Jet.muonIdx2, events.Jet.muonIdx2 >= 0)

    # list with matched leptons
    jet_leptons_types = [
        (events.Electron[idx_e1], "e"),
        (events.Electron[idx_e2], "e"),
        (events.Muon[idx_m1], "mu"),
        (events.Muon[idx_m2], "mu"),
    ]

    # total energy from clustered leptonic PF candidates
    jet_pf_energies = {
        "mu": jet_lv.energy * events.Jet.muEF,
        "e": jet_lv.energy * events.Jet.chEmEF,
    }
    # subtract lepton contributions from jets
    tolerance = 0.1
    for jet_lepton, jet_lepton_type in jet_leptons_types:
        jet_lepton_lv = lv_xyzt(jet_lepton)
        jet_lv_cleaned = lv_xyzt(jet_lv - jet_lepton_lv)
        jet_pf_energy = jet_pf_energies[jet_lepton_type]
        jet_pf_energy_cleaned = jet_pf_energy - jet_lepton_lv.energy

        # lepton energy compatible with PF energy fraction (within tolerance)
        lep_energy_pf_compatible = (jet_lepton_lv.energy < (1 + tolerance) * jet_pf_energy)

        # square of cleaned jet mass; mask values that would give imaginary
        # masses, but keep abs() if only negative within tolerance (lepton fake)
        jet_lv_cleaned_mass_sq = jet_lv_cleaned.energy**2 - jet_lv_cleaned.rho**2
        jet_lv_cleaned_mass = ak.mask(
            np.sqrt(abs(jet_lv_cleaned_mass_sq)),
            jet_lv_cleaned_mass_sq >= -tolerance,
        )
        # cleaning does not result in a negative/imaginary/undefined mass
        mass_stays_positive = ~ak.is_none(jet_lv_cleaned_mass, axis=1)

        # angle before/after cleaning is similar, OR cleaned pt is very low
        # (high probability that this was a pure lepton fake)
        angle_change_small = (
            (jet_lv.delta_r(jet_lv_cleaned) <= np.pi / 2) |
            (jet_lv_cleaned.pt < 10)
        )

        # AND of cleaning conditions; `None` (no matched lepton) -> no cleaning
        do_clean = mass_stays_positive & angle_change_small & lep_energy_pf_compatible
        do_clean = ak.fill_none(do_clean, False)

        # update jet LV and PF energies where we cleaned
        jet_lv = ak.where(do_clean, jet_lv_cleaned, jet_lv)
        jet_pf_energies[jet_lepton_type] = ak.where(
            do_clean, jet_pf_energy_cleaned, jet_pf_energy,
        )

    # save updated jet variables
    jet_lv = lv_mass(jet_lv)
    for var in ["pt", "eta", "phi", "mass"]:
        value = ak.fill_none(ak.nan_to_none(getattr(jet_lv, var)), 0.0)
        value = ak.where(np.isfinite(value), value, 0)
        events = set_ak_column(events, f"Jet.{var}", value)

    return events


# ===========================================================================
# Muon momentum scale & smearing (MuonScaRe)
#
# TODO(physics, separate step -- triggers reprocess):
#   The file already ships a `RandomSmearing` evaluator (uniform[0,1) keyed on
#   evtNr/lumiNr/phi). Replace the hand-rolled splitmix64 hash below with it,
#   and diff the Crystal Ball inverse-CDF against the official muonscarekit
#   MuonScaRe.py. Names (a/m/k_*, cb_params, poly_params) already match the JSON.
# ===========================================================================

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

        # Crystal Ball random number via inverse CDF.
        # Deterministic uniform[0,1) per muon, hashed from (event, lumi, phi).
        # This replaces the custom "RandomSmearing" correction that used to
        # be bolted onto muon_scalesmearing.json.gz -- the stock POG JSON
        # does not include it. The splitmix64-style hash below is fully
        # vectorized, bit-stable across re-runs, and uniform to ~2%.
        ev_u64 = ak.to_numpy(ak.flatten(
            ak.ones_like(muons.pt, dtype=np.int64) * events.event[:, np.newaxis]
        )).astype(np.uint64)
        lu_u64 = ak.to_numpy(ak.flatten(
            ak.ones_like(muons.pt, dtype=np.int64) * events.luminosityBlock[:, np.newaxis]
        )).astype(np.uint64)
        phi_bits = np.frombuffer(
            np.ascontiguousarray(flat_phi, dtype=np.float64).tobytes(),
            dtype=np.uint64,
        ).copy()
        with np.errstate(over="ignore"):
            _h = (
                ev_u64 * np.uint64(0x9E3779B97F4A7C15)
                + lu_u64 * np.uint64(0xBF58476D1CE4E5B9)
                + phi_bits
            )
            _h ^= _h >> np.uint64(30); _h = _h * np.uint64(0xBF58476D1CE4E5B9)
            _h ^= _h >> np.uint64(27); _h = _h * np.uint64(0x94D049BB133111EB)
            _h ^= _h >> np.uint64(31)
        u = (_h >> np.uint64(11)).astype(np.float64) / float(1 << 53)

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

"""
EGM electron scale & smearing -- eT-dependent flavour (POG-recommended).

Replaces the standard-flavour electron_ss. Applies:
  * data: energy SCALE   -> Electron.pt *= scale
  * MC:   energy SMEARING -> Electron.pt *= (1 + sigma * gaussian)

Key correctness points (all learned from introspecting the real JSONs):

  * Supercluster eta. The corrections are binned in ScEta (or AbsScEta,
    depending on the file version). We compute ScEta = eta + deltaEtaSC and let
    the setup decide, per correction, whether to pass the signed or absolute
    value -- read from the correction's declared inputs, NOT hardcoded, because
    CVMFS and older mirrors disagree on this.

  * eT-dependent entry point. The file ships many EGMScale_*/EGMSmearAndSyst_*
    components; the two that return the final applied numbers are the
    'ElePTsplit' ones, selected via the syst string ("scale" / "smear").

  * Reproducible smearing. The Gaussian is seeded per-electron from
    (event, object index), so re-running -- at any chunk size -- reproduces the
    same smeared pt. (The old code seeded once per chunk, which was not
    reproducible.)

  * <15 GeV guard. The POG states S&S is untuned below ~15 GeV; electrons below
    that (our loose floor is 10) are passed through uncorrected.
"""

# S&S not tuned below this pt (EGM recommendation)
SS_PT_MIN = 15.0


def _build_args(corr, syst, pt, r9, sceta):
    """
    Build the evaluate() argument tuple by reading the correction's declared
    inputs, so we pass signed ScEta or AbsScEta as required and tolerate file
    version differences. First input is always the syst string.
    """
    values = {"pt": pt, "r9": r9, "ScEta": sceta, "AbsScEta": np.abs(sceta)}
    args = [syst]
    for inp in corr.inputs[1:]:
        if inp.name not in values:
            raise KeyError(
                f"electron_ss: correction '{corr.name}' declares unexpected "
                f"input '{inp.name}' (known: {sorted(values)})",
            )
        args.append(values[inp.name])
    return tuple(args)


@calibrator(
    uses={
        "Electron.pt", "Electron.eta", "Electron.deltaEtaSC", "Electron.r9",
        "event",
    },
    produces={"Electron.pt"},
)
def electron_ss(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    ele = events.Electron
    counts = ak.num(ele.pt, axis=1)

    flat_pt = ak.to_numpy(ak.flatten(ele.pt)).astype(np.float64)
    flat_r9 = ak.to_numpy(ak.flatten(ele.r9)).astype(np.float64)
    flat_sceta = ak.to_numpy(ak.flatten(ele.eta + ele.deltaEtaSC)).astype(np.float64)

    # only correct electrons above the S&S validity floor
    do_corr = flat_pt >= SS_PT_MIN
    corrected = flat_pt.copy()

    if self.dataset_inst.is_data:
        args = _build_args(
            self.corr_scale, "scale",
            flat_pt[do_corr], flat_r9[do_corr], flat_sceta[do_corr],
        )
        scale = self.corr_scale.evaluate(*args)
        corrected[do_corr] = flat_pt[do_corr] * scale
    else:
        args = _build_args(
            self.corr_smear, "smear",
            flat_pt[do_corr], flat_r9[do_corr], flat_sceta[do_corr],
        )
        sigma = self.corr_smear.evaluate(*args)

        # reproducible per-electron gaussian, seeded from (event, object index)
        event_per_ele = ak.to_numpy(ak.flatten(
            ak.broadcast_arrays(events.event, ele.pt)[0],
        )).astype(np.uint64)
        obj_idx = ak.to_numpy(ak.flatten(ak.local_index(ele.pt, axis=1))).astype(np.uint64)
        seeds = (event_per_ele * np.uint64(2654435761) + obj_idx)[do_corr]

        gauss = np.empty(do_corr.sum(), dtype=np.float64)
        for i, sd in enumerate(seeds):
            gauss[i] = np.random.default_rng(sd).standard_normal()

        corrected[do_corr] = flat_pt[do_corr] * (1.0 + sigma * gauss)

    corrected = np.maximum(corrected, 0.0).astype(np.float32)
    events = set_ak_column(events, "Electron.pt", ak.unflatten(corrected, counts))
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
    import correctionlib
    bundle = reqs["external_files"]
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.electron_ss.load(formatter="gzip").decode("utf-8"),
    )
    scale_name, smear_name = self.config_inst.x.electron_ss_names
    self.corr_scale = cset[scale_name]
    self.corr_smear = cset[smear_name]
                        
