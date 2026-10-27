"""
Calibration corrections: value-changing corrections applied before
selection/reduction. This module holds the definitions only; the composite
calibrators that sequence them are in azh/calibration/default.py.

Contents:
  - jec_nominal, jec_full, jet_energy   JEC (+ JER for MC), CandJet collection
  - ecal_badcrystal_veto                JME prompt-reco ECAL crystal veto (data)
  - jet_id_v15                          Jet.jetId bitmap for NanoAOD v15
  - met_unclustered_capture / _apply    PuppiMET unclustered-energy variation
  - muon_scare                          MuonScaRe momentum scale & smearing
  - electron_ss                         EGM electron scale & smearing

Jet-lepton overlap is handled by Delta R < 0.3 removal in
selection/jet_selection.py (AN-2022/158 Sec. 4.4); the former lepton-subtraction
cleaner rewrote the raw jets that Type-1 MET is rebuilt from, which JME calls
non-standard.
"""

from columnflow.calibration import Calibrator, calibrator
from columnflow.calibration.cms.jets import jec, jer
from columnflow.columnar_util import set_ak_column
from law.util import InsertableDict
from columnflow.util import maybe_import

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
# makes the producer fall back to cfg.x.jec's "uncertainty_sources", so the
# source list is controlled in one place: config_run3.py (the full set of 27
# independent sources, which reproduces Total in quadrature in every era).
# The JES/JER shifts are production-level (see production/default.py).
jec_full = jec.derive("jec_full", cls_dict=dict(_met_names))

# JER, likewise propagated to PuppiMET.
jer_puppi = jer.derive("jer_puppi", cls_dict={"met_name": "PuppiMET"})


# ---------------------------------------------------------------------------
# Candidate jets (CandJet) carrying the JES / JER variations
# ---------------------------------------------------------------------------
# columnflow's jec/jer write every JES/JER variation for every jet of every
# event; for MC that made the calibration output larger than the NanoAOD input
# (1-3 GB per file) and needed 7-11 GB of memory. Here the variations are
# computed exactly as before (vary, then smear), but only kept for
#   * events that can pass the preselection: >= 2 electrons + muons with
#     NanoAOD pt > 8 GeV (any ID; a strict superset of the 10 GeV lepton floor
#     including the scale/smearing corrections and their variations; the
#     selector raises if a selected event was not flagged), and
#   * jets that can be analysis jets: |eta| < 2.5, TightLepVeto, pT > 30 GeV in
#     the nominal or ANY variation.
# They are stored in a separate CandJet collection (index into Jet, nominal and
# varied pT, eta, phi, mass, b-tag score, hadron flavour). The varied mass is not
# stored: a JES/JER shift scales pT and mass by the same factor, so production
# rebuilds it as mass * pt / pt_nominal. The full Jet collection keeps only its
# nominal calibrated values (used e.g. by the jet veto map); the MET variations
# stay event-level and are computed from all jets, as before.
CANDJET_ETA_MAX = 2.5
CANDJET_PT_MIN = 30.0
PRESEL_LEPTON_PT = 8.0
# nominal Jet columns written by columnflow's jec/jer that are kept for the full
# Jet collection (check against columnflow's jec produces if it changes)
JET_NOMINAL_COLUMNS = ("pt", "mass", "rawFactor")


def jes_jer_postfixes(config_inst) -> list:
    """Column postfixes of the JES/JER variations, e.g. jec_Regrouped_Absolute_up."""
    return [
        f"jec_{src}_{d}" for src in config_inst.x.jec.Jet.uncertainty_sources for d in ("up", "down")
    ] + ["jer_up", "jer_down"]


@calibrator
def jet_energy(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """
    JEC (nominal for data; with the configured uncertainty sources for MC), JER
    for MC, then the CandJet collection (see above).
    """
    if self.dataset_inst.is_mc:
        events = self[jec_full](events, **kwargs)
        events = self[jer_puppi](events, **kwargs)
    else:
        events = self[jec_nominal](events, **kwargs)

    jet = events.Jet
    n_lep = (
        ak.sum(events.Electron["pt"] > PRESEL_LEPTON_PT, axis=1) +
        ak.sum(events.Muon["pt"] > PRESEL_LEPTON_PT, axis=1)
    )
    presel = n_lep >= 2

    var_cols = [f"pt_{p}" for p in self.variation_postfixes]
    pt_max = jet["pt"]
    for col in var_cols:
        pt_max = np.maximum(pt_max, jet[col])
    cand = (
        (abs(jet["eta"]) < CANDJET_ETA_MAX) &
        ((jet["jetId"] & 0b110) == 0b110) &
        (pt_max > CANDJET_PT_MIN) &
        presel
    )
    cand = ak.fill_none(cand, False)

    events = set_ak_column(events, "CandJet.index", ak.local_index(jet["pt"], axis=1)[cand])
    for f in self.cand_fields:
        events = set_ak_column(events, f"CandJet.{f}", jet[f][cand])
    events = set_ak_column(events, "CandJet.pt_nominal", jet["pt"][cand])
    for col in var_cols:
        events = set_ak_column(events, f"CandJet.{col}", jet[col][cand])
    events = set_ak_column(events, "jet_presel", ak.fill_none(presel, False))
    return events


@jet_energy.init
def jet_energy_init(
    self: Calibrator,
    **kwargs,
) -> None:
    # The JES/JER shifts are declared on the producer (production/default.py);
    # this calibrator only computes the varied columns in the nominal pass.
    cfg = self.config_inst
    btag_col = cfg.x.btag_default.column
    is_mc = bool(getattr(self, "dataset_inst", None)) and self.dataset_inst.is_mc

    self.cand_fields = ["pt", "eta", "phi", "mass", btag_col] + (["hadronFlavour"] if is_mc else [])
    self.variation_postfixes = jes_jer_postfixes(cfg) if is_mc else []

    self.uses |= {"Jet.{eta,phi,jetId}", f"Jet.{btag_col}", "Electron.pt", "Muon.pt"}
    if is_mc:
        self.uses |= {"Jet.hadronFlavour", jec_full, jer_puppi}
        # write only the nominal Jet columns and the event-level MET variations;
        # jec_full / jer_puppi are deliberately NOT in produces, otherwise all
        # their per-jet variation columns would be written as well
        self.produces |= {f"Jet.{c}" for c in JET_NOMINAL_COLUMNS}
        self.produces |= {"PuppiMET.pt", "PuppiMET.phi"}
        self.produces |= {f"PuppiMET.{v}_{p}" for v in ("pt", "phi") for p in self.variation_postfixes}
    else:
        self.uses |= {jec_nominal}
        self.produces |= {jec_nominal}

    self.produces |= {f"CandJet.{f}" for f in self.cand_fields + ["index", "pt_nominal"]}
    self.produces |= {f"CandJet.pt_{p}" for p in self.variation_postfixes}
    self.produces.add("jet_presel")


# ===========================================================================
# 2022-2023 prompt-reco ECAL bad crystal (JME MET-filter recommendation)
# ===========================================================================
# The 22Sep2023 2022G / 2023C datasets used here are re-NANOs of prompt reco
# (DAS parentage: ...-PromptReco-v1/AOD), so the recipe applies. For data in
# runs 362433-367144 the stored Flag_ecalBadCalibFilter must not be used;
# instead reject the event if PuppiMET_pt > 100 GeV and at least one AK4 jet
# (no jet ID) has pt > 50, -0.5 < eta < -0.1, -2.1 < phi < -1.8 and
# (neEmEF > 0.9 or chEmEF > 0.9). Data only; JME quotes < 0.2% loss.
#
# The recipe is defined on the NanoAOD values, which jet_energy overwrites, so
# this calibrator runs FIRST and stores only the decision.
ECAL_BADCRYSTAL_RUNS = (362433, 367144)


@calibrator(
    uses={"run", "PuppiMET.pt", "Jet.{pt,eta,phi,neEmEF,chEmEF}"},
    produces={"ecal_badcrystal_veto"},
)
def ecal_badcrystal_veto(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    """True for data events to reject; False everywhere else."""
    lo, hi = ECAL_BADCRYSTAL_RUNS
    jet = events.Jet
    bad_jet = (
        (jet["pt"] > 50) &
        (jet["eta"] > -0.5) & (jet["eta"] < -0.1) &
        (jet["phi"] > -2.1) & (jet["phi"] < -1.8) &
        ((jet["neEmEF"] > 0.9) | (jet["chEmEF"] > 0.9))
    )
    veto = (
        (events.run >= lo) & (events.run <= hi) &
        (events.PuppiMET["pt"] > 100) &
        ak.any(bad_jet, axis=1)
    )
    return set_ak_column(events, "ecal_badcrystal_veto", ak.fill_none(veto, False))


# ===========================================================================
# Jet ID for NanoAOD v15 (2024)
# ===========================================================================
# v15 dropped Jet_jetId. Rebuild the v12 bitmap from the JME jetid.json payload
# (bit 1 = tight, bit 2 = tight lepton veto), so that columnflow's jet_veto_map
# (which reads Jet.jetId) and jet_selection use one definition in every era.
JET_ID_INPUTS = ["eta", "chHEF", "neHEF", "chEmEF", "neEmEF", "muEF", "chMultiplicity", "neMultiplicity"]


@calibrator(
    uses={f"Jet.{f}" for f in JET_ID_INPUTS},
    produces={"Jet.jetId"},
)
def jet_id_v15(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    jet = events.Jet
    counts = ak.num(jet["eta"])
    flat = {f: ak.to_numpy(ak.flatten(jet[f])) for f in JET_ID_INPUTS}
    flat["multiplicity"] = flat["chMultiplicity"] + flat["neMultiplicity"]

    def evaluate(corr):
        # match the payload's declared inputs by name rather than by position
        args = [flat[i.name] for i in corr.inputs]
        return np.asarray(corr.evaluate(*args)) > 0.5

    tight = evaluate(self.corr_tight)
    lepveto = tight & evaluate(self.corr_lepveto)
    jet_id = (2 * tight + 4 * lepveto).astype(np.int32)
    return set_ak_column(events, "Jet.jetId", ak.unflatten(jet_id, counts))


@jet_id_v15.requires
def jet_id_v15_requires(self: Calibrator, task, reqs: dict, **kwargs) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles
    reqs["external_files"] = BundleExternalFiles.req(task)


@jet_id_v15.setup
def jet_id_v15_setup(self: Calibrator, task, reqs: dict, inputs: dict, reader_targets: InsertableDict, **kwargs) -> None:
    import correctionlib
    cset = correctionlib.CorrectionSet.from_string(
        reqs["external_files"].files.jet_id.load(formatter="gzip").decode("utf-8"),
    )
    jid = self.config_inst.x.jet_id
    self.corr_tight = cset[jid.tight]
    self.corr_lepveto = cset[jid.tight_lepveto]
    unknown = {i.name for c in (self.corr_tight, self.corr_lepveto) for i in c.inputs} - set(JET_ID_INPUTS) - {"multiplicity"}
    if unknown:
        raise KeyError(f"jet ID payload declares unexpected inputs {sorted(unknown)}")


# ===========================================================================
# MET unclustered-energy variation (NanoAOD PuppiMET_*Unclustered*)
# ===========================================================================
# NanoAOD provides the unclustered variation relative to its own PuppiMET. The
# calibrator recomputes PuppiMET with newer JECs, so the variation is carried
# over as a vector difference: capture (dx, dy) = unclustered - nominal on the
# NanoAOD values BEFORE jet_energy, add it to the recalibrated MET AFTER.


@calibrator(
    uses={"PuppiMET.{pt,phi,ptUnclusteredUp,phiUnclusteredUp,ptUnclusteredDown,phiUnclusteredDown}"},
    produces={f"PuppiMET.{c}_unclustered_{d}" for c in ("dx", "dy") for d in ("up", "down")},
    mc_only=True,
)
def met_unclustered_capture(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    met = events.PuppiMET
    px, py = met["pt"] * np.cos(met["phi"]), met["pt"] * np.sin(met["phi"])
    for d, D in (("up", "Up"), ("down", "Down")):
        pt_v, phi_v = met[f"ptUnclustered{D}"], met[f"phiUnclustered{D}"]
        # NanoAOD has non-finite unclustered values in some events; those get
        # no unclustered variation (delta 0) instead of failing CalibrateEvents
        dx = np.nan_to_num(pt_v * np.cos(phi_v) - px, nan=0.0, posinf=0.0, neginf=0.0)
        dy = np.nan_to_num(pt_v * np.sin(phi_v) - py, nan=0.0, posinf=0.0, neginf=0.0)
        events = set_ak_column(events, f"PuppiMET.dx_unclustered_{d}", dx)
        events = set_ak_column(events, f"PuppiMET.dy_unclustered_{d}", dy)
    return events


@calibrator(
    uses={"PuppiMET.{pt,phi}", *{f"PuppiMET.{c}_unclustered_{d}" for c in ("dx", "dy") for d in ("up", "down")}},
    produces={f"PuppiMET.{c}_unclustered_{d}" for c in ("pt", "phi") for d in ("up", "down")},
    mc_only=True,
)
def met_unclustered_apply(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    met = events.PuppiMET
    px, py = met["pt"] * np.cos(met["phi"]), met["pt"] * np.sin(met["phi"])
    for d in ("up", "down"):
        vx = px + met[f"dx_unclustered_{d}"]
        vy = py + met[f"dy_unclustered_{d}"]
        events = set_ak_column(events, f"PuppiMET.pt_unclustered_{d}", np.sqrt(vx ** 2 + vy ** 2))
        events = set_ak_column(events, f"PuppiMET.phi_unclustered_{d}", np.arctan2(vy, vx))
    return events


# ===========================================================================
# Muon momentum scale & smearing (MuonScaRe)
#
# Thin wrapper around the OFFICIAL Muon POG kit
# (modules/muonscarekit/scripts/MuonScaRe.py). The kit reads the same
# muon_scalesmearing.json.gz we already load -- it evaluates a_/m_ (scale),
# poly_params + cb_params + k_ (resolution) -- and generates the reproducible
# smearing random number itself, seeded from (event, lumi, phi) with numpy
# (rnd_gen="np"); it does not use the file's RandomSmearing correction.
# Muons below 26 GeV (and above 200) are left uncorrected by the kit, which is
# the intended choice for this analysis.
#
# The kit is awkward-native (nested=True): pass jagged Muon.* arrays directly,
# no flatten/unflatten. filter_boundaries() (low_pt_threshold=26) and the
# pt_corr/pt sanity cut live inside pt_scale/pt_resol, so we don't re-guard.
# ===========================================================================


@calibrator(
    uses={
        "Muon.pt",
        "Muon.eta",
        "Muon.phi",
        "Muon.charge",
        "Muon.nTrackerLayers",
        "event",
        "luminosityBlock",
    },
    produces={"Muon.pt"},
)
def muon_scare(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    pt_scale, pt_resol = self.pt_scale, self.pt_resol  # set in setup
    is_data = self.dataset_inst.is_data

    # scale: applied to data AND MC
    pt_corr = pt_scale(
        is_data,
        events.Muon["pt"],
        events.Muon["eta"],
        events.Muon["phi"],
        events.Muon["charge"],
        self.muon_cset,
        nested=True,
    )
    events = set_ak_column(events, "Muon.pt", pt_corr)

    # resolution smearing: MC only, on the scale-corrected pt
    if not is_data:
        pt_scaled = events.Muon["pt"]
        pt_corr = pt_resol(
            pt_scaled,
            events.Muon["eta"],
            events.Muon["phi"],
            events.Muon["nTrackerLayers"],
            events.event,
            events.luminosityBlock,
            self.muon_cset,
            nested=True,
            rnd_gen="np",
        )
        events = set_ak_column(events, "Muon.pt", pt_corr)

        # MUO scale / resolution variations, as in the MuonScaRe kit README:
        # scale variation on the fully corrected pt, resolution variation from
        # the (scale-only, scale+resol) pair. Outside the kit's validity range
        # (pt < 26 or > 200 GeV) the kit returns the input, i.e. no variation.
        for d in ("up", "down"):
            events = set_ak_column(events, f"Muon.pt_scale_{d}", self.pt_scale_var(
                pt_corr, events.Muon["eta"], events.Muon["phi"], events.Muon["charge"], KIT_DIRECTION[d], self.muon_cset, nested=True,
            ))
            events = set_ak_column(events, f"Muon.pt_resol_{d}", self.pt_resol_var(
                pt_scaled, pt_corr, events.Muon["eta"], KIT_DIRECTION[d], self.muon_cset, nested=True,
            ))

    return events


# the kit spells the down variation "dn"; anything else only prints an error
KIT_DIRECTION = {"up": "up", "down": "dn"}


@muon_scare.init
def muon_scare_init(self: Calibrator, **kwargs) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        self.produces |= {f"Muon.pt_{v}_{d}" for v in ("scale", "resol") for d in ("up", "down")}


@muon_scare.requires
def muon_scare_requires(
    self: Calibrator,
    task,
    reqs: dict,
    **kwargs,
) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles

    reqs["external_files"] = BundleExternalFiles.req(task)


@muon_scare.setup
def muon_scare_setup(
    self: Calibrator,
    task,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
    **kwargs,
) -> None:
    import os
    import sys

    import azh

    # repo root = parent of the azh/ package dir; kit lives under modules/
    _repo = os.path.dirname(os.path.dirname(os.path.abspath(azh.__file__)))
    _kit = os.path.join(_repo, "modules", "muonscarekit", "scripts")
    if _kit not in sys.path:
        sys.path.insert(0, _kit)
    import inspect
    from MuonScaRe import pt_resol, pt_resol_var, pt_scale, pt_scale_var

    self.pt_scale, self.pt_resol = pt_scale, pt_resol
    self.pt_scale_var, self.pt_resol_var = pt_scale_var, pt_resol_var

    # the variation calls above are positional; fail loudly if the pinned kit
    # changes their signatures
    expected = {
        pt_scale_var: ["pt", "eta", "phi", "charge", "updn", "cset", "nested"],
        pt_resol_var: ["pt_woresol", "pt_wresol", "eta", "updn", "cset", "nested"],
    }
    for func, names in expected.items():
        got = list(inspect.signature(func).parameters)[:len(names)]
        if got != names:
            raise RuntimeError(
                f"MuonScaRe.{func.__name__} has parameters {got}, expected {names}; "
                "update the call in azh/calibration/corrections.py:muon_scare",
            )

    import correctionlib

    bundle = reqs["external_files"]
    self.muon_cset = correctionlib.CorrectionSet.from_string(
        bundle.files.muon_scalesmearing.load(formatter="gzip").decode("utf-8"),
    )


"""
EGM electron scale & smearing, eT-dependent (electronSS_EtDependent.json.gz).

  * data: pt *= compound "Scale"(syst="scale", run, ScEta, r9, pt, seedGain).
    The compound chains EGMScaleVsRun -> EleEtaR9 -> EleFineEtaR9 -> ElePT ->
    EleGain -> ElePTsplit. The previous code applied only the last step, a
    ~1e-4 residual; the run-dependent step alone moves 2023D electrons by
    +2.3% on average (Z->ee core peak 88.8 -> 90.8 GeV in data).
  * MC: pt *= 1 + sigma * N(0,1), sigma = SmearAndSyst("smear", pt, r9, ScEta).
    No scale on MC, no smearing on data (EGM).
  * MC variations, on top of the smeared (unscaled) pt, as EGM prescribes:
        pt_scale_{up,down} = pt_smeared * (1 +- escale)
        pt_smear_{up,down} = pt * (1 + (sigma +- esmear) * N)   (same N)
    escale / esmear are the relative uncertainties from SmearAndSyst.
  * Corrections are applied at all pT: every pT-binned correction in the file
    starts at 0 GeV (the former 15 GeV floor is removed).
  * Reproducible smearing: the Gaussian is seeded per electron from
    (event, object index).

Input values are matched to each correction's declared input names, so signed
vs absolute ScEta and the run / seedGain inputs are resolved from the file.

Collection fields are read by key (ele["pt"]), not attribute: after jet_energy
the collections carry vector behaviour, and ele.pt then dispatches to a
Lorentz-vector property that needs phi, which this calibrator does not load.
"""


def _build_args(corr, syst, values):
    """evaluate() arguments for *corr*, matched by the declared input names."""
    args = []
    for inp in corr.inputs:
        if inp.name == "syst":
            args.append(syst)
        elif inp.name in values:
            args.append(values[inp.name])
        else:
            raise KeyError(
                f"electron_ss: correction '{corr.name}' declares unexpected input "
                f"'{inp.name}' (known: syst, {sorted(values)})",
            )
    return tuple(args)


@calibrator(
    uses={
        "run",
        "event",
        "Electron.{pt,eta,deltaEtaSC,r9,seedGain}",
    },
    produces={"Electron.pt"},
)
def electron_ss(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    ele = events.Electron
    counts = ak.num(ele["pt"], axis=1)

    pt = ak.to_numpy(ak.flatten(ele["pt"])).astype(np.float64)
    sceta = ak.to_numpy(ak.flatten(ele["eta"] + ele["deltaEtaSC"])).astype(np.float64)
    values = {
        "pt": pt,
        "r9": ak.to_numpy(ak.flatten(ele["r9"])).astype(np.float64),
        "ScEta": sceta,
        "AbsScEta": np.abs(sceta),
        "run": ak.to_numpy(ak.flatten(ak.broadcast_arrays(events.run, ele["pt"])[0])).astype(np.int64),
        "seedGain": ak.to_numpy(ak.flatten(ele["seedGain"])).astype(np.int64),
    }

    def store(name, flat):
        return set_ak_column(events, name, ak.unflatten(np.maximum(flat, 0.0).astype(np.float32), counts))

    if self.dataset_inst.is_data:
        scale = self.corr_scale.evaluate(*_build_args(self.corr_scale, "scale", values))
        return store("Electron.pt", pt * scale)

    sigma = self.corr_smear.evaluate(*_build_args(self.corr_smear, "smear", values))
    unc_scale = self.corr_smear.evaluate(*_build_args(self.corr_smear, "escale", values))
    unc_smear = self.corr_smear.evaluate(*_build_args(self.corr_smear, "esmear", values))

    # reproducible per-electron gaussian, seeded from (event, object index)
    event_per_ele = ak.to_numpy(ak.flatten(ak.broadcast_arrays(events.event, ele["pt"])[0])).astype(np.uint64)
    obj_idx = ak.to_numpy(ak.flatten(ak.local_index(ele["pt"], axis=1))).astype(np.uint64)
    seeds = event_per_ele * np.uint64(2654435761) + obj_idx
    gauss = np.array([np.random.default_rng(sd).standard_normal() for sd in seeds], dtype=np.float64)

    pt_smeared = pt * (1.0 + sigma * gauss)
    events = store("Electron.pt_scale_up", pt_smeared * (1.0 + unc_scale))
    events = store("Electron.pt_scale_down", pt_smeared * (1.0 - unc_scale))
    events = store("Electron.pt_smear_up", pt * (1.0 + (sigma + unc_smear) * gauss))
    events = store("Electron.pt_smear_down", pt * (1.0 + np.maximum(sigma - unc_smear, 0.0) * gauss))
    return store("Electron.pt", pt_smeared)


@electron_ss.init
def electron_ss_init(self: Calibrator, **kwargs) -> None:
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        self.produces |= {f"Electron.pt_{v}_{d}" for v in ("scale", "smear") for d in ("up", "down")}


@electron_ss.requires
def electron_ss_requires(
    self: Calibrator,
    task,
    reqs: dict,
    **kwargs,
) -> None:
    if "external_files" in reqs:
        return
    from columnflow.tasks.external import BundleExternalFiles

    reqs["external_files"] = BundleExternalFiles.req(task)


@electron_ss.setup
def electron_ss_setup(
    self: Calibrator,
    task,
    reqs: dict,
    inputs: dict,
    reader_targets: InsertableDict,
    **kwargs,
) -> None:
    import correctionlib

    bundle = reqs["external_files"]
    cset = correctionlib.CorrectionSet.from_string(
        bundle.files.electron_ss.load(formatter="gzip").decode("utf-8"),
    )
    scale_name, smear_name = self.config_inst.x.electron_ss_names

    # correctionlib raises a bare "IndexError: map::at" for an unknown key;
    # report which name failed and what the file provides instead
    plain, compound = list(cset.keys()), list(cset.compound.keys())
    missing = [n for n in (scale_name, smear_name) if n not in plain + compound]
    if missing:
        raise KeyError(
            f"electron S&S correction(s) {missing} not found for config "
            f"'{self.config_inst.name}'. The era's electronSS_EtDependent.json.gz "
            f"provides plain {plain} and compound {compound}",
        )
    self.corr_scale = cset.compound[scale_name] if scale_name in compound else cset[scale_name]
    self.corr_smear = cset.compound[smear_name] if smear_name in compound else cset[smear_name]


# ===========================================================================
# Non-finite MET guard
# ===========================================================================
# Some NanoAOD data events carry a non-finite RawPuppiMET (e.g. run 360927,
# lumi 1083, event 2217841979 in Run2022F Muon). Re-applying the JEC Type-1
# propagation then gives a non-finite PuppiMET, and CalibrateEvents refuses to
# write it. Calibration cannot drop events, so every PuppiMET column (nominal
# and all variations) of such an event is set to -1, an impossible value; the
# selector rejects events with PuppiMET.pt < 0 (step "met_finite"). The number
# of such events is printed per chunk: it should be a handful per file at most.
MET_INVALID = -1.0


@calibrator
def met_finite_guard(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    met = events.PuppiMET
    bad = np.zeros(len(events), dtype=bool)
    for col in self.met_columns:
        bad |= ~np.isfinite(ak.to_numpy(met[col]))
    n_bad = int(bad.sum())
    if n_bad:
        print(f"met_finite_guard: {n_bad} event(s) with non-finite PuppiMET set to {MET_INVALID} "
              "(rejected in selection, step met_finite)")
        for col in self.met_columns:
            vals = np.where(bad, MET_INVALID, ak.to_numpy(met[col])).astype(np.float32)
            events = set_ak_column(events, f"PuppiMET.{col}", vals)
    return events


@met_finite_guard.init
def met_finite_guard_init(self: Calibrator, **kwargs) -> None:
    cols = ["pt", "phi"]
    if getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc:
        postfixes = [
            f"jec_{src}_{d}" for src in self.config_inst.x.jec.Jet.uncertainty_sources for d in ("up", "down")
        ] + ["jer_up", "jer_down", "unclustered_up", "unclustered_down"]
        cols += [f"{v}_{p}" for v in ("pt", "phi") for p in postfixes]
    self.met_columns = cols
    self.uses |= {f"PuppiMET.{c}" for c in cols}
    self.produces |= {f"PuppiMET.{c}" for c in cols}


# ===========================================================================
# Non-finite lepton momentum variations
# ===========================================================================
# The MuScaRe kit falls back to the uncorrected pT where its nominal correction
# is undefined, but its variation functions return NaN for such muons (seen in
# 2024 ttbar). A lepton with a non-finite varied pT gets no variation: the
# varied value is set to its nominal pT. The count is printed per chunk and
# should be a handful of leptons at most.
LEPTON_VARIATIONS = {
    "Muon": [f"pt_{v}_{d}" for v in ("scale", "resol") for d in ("up", "down")],
    "Electron": [f"pt_{v}_{d}" for v in ("scale", "smear") for d in ("up", "down")],
}


@calibrator
def lepton_variation_guard(self: Calibrator, events: ak.Array, **kwargs) -> ak.Array:
    if not self.dataset_inst.is_mc:
        return events
    for coll, cols in LEPTON_VARIATIONS.items():
        nominal = events[coll]["pt"]
        for col in cols:
            vals = events[coll][col]
            bad = ~np.isfinite(vals)
            n_bad = int(ak.sum(bad))
            if n_bad:
                print(f"lepton_variation_guard: {n_bad} non-finite {coll}.{col} value(s) set to the nominal pt")
                events = set_ak_column(events, f"{coll}.{col}", ak.where(bad, nominal, vals))
    return events


@lepton_variation_guard.init
def lepton_variation_guard_init(self: Calibrator, **kwargs) -> None:
    if not (getattr(self, "dataset_inst", None) and self.dataset_inst.is_mc):
        return
    for coll, cols in LEPTON_VARIATIONS.items():
        self.uses |= {f"{coll}.pt"} | {f"{coll}.{c}" for c in cols}
        self.produces |= {f"{coll}.{c}" for c in cols}
