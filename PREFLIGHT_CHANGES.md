# Pre-flight patch series (2022–2024 SR/CR plots)

Base: `6e78263`. Scope of the next run: correctly normalized SR/CR plots for all
five eras with every POG- or NanoAOD-derived uncertainty; no signal, no
reconstruction, no data-driven backgrounds.

The code is lint-clean and parses as Python 3.9, and the new producers' logic
was unit-tested offline. It has **not** been run against columnflow; the
validation plan at the end is the real test.

## Commits

| # | Topic | What changed |
|---|---|---|
| 1 | hygiene | Stale scripts and `production/trigger.py` deleted; `tests/validate_corrections.py` IndentationError fixed; muon pT-floor check compares against `cfg.x.muon_sf_pt_min` |
| 2 | top pT off | `gen_top.py`, top-pT shifts, params and dataset weight removed; `is_ttbar` = `tt_sl/dl/fh` only; `GenPart.*` no longer kept; dead `zpt_reweight`, `muon_reco_weights` removed |
| 3 | luminosity | brilcalc values for the processed runs (current golden JSON, `normtag_PHYSICS`): 7989.5 / 26674.9 / 17964.2 / 9676.7 / 109710.3 pb⁻¹; LUM nuisances `lumi_1/2/3`; golden JSONs from `data/lumi/` |
| 4 | samples | No parent/child pairs in `process_names`; AN background list in every era; missing cmsdb names go to `cfg.x.missing_datasets` (FAIL in the static check); never the overscaled 2022 `ttw_amcatnlo`; MuonEG removed; 2022C needs `data_singlemu_c`; `channel_lumi_weight` deleted; dead DY NNLO override deleted; b-tag efficiency groups from the config's own datasets |
| 5 | triggers | One `add_triggers()` for all eras (2023 had none); IsoMu24 ‖ Ele30 only; HLT decision without TrigObj matching; PD priority Muon/SingleMuon > EGamma |
| 6 | trigger SF | Event-level SF from per-lepton data/MC efficiencies; variations `e_trig`, `mu_trig_stat`, `mu_trig_syst` |
| 7 | lepton SFs | `e_reco` and `e_id` separate; `production/muon_sf.py` with stat/syst variations for muon ID and iso |
| 8 | lepton momentum | Data electrons use the compound EGM `Scale`; S&S at all pT; `e_scale`, `e_smear`, `mu_scale`, `mu_resol` (selection dependent); crack 1.4442–1.5560 |
| 9 | b-tag | c jets as flavour 4; `btag_{bc,light}_{correlated,uncorrelated}` |
| 10 | theory | Hessian PDF + α_s (`pdf_alphas_scale` = 0.75); ISR/FSR from `PSWeight`, normalized per process; `lumi` weight shift for plot bands |
| 11 | MET filters | JME ECAL bad-crystal veto replaces `Flag_ecalBadCalibFilter` for data in runs 362433–367144 |
| 12 | jets / MET / blinding | ΔR < 0.3 cleaning replaces the subtraction cleaner; v15 `Jet.jetId` rebuilt; candidate jets at selection, analysis jets (`AnaJet`, `n_jet`, `n_bjet`) in production; JES (27 sources), JER and `met_unclustered` registered on the producer; SR data stripped from every category |
| 13 | config | `cfg.x.shift_correlations`; fixed groups; versions calib v2 / rest v6 |
| 16 | fixes | `cfg.x.jer` keyed by jet collection with only JERConfig fields (the extra `sf_unc_mode` key made columnflow's JERConfig raise); mode moved to `cfg.x.jer_sf_unc_mode`; unusable tune/hdamp shifts removed; static check no longer flags production-level shifts as orphans |
| 14 | tests / inference | `tests/preflight_static.py` and three study scripts; inference nuisances generated from the correlation table |

## After applying

```bash
cd /data/dust/user/eranders/AZHtt/azh_semileptonic
git am /path/to/patches/*.patch

# 1. the columnflow JER patch changed; setup.sh only applies patches that are
#    not applied yet, so revert the old version first, then re-run setup
git -C modules/columnflow checkout columnflow/calibration/cms/jets.py
source ~/azh_env.sh            # re-applies patches/cf031-jer-additive.patch
git -C modules/columnflow diff --stat   # expect jets.py changed

# 2. pinned golden JSONs (the files currently in the repo root)
mkdir -p data/lumi && mv Cert_Collisions202*_Golden.json data/lumi/

# 3. leftovers that are not tracked by git
find azh -name "*.bak*" -delete; find azh tests -name __pycache__ -exec rm -rf {} +

# 4. static gate: every FAIL except missing_datasets must be gone
python tests/preflight_static.py 2>&1 | tee preflight_static.log
```

## cmsdb additions (your `azh_run3` fork)

These names are what `config_run3.py` now requires. For each key, get
`nfiles` / `nevents` with
`dasgoclient --query="summary dataset=<key>"`. Cross sections: tZq, WWW, WZZ,
ZZZ and ttW(→ℓν) need a process with a 13.6 TeV cross section and an uncertainty
from your reference (not the generator value). For ttW, use cmsdb's existing
`ttw_wlnu` process (0.2249 pb).

**2022preEE** (`Run3Summer22NanoAODv12`)

| dataset | key(s) |
|---|---|
| `data_singlemu_c` | `/SingleMuon/Run2022C-22Sep2023-v1/NANOAOD` (runs 355862–356386, disjoint from Muon C) |
| `tzq_zll_4f_amcatnlo` | `/TZQB-Zto2L-4FS_MLL-30_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` |
| `wz_wlnu_zll_powheg` | `/WZto3LNu_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` + `…_v5_ext1-v3/NANOAODSIM` |
| `zz_zll_zll_powheg` | `/ZZto4L_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` + `…_v5_ext1-v2/NANOAODSIM` |
| `ttw_wlnu_amcatnlo` | `/TTLNu-1Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22NanoAODv12-mg35x_130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` |
| `www_4f_amcatnlo` | `/WWW_4F_TuneCP5_13p6TeV_amcatnlo-madspin-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` |
| `wwz_4f_amcatnlo` | `/WWZ_4F_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` (same key as today's `wwz_amcatnlo`) |
| `wzz_amcatnlo` | `/WZZ_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` |
| `zzz_amcatnlo` | `/ZZZ_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM` |
| `ttz_zll_m50toinf_amcatnlo` (extra key) | `/TTLL_MLL-50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v3/NANOAODSIM` |

**2022postEE** (`Run3Summer22EENanoAODv12`, processing `130X_mcRun3_2022_realistic_postEE_v6`)

| dataset | key suffix after the primary name |
|---|---|
| `tzq_zll_4f_amcatnlo` | `TZQB-Zto2L-4FS_MLL-30_…/…postEE_v6-v2` |
| `wz_wlnu_zll_powheg` | `WZto3LNu_…powheg…/…postEE_v6-v2` + `…postEE_v6_ext1-v2` |
| `zz_zll_zll_powheg` | `ZZto4L_…powheg…/…postEE_v6-v2` + `…postEE_v6_ext1-v2` |
| `ttw_wlnu_amcatnlo` | `TTLNu-1Jets_TuneCP5_…/…-mg35x_130X_mcRun3_2022_realistic_postEE_v6-v2` |
| `www_4f_amcatnlo`, `wwz_4f_amcatnlo`, `wzz_amcatnlo`, `zzz_amcatnlo` | `…postEE_v6-v2` |
| `ttz_zll_m50toinf_amcatnlo` (extra key) | `TTLL_MLL-50_…/…postEE_v6_ext1-v2` |

**2023preBPix** (`Run3Summer23NanoAODv12`)

| dataset | key suffix |
|---|---|
| `tzq_zll_4f_amcatnlo` | `…130X_mcRun3_2023_realistic_v15-v2` |
| `wz_wlnu_zll_powheg` | `…v14-v2` + `…v15_ext1-v2` |
| `zz_zll_zll_powheg` | `…v14-v3` |
| `ttw_wlnu_amcatnlo` | `…-mg35x_130X_mcRun3_2023_realistic_v15-v2` |
| `www_4f_amcatnlo`, `wwz_4f_amcatnlo`, `wzz_amcatnlo`, `zzz_amcatnlo` | `…v14-v2` |
| `ttz_zll_m50toinf_amcatnlo` (extra key) | `…v15_ext1-v2` |

**2023postBPix** (`Run3Summer23BPixNanoAODv12`)

| dataset | key suffix |
|---|---|
| `tzq_zll_4f_amcatnlo` | `…130X_mcRun3_2023_realistic_postBPix_v6-v3` |
| `wz_wlnu_zll_powheg` | `…postBPix_v2-v2` + `…postBPix_v6_ext1-v2` |
| `zz_zll_zll_powheg` | `…postBPix_v2-v3` |
| `ttw_wlnu_amcatnlo` | `…-mg35x_130X_mcRun3_2023_realistic_postBPix_v6-v2` |
| `www_4f_amcatnlo`, `wzz_amcatnlo`, `zzz_amcatnlo` | `…postBPix_v2-v2` |
| `wwz_4f_amcatnlo` | `…postBPix_v2-v3` |
| `ttz_zll_m50toinf_amcatnlo` (extra key) | `…postBPix_v6_ext1-v2` |

The full keys for 2022post–2023post are in the DAS outputs of the pre-flight
thread; the pattern is `/<primary>/<campaign>-<processing>/NANOAODSIM`.

**2024** (`RunIII2024Summer24NanoAODv15`): cmsdb already has everything except

| dataset | key |
|---|---|
| `tzq_zll_4f_amcatnlo` | `/TZQB-Zto2L-4FS_Bin-MLL-30_TuneCP5_13p6TeV_amcatnlo-pythia8/RunIII2024Summer24NanoAODv15-Madgraph_2_6_5_150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` |

The static check confirmed that cmsdb's 2024 `wz_wlnu_zll_powheg` and
`zz_zll_zll_powheg` use the plain keys (not `JMENanoV15`).

**Existing cmsdb ttW entries to fix:**

| era | current key | should be |
|---|---|---|
| 2023preBPix | `/TTLNu-1Jets_…/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v2/…` (3 files) | `…-mg35x_130X_mcRun3_2023_realistic_v15-v2/NANOAODSIM` |
| 2023postBPix | `/TTLNu-1Jets_…/Run3Summer23BPixNanoAODv12-130X_…postBPix_v6-v2/…` (1 file) | `…-mg35x_130X_mcRun3_2023_realistic_postBPix_v6-v2/NANOAODSIM` |
| 2024 | `/TTLNu-EWK_TuneCP5_13p6TeV_amcatnlo-pythia8/…` -- the **electroweak** ttW component, normalized with the QCD ttW cross section | `/TTLNu-1Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24NanoAODv15-mg35x_150X_mcRun3_2024_realistic_v2-v2/NANOAODSIM` |

Until the fork has them, the config falls back to LO `wz_pythia` / `zz_pythia`
and runs without tZq, ttW and VVV. The static check reports each missing name.

## Things to confirm on your side

- **columnflow shift propagation.** The JES/JER/unclustered shifts are
  registered on the producer. Confirm that ProduceColumns and CreateHistograms
  register producer shifts:
  `grep -n "register_.*_shifts" modules/columnflow/columnflow/tasks/*.py`.
  Then check without running anything:

  ```bash
  law run cf.CreateHistograms --config config_2022pre_limited --dataset tt_dl_powheg \
      --shift jec_AbsoluteStat_up --version v6 --print-status 5
  ```

  CalibrateEvents, SelectEvents and ReduceEvents should appear with shift
  `nominal`, and ProduceColumns and CreateHistograms with the JES shift. For
  `--shift e_scale_up`, Select and Reduce should carry the shift.
- **MuonScaRe signatures.** The calibrator raises at setup if `pt_scale_var` /
  `pt_resol_var` differ from the README-style signatures:
  `grep -n "def pt_scale_var\|def pt_resol_var" modules/muonscarekit/scripts/MuonScaRe.py`.
- **Non-blocking POG questions.**
  - JME: Summer24 JER convention (additive assumed); Type-1 jet selection for PUPPI; the Run 3 JES correlation table (Run 2 pattern used).
  - EGM: SC-η vs η for the HLT efficiencies (SC-η used, `cfg.x.electron_hlt_use_sc_eta`).

## Validation plan

1. **Static.** `python tests/preflight_static.py`: only `missing_datasets` FAILs remain.
2. **Nominal, limited.** For each era, run ProduceColumns on `_limited` for one
   data and three MC datasets (ttZ, WZ, DY). Check the produced columns exist:
   `n_jet`, `n_bjet`, `AnaJet.*`, `trigger_weight*`, `muon_id_weight_stat_up`,
   `normalized_isr_weight`, `lumi_weight*`. Check also that data events with
   3l + baseline + ≥ 1 b have empty `category_ids`.
3. **Shifts.** For one production-level shift (`jec_FlavorQCD_up`) and one
   selection-level shift (`e_scale_up`), make one histogram each on limited ttZ
   and confirm it differs from nominal. A bit-identical histogram means an
   alias fell back.
4. **Physics.** Before any SR plot:
   - m_ℓℓ in `2l__2e` and `2l__2mu` per era, data vs MC (EGM/MUO scale, 2023D electrons);
   - lepton pT;
   - `n_jet` in 2l (the ΔR cleaning);
   - the WZ CR.
