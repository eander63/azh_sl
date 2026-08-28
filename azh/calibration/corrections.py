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
# Type-1 MET propagation must target the collection the analysis actually reads.
# selection/default.py and production/higgs_reco.py use PuppiMET; columnflow's
# jec/jer default to MET (PFMET), so without this the corrections and their
# variations would be written to a branch nothing looks at. Puppi is the default
# jet collection from Run 3 on, which also makes the AN-2022/158 workaround of
# propagating CHS JES uncertainties to PuppiMET (Sec. 9.1, l. 739-745) obsolete.
_met_names = {"met_name": "PuppiMET", "raw_met_name": "RawPuppiMET"}

# Data gets JEC with no uncertainties -- there are none to evaluate.
jec_nominal = jec.derive("jec_nominal", cls_dict={"uncertainty_sources": [], **_met_names})

# MC gets JEC *with* uncertainties. Leaving uncertainty_sources unset (None)
# makes the producer fall back to cfg.x.jec["uncertainty_sources"]
# (columnflow/calibration/cms/jets.py:388-390), so the source list is controlled
# in one place: config_run3.py. Start with ["Total"] for commissioning; the
# AN-2022/158 reduced set of 11 (Sec. 9.1, l. 734-738) is the target for the
# final fit and costs ~22 full Calibrate -> Select -> Reduce passes per dataset.
jec_full = jec.derive("jec_full", cls_dict=dict(_met_names))

# JER, likewise propagated to PuppiMET.
jer_puppi = jer.derive("jer_puppi", cls_dict={"met_name": "PuppiMET"})


@calibrator
def jet_energy(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    Common calibrator for Jet energy corrections, applying nominal JEC for data, and JEC with
    uncertainties plus JER for MC. Information about used and produced columns and dependent
    calibrators is added in a custom init function below.
    """
    if self.dataset_inst.is_mc:
        events = self[jec_full](events, **kwargs)
        events = self[jer_puppi](events, **kwargs)
    else:
        events = self[jec_nominal](events, **kwargs)

    return events


@jet_energy.init
def jet_energy_init(self: Calibrator) -> None:
    # full jec (with uncertainty sources) + jer for mc, nominal-only jec for data
    #
    # NOTE: the JEC/JER shifts are deliberately NOT declared here. They are
    # declared on the selector (azh/selection/default.py), because SelectEvents
    # and ReduceEvents are the tasks that set register_selector_shifts = True and
    # therefore the tasks whose local_shift -- and hence column aliases -- respond
    # to the shift. Declaring them here instead makes CalibrateEvents rerun once
    # per shift for byte-identical output (jec never inspects shift_inst; it
    # writes every Jet.pt_jec_<source>_<dir> column in a single nominal pass)
    # while SelectEvents still reads the unshifted Jet.pt.
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        self.uses |= {jec_full, jer_puppi}
        self.produces |= {jec_full, jer_puppi}
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
# Thin wrapper around the OFFICIAL Muon POG kit
# (modules/muonscarekit/scripts/MuonScaRe.py). The kit reads the same
# muon_scalesmearing.json.gz we already load -- it evaluates a_/m_ (scale),
# poly_params + cb_params + k_ (resolution), and pulls the reproducible
# smearing random number from the file's own RandomSmearing correction. So the
# entire hand-rolled Crystal Ball inverse-CDF and the splitmix64 hash are gone;
# reproducibility and the CB tails are now handled by validated POG code.
#
# The kit is awkward-native (nested=True): pass jagged Muon.* arrays directly,
# no flatten/unflatten. filter_boundaries() (low_pt_threshold=26) and the
# pt_corr/pt sanity cut live inside pt_scale/pt_resol, so we don't re-guard.
# ===========================================================================

@calibrator(
    uses={
        "Muon.pt", "Muon.eta", "Muon.phi", "Muon.charge", "Muon.nTrackerLayers",
        "event", "luminosityBlock",
    },
    produces={"Muon.pt"},
)
def muon_scare(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    pt_scale, pt_resol = self.pt_scale, self.pt_resol   # set in setup
    is_data = self.dataset_inst.is_data

    # scale: applied to data AND MC
    pt_corr = pt_scale(
        is_data,
        events.Muon.pt, events.Muon.eta, events.Muon.phi, events.Muon.charge,
        self.muon_cset, nested=True,
    )
    events = set_ak_column(events, "Muon.pt", pt_corr)

    # resolution smearing: MC only, on the scale-corrected pt
    if not is_data:
        pt_corr = pt_resol(
            events.Muon.pt, events.Muon.eta, events.Muon.phi,
            events.Muon.nTrackerLayers,
            events.event, events.luminosityBlock,
            self.muon_cset, nested=True, rnd_gen="np",
        )
        events = set_ak_column(events, "Muon.pt", pt_corr)

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
    import sys, os, azh
    # repo root = parent of the azh/ package dir; kit lives under modules/
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(azh.__file__)))
    _kit = os.path.join(_repo, "modules", "muonscarekit", "scripts")
    if _kit not in sys.path:
        sys.path.insert(0, _kit)
    from MuonScaRe import pt_scale, pt_resol
    self.pt_scale, self.pt_resol = pt_scale, pt_resol

    import correctionlib
    bundle = reqs["external_files"]
    self.muon_cset = correctionlib.CorrectionSet.from_string(
        bundle.files.muon_scalesmearing.load(formatter="gzip").decode("utf-8"),
    )

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

    # correctionlib raises a bare "IndexError: map::at" for an unknown key, which
    # says nothing about which name failed or what was available. The EGM scale
    # corrections carry era suffixes (EGMScale_ElePTsplit_2022preEE etc.), so a
    # name copied between eras fails here -- report it usefully.
    available = list(cset.keys())
    missing = [n for n in (scale_name, smear_name) if n not in available]
    if missing:
        raise KeyError(
            f"electron S&S correction(s) {missing} not found for config "
            f"'{self.config_inst.name}'. Check cfg.x.electron_ss_names against the "
            f"era's electronSS_EtDependent.json.gz, which provides: {available}",
        )

    self.corr_scale = cset[scale_name]
    self.corr_smear = cset[smear_name]
                        
