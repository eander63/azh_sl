# AZH → semileptonic (Run 3)

Search for a heavy pseudoscalar **A → ZH**, with H → tt̄ and Z → ℓℓ, in CMS Run 3
data. Built on
[columnflow](https://github.com/columnflow/columnflow). Directions are for use on DESY.

**Status: work in progress.** The full chain runs end to end on real events
(through `cf.ProduceColumns`) with the 3-lepton selection and all six POG
corrections in place. Next step is the batched reprocess into a fresh version,
then histograms/limits. Systematics are deferred (nominal only).

---

## Setup

### First time

```bash
git clone --recursive git@github.com:eander63/azh_sl.git
cd azh_sl
```

`--recursive` matters: `columnflow`, `cmsdb`, and `muonscarekit` are submodules,
and columnflow has its own (`law`, `order`). If you forget it:
`git submodule update --init --recursive`.

Note `muonscarekit` is **pinned at commit 5541977** (see MUO below) — do not
update it without re-checking the RandomSmearing/JSON compatibility.

### Every session

From the repo root, in a **fresh shell**:

```bash
cd /path/to/azh_sl

export CF_DATA=/data/dust/user/$(whoami)/azh_data
export CF_HTCONDOR_FLAVOR=naf_el9
export CF_JOB_BASE=/data/dust/user/$(whoami)/azh_jobs
export CF_WLCG_USE_CACHE=True
export CF_WLCG_CACHE_ROOT=/data/dust/user/$(whoami)/azh_cache
export CF_WLCG_CACHE_CLEANUP=False

source setup.sh
source /cvmfs/grid.desy.de/etc/profile.d/grid-ui-env.sh
voms-proxy-init --voms cms --valid 192:00
```

- The exports must come **before** `source setup.sh` — they're read during setup.
- The first run builds the software stack under `$CF_DATA/software` and is slow.
  Later runs are fast.
- Everything is written to `$CF_DATA`. No CERN EOS, no Tier-2 — `naf_el9` jobs
  run on workers that mount `/data/dust`.
- correctionlib and awkward only exist inside the columnflow sandbox. For a bare
  `python3` check outside a `law run`, source a sandbox first, e.g.
  `source modules/columnflow/sandboxes/venv_columnar.sh`.

---

## What runs

```
cf.GetDatasetLFNs        find input NanoAOD files
    ↓
cf.CalibrateEvents       JEC/JER, muon + electron scale & smearing, jet-lepton cleaning
    ↓
cf.SelectEvents          lepton / jet / trigger selection, MET filters, jet veto map
    ↓
cf.ReduceEvents          drop rejected events and unused columns
    ↓
cf.MergeReducedEvents
    ↓
cf.ProduceColumns        Z / H reconstruction, weights, categories
    ↓
cf.CreateHistograms  →  cf.MergeHistograms  →  cf.PlotVariables1D
```

### Defaults

Set in `azh/config/config_run3.py` (~line 708). These name the files to read:

| Setting | Value | Lives in |
|---|---|---|
| `default_calibrator` | `skip_jecunc` | `azh/calibration/default.py` |
| `default_selector` | `default` | `azh/selection/default.py` |
| `default_producer` | `default` | `azh/production/default.py` |
| `default_weight_producer` | `all_weights` | `azh/trigger/weights.py` |
| `default_categories` | `["cat_incl"]` | `azh/config/categories.py` |
| `default_variables` | `["jet1_pt"]` | `azh/config/variables.py` |

`law.cfg` sets `default_config: config_2022pre`, `default_dataset: tt_sl_powheg`.

The names `skip_jecunc` / `default` / `default` are load-bearing — they appear in
the store path, so renaming them orphans the existing store. Leave them ugly.

### Configs

Eleven configs, five eras. Built in `azh/config/analysis_azh_run3.py`; the real
content is `azh/config/config_run3.py`.

| Config | Lumi (pb⁻¹) | NanoAOD | Signal |
|---|---|---|---|
| `config_2022pre` | 7990 | v12 | yes |
| `config_2022post` | 26675 | v12 | yes |
| `config_2023pre` | 18062 | v12 | yes |
| `config_2023post` | 9693 | v12 | yes |
| `config_2024` | 109948 | v15 | no |

Each era has a `_limited` variant (1 file per dataset) for fast iteration;
`config_2022pre` also has `config_2022pre_10files`. Config groups:

- `--configs run3` — all five eras
- `--configs run3_v12` — the four v12 eras, i.e. everything the AZH signal
  samples exist for

2025/2026 are **not supported**: those cmsdb campaigns contain data PDs only,
no MC.

### 2024

2024 is a single undivided era (no pre/post split), so `corr_postfix` is `""`
and the era key is just `"2024"`. Three things differ structurally from
2022/23, beyond the usual per-era correction values:

**b tagging.** BTV published no ParticleNet or DeepJet working points for 2024;
the recommended tagger is UParT. `cfg.x.btag_default` carries the
era-appropriate `{name, column, wp}` and is consumed by `jet_selection`,
`higgs_reco`, `variables` and `keep_columns` instead of a hard-coded
`btagPNetB`. For 2022/23 it resolves to ParticleNet medium — identical to the
previous behaviour, so existing 22/23 stores stay valid and need no version
bump. This matters for `sr_1b` / `sr_2b`, which are defined by b-jet count.

**Drell-Yan.** 2024 has no lepton-inclusive DY sample, so the three
flavour-split ones (`dy_{ee,mumu,tautau}_m50toinf_amcatnlo` plus the `m10to50`
powheg equivalents) are used instead. Note the low-mass generator therefore
differs by era. These datasets are deliberately **not** tagged `is_dy`, because
`dy_producer` needs `<base>_<njet>j_<hf|lf>` child processes that cmsdb does not
define for the flavour-split processes. They instead get a plain `process_id`
from their own leaf process, and the config registers `dy_ee` / `dy_mumu` /
`dy_tautau` in place of `dy_hf` / `dy_lf`.

**No signal.** The 2024 campaign ships no `azh.py`, so all `azh_htt_zll_*`
entries are stripped from `process_names`. Anything resolving a signal process
by name against `config_2024` will fail — use `--configs run3_v12`.

Primary datasets: the EGamma PD is `data_e_*` in 2024, not `data_egamma_*`.
Both get the `egamma` tag so `Trigger.applies_to_dataset` is unaffected. Eras
run C–I. Sanity numbers: 43 datasets, 22 MC + 21 data.

#### 2024 open items

Settings transcribed from POG docs or a sister analysis but not checked against
the actual files are collected per config in `cfg.x.unverified_settings` and
logged as a warning at config build. Clear an entry once verified.

| Item | What to do |
|---|---|
| Trigger filter bits | v15 repacked the electron `TrigObj.filterBits`; `add_triggers_2024` uses bit 18 for Ele30 (v12 used bit 19, a *different* filter in v15). A wrong bit does not raise — check the trigger-matching turn-on vs. offline pT. |
| `pu_sf` / pileup JSON | LUM may ship 2024 as `puWeights_BCDEFGHI.json.gz` rather than the plain name from `corr_tag`, and the Collisions24 PileUp area may be split per era-range. Check on `/cvmfs`. |
| btag SF correction sets | `unifiedParTAK4_light` / `_comb` — confirm against the 2024 BTV correctionlib file. |
| `muon_sf_*` era key | These pass `"2024"` straight into `muon_Z.json`; confirm MUO uses that string. |
| `electron_ss_names`, `electron_sf_trig_names` | The `EGMScale_ElePTsplit_2024` / `2024Prompt` keys follow the 2022/23 pattern; introspect the 2024 EGM files. |
| `channel_lumis` | Left at 1.0 (muon = egamma = nominal). Re-derive with brilcalc per PD if the two PDs do not run end-to-end. |
| Luminosity | 109948 pb⁻¹ for runs 378981–386951 is the central recommendation, not locally brilcalc-verified. |
| W+jets | Dropped for 2024 — only jet-binned madgraph (no 0j bin) and pt-binned amcatnlo exist, both needing stitching. Small in 2l/3l, but add it back before unblinding. |
| DY hf/lf split | Needs `dy_{flav}_m50toinf_{0..3}j_{hf,lf}` processes in `modify_cmsdb_processes` plus a flavour-aware `base_proc_name` in `dy_producer`. Decide first whether 2024 DY should be njet-split at all. |
| Single top | 2024 uses the `_lep_` t-channel samples; `_had_` omitted as it cannot pass a 2l/3l selection. |

Note: the cmsdb `azh_run3` branch renamed `wwz_pythia` → `wwz_amcatnlo`
(generator change, not just a rename) in the 2022preEE campaign. Diboson
normalisation is not directly comparable across the submodule switch.
---

## Running

### Example

```bash
law run cf.PlotVariables1D \
    --config config_2022pre \
    --version v1 \
    --datasets tt_sl_powheg,dy_m50toinf_amcatnlo,data_mu_c \
    --variables m_z,n_jets \
    --categories 2l__2mu \
    --
```

### `--version` is mandatory

There is no default version — omitting it raises
`MissingParameterException: requires the 'version' parameter to be set`.
`--print-status` also needs a `--version`.

### Store paths hash names, not code

```
$CF_DATA/cf_store/analysis_azh/{task}/{config}/{dataset}/{shift}/{calib}/{version}/
```

Every element is a *name*, not a checksum of your source. So **pure code moves /
renames-within-a-file are free** (the store stays valid), but **any behavioral
change needs a `--version` bump** — nothing forces it for you, and the framework
will happily reuse a stale store after a physics change. When you change
`keep_columns`, the reduced store must be rebuilt: bump the version, or force it
with `--cf.ReduceEvents-remove-output 0,a,y`.

---

## Categories: validation vs. analysis in one store

Three orthogonal axes (`azh/config/categories.py`, `azh/production/categories.py`):

```
multiplicity:  2l (=100)  |  3l (=200)          validation vs analysis
flavor:        2e (=10)   |  2mu (=20)          Z candidate flavor
region:        wz_cr (=4000) | sr_1b (=5000) | sr_2b (=6000)   b-jet count (3l only)
```

IDs are additive (`3l__2e__sr_2b` = 6210). 13 combined leaves, built as three
scoped 2-group `create_category_combinations` calls (not one 3-group call +
skip_fn — columnflow's parent-finding ignores skip_fn, so skipping a mid-node
crashes on the missing parent).

- **Validation** = `2l__2e`, `2l__2mu` — no baseline cuts, high-stat DY for
  Z-peak / lepton-calibration checks.
- **Analysis** = `3l__*__<region>` — full B2G-24-002 baseline (Z window, MET,
  ≥4 jets) plus the b-jet region split.

The selector is deliberately **conservative** (loose leptons pT>10, loose IDs,
crack veto, SC-η, ≥2 loose jets); all tunable cuts (25/20/15 pT, tight IDs,
4th-lepton veto, Min(mℓℓ), charge sum) live in categories so they can be
retuned without reprocessing. Categorizers use hard `_require()` failures, not
silent-empty masks.

---

## POG corrections

All six audited against the jsonpog-integration JSONs and run end-to-end on data
+ MC. Nominal only; systematics deferred. Verified with sane weight values
(b-tag mean ≈ 1.00, pileup 0.17–1.64, lepton SFs ≈ 0.97–0.99).

### LUM — done
- Pileup via correctionlib (`azh/production/pileup.py`, reads `pu_sf`); profile
  route (`mc_profile`/`data_profile`) fully removed. Closes the stale-2023
  profile bug and the "pu_weight 0–160" pathology (now bounded 0.17–1.64).
- Per era, one correction, run range matches (BCD/EFG/BC/D).
- `pu.json` kept — required by columnflow `BundleExternalFiles`, not used to
  build the weight.
- Deferred: `minbias_xs` up/down (same JSON, "up"/"down").

### EGM — done (ran data + MC)
- Reco (RecoBelow20 / Reco20to75 / RecoAbove75) + ID (wp80iso) + trigger SFs,
  all four eras. Low-pT reco (10–20) added for the pT>10 loose floor.
- phi (2023) and supercluster-η handled automatically by stock `electron_weights`.
- Scale & smearing → **eT-dependent** (POG-recommended): `electron_ss` in
  `calibration/corrections.py`. SC-η = eta + deltaEtaSC, ElePTsplit scale/smear,
  reproducible per-electron seed, <15 GeV pass-through. `external_files` →
  `electronSS_EtDependent.json.gz`; per-era `EGMScale_ElePTsplit_*` /
  `EGMSmearAndSyst_ElePTsplit_*`.
- Deferred: `electron_loreco_weight_down` can dip very slightly negative
  (~-1e-4) in the 10–20 GeV bin (large Zee background per EGM) — clamp at 0 or
  accept when electron-reco systematics are enabled. Harmless for nominal.

### MUO — done (ran data + MC)
- ID (`NUM_TightID_DEN_TrackerMuons`) + iso (`NUM_TightPFIso_DEN_TightID`) SFs.
- Trigger SF fixed to plain `NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight`
  (matches HLT_IsoMu24; was the IsoMu24-OR-highPt numerator).
- SFs masked to pT≥15 (file bins start at 15; sub-15 muons get SF=1 and are cut
  by `catid_3l`).
- RECO SF correctly NOT applied (Run 3 SF≈1, POG provides none).
- Scale & smearing: official **muonscarekit** (submodule pinned at **5541977**,
  which generates the CB random itself — matches the no-RandomSmearing CVMFS
  JSON). `rnd_gen="np"` (no ROOT), deterministic seed from (event, lumi, phi).
  Replaced a hand-rolled CB inverse-CDF that had visible bugs.
- Deferred: high-pT GE correction (pT>200) for high-mass signal points;
  scale/iso systematics (`pt_scale_var`/`pt_resol_var` in the kit).

### JME — done (nominal; systematics deferred)
- **JEC/JER**: `jet_type = "AK4PFPuppi"`, nominal only (`jec_nominal`, empty
  uncertainty sources). AK4PFPuppi confirmed all four eras (Summer22_V2,
  Summer22EE_V2, Summer23Prompt23, Summer23BPixPrompt23_V3).
- **MET → PuppiMET** everywhere (baseline pT_miss, χ² top reco, uses/produces,
  variables, keep_columns). PF MET is invalid with PUPPI jets.
- **Endcap noise veto** on loose jets: 2.5<|η|<3.0 requires pT>50 (EE eta-spike).
- **jetId**: v12 packing {0,2,6}; loose ≥2, tight ==6.
- **Jet veto maps**: stock `jet_veto_map` applies `jetvetomap` (2022 EE water
  leak) all eras, and for 2023postBPix folds in negated `jetvetomap_bpix` (FPix)
  — the postBPix condition fires for our campaign. No override needed.
- **Noise filters** reconciled to Run-3 rec: added `hfNoisyHitsFilter`,
  uncommented `ecalBadCalibFilter`; HBHE filters removed (no longer needed).
- Deferred: JEC uncertainty sources (Regrouped_* present in file), JER variations
  (scaling method for 2.5<|η|<3); ecalBadCalib uses the stored flag (a remade
  version may be recommended — revisit if MET tails look off).

### BTV — done (ran; b-tag weight mean ≈ 1.00)
- **DeepJet → ParticleNet** (POG-preferred, better Run-3 performance; ~85% vs
  82% b-eff at medium WP). SR/CR split *is* b-multiplicity, so this directly
  sharpens signal/control separation.
- b-jet definition `Jet.btagPNetB > particlenet.medium` (per-era WP, values
  file-verified: 0.245 / 0.2605 / 0.1917 / 0.1919).
- SF via `particleNet_comb` + `particleNet_light` (`_comb`, not `_shape` — this
  is a WP-count analysis, not a discriminant-shape one; `_comb` also exists in
  all four eras whereas 2023 lacks `particleNet_mujets`).
- `btagPNetB` + `hadronFlavour` kept through reduction for the SF.

### TAU — N/A
No hadronic taus in the final state; correctly absent from `external_files`.

---

## Batched reprocess (next step)

All the POG changes above plus the 3-lepton selection and category scheme are
behavioral, so they land together in **one reprocess at a new `--version`** — the
"conservative selector, tune in categories" design exists to make this survivable.
Staged changes: pileup correctionlib swap, eT-dependent electron S&S,
muonscarekit, PuppiMET, endcap jet cut, noise filters, ParticleNet b-tagging,
3-lepton selection + 2l/3l categories.

After the reprocess: re-make the `2l__2e` / `2l__2mu` Z-validation plots and check
whether the original ee Data/MC tilt is resolved (crack veto + SC-η +
eT-dependent S&S should fix it).

---

## Systematics (deferred, not started)

`cfg.x.event_weights` entries are all `[]` and JEC `uncertainty_sources` is empty,
so systematics are effectively off. The pieces that come from the same POG JSONs
(lepton/b-tag SF up/down, JEC sources, JER, pileup up/down) are enabled by the
`"up"`/`"down"` strings; theory (μR/μF, PDF, PS) come from LHE weights already in
the store; luminosity and nonprompt are analysis-derived. Note the JES/JER
migration across the b-jet SR/CR boundary is the main *migration effect* to get
right, not just a nuisance. Also disabled but purposeful: `zpt_reweight`
(DY NLO-shape fix, placeholder in `weights.py`), the `w_lepton` assignment bug
(uses 3rd-hardest lepton not the one outside the Z pair — matters for χ² top reco).

---

## Housekeeping notes

- `azh/production/trigger.py` is a WIP debug producer (`trig_ids`), registered in
  `law.cfg` but never called in the chain — safe to remove.
- `deepcsv` in `btag_working_points` (config_run3.py) is Run-2 vestigial, unused.
- `analysis_azh_run3.py` still carries columnflow-template boilerplate comments.

---

## Resources

[columnflow](https://github.com/columnflow/columnflow) ·
[law](https://github.com/riga/law) ·
[order](https://github.com/riga/order) ·
[cmsdb](https://github.com/uhh-cms/cmsdb) ·
[muonscarekit](https://gitlab.cern.ch/cms-muonPOG/muonscarekit)
