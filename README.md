# AZH → semileptonic (Run 3)

Search for a heavy pseudoscalar **A → ZH**, with H → tt̄ and Z → ℓℓ, in CMS Run 3
data (2022 + 2023, NanoAOD v12). Built on
[columnflow](https://github.com/columnflow/columnflow). Note that the directions are for use on DESY.

**Status: work in progress.** The chain runs end to end and produces validation
plots. It is not ready for limits.

---

## Setup

### First time

```bash
git clone --recursive git@github.com:eander63/azh_sl.git
cd azh_sl
```

`--recursive` matters: `columnflow` and `cmsdb` are submodules, and columnflow
has its own (`law`, `order`). If you forget it:
`git submodule update --init --recursive`.

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

### Configs

Nine configs, four eras, NanoAOD v12. Built in
`azh/config/analysis_azh_run3.py`; the real content is
`azh/config/config_run3.py`.

| Config | Lumi (pb⁻¹) |
|---|---|
| `config_2022pre` | 7990 |
| `config_2022post` | 26675 |
| `config_2023pre` | 18062 |
| `config_2023post` | 9693 |

Each era has a `_limited` variant (1 file per dataset) for fast iteration;
`config_2022pre` also has `config_2022pre_10files`. The group `run3` fans out
across all four full eras: `--configs run3`.

---

## Running

### Example

```bash
law run cf.PlotVariables1D \
    --config config_2022pre \
    --version v1 \
    --datasets tt_sl_powheg,dy_m50toinf_amcatnlo,data_mu_c \
    --variables m_z,n_jets \
    --categories cat_incl \
    --
```

### `--version` is mandatory

There is no default version — omitting it raises
`MissingParameterException: requires the 'version' parameter to be set`.

### Make sure that version number choice is consistent

Store layout:

```
$CF_DATA/cf_store/analysis_azh/{task}/{config}/{dataset}/{shift}/{calib}/{version}/
```

---

## Development

*Last updated: 2026-07 — update this when the plan below changes.*

The chain runs end to end and produces validation plots. The categorization
has been rewritten into blinded analysis regions (see `azh/production/categories.py`
and `azh/config/categories.py`), but **the base selection does not yet match the
target analysis** (B2G-24-002).

1. **The selection is 2-lepton; the analysis is 3-lepton.** The target final
   state is A → ZH → ℓℓ + tt̄(semileptonic): two leptons from the Z, one from
   the leptonic top → three tight leptons, with a fourth-lepton veto and
   Σcharge = ±1. The current selector builds only the OSSF Z pair
   (`n_tight_leptons == 2` in `catid_baseline`). Consequences:
   - No third lepton → no leptonic-W → no neutrino → no m_tt̄, no m_A, **no Δm**.
     Δm × pT_Z is the final observable of the search, so it cannot yet be built.
   - The 0b "WZ CR" is a 3-lepton region in the analysis. The current 2-lepton
     version is a **Z+jets sanity check, not the WZ CR** — it can't validate the
     WZ normalization, because WZ's third lepton is what defines that background.
   - The columns needed for 3-lepton (`n_tight_leptons`, `charge_sum`, `min_mll`)
     are already built in `azh/production/leptons.py`; `catid_3l` already encodes
     the cut. They're just not wired into the baseline yet.

2. **No JEC/JER/b-tag/lepton/trigger systematics.** All processed data used
   `skip_jecunc` (nominal JEC only). Because the analysis regions are b-jet
   multiplicity slices, JES/JER directly migrate events across the SR/CR
   boundary — so this is a missing *migration effect*, not just a missing
   nuisance. See `azh/calibration/jets.py`.

###TODO

**the 3-lepton overhaul and the final reprocessing are one step,
not two.** The CR can't be validated until the selection is 3-lepton.

1. 2-lepton Z-validation plots on the existing
   v0/v1 store: confirm calibration and Z reconstruction are sane (`m_z`, `pt_z`,
   `n_jets`, `n_bjets` data/MC agreement). This is a sanity check on the current
   store, *not* the analysis CR.

2. Move to 3-lepton base selection; turn on real JEC
   (stock `jec`, source "Total"); add lepton / b-tag / trigger scale factors.
   These are entangled — the selection changes which events exist, JEC changes
   their kinematics, SFs reweight them — so they must land together to avoid
   reprocessing three times.

3. Reprocess into a fresh version. **Then** delete the
   old `skip_jecunc` calibration store.

4. Build Δm and pT_Z × Δm; run the fit. The
   systematics-laden store from step 3 is the input the fit consumes.

### Open questions to resolve before overhaul

- **Do the NanoAOD / MC samples actually contain the third lepton?** If upstream
  skimming dropped it for a 2-lepton selection, no reselection recovers it. Test
  on ttZ (which genuinely has 3 leptons) before investing in the 3-lepton work —
  if `n_tight_leptons == 3` is never populated there, that's the first problem.
- **`choose_lepton` pairing rule.** The analysis forms the Z from the OSSF pair
  closest to m_Z. Confirm `azh/production/leptons.py::choose_lepton` does this,
  not just leading-pT, before trusting m_z in 3-lepton events.
- **Which lepton selector?** `azh/selection/lepton_selection.py`
  (wired in, tightId, pT>25 high leg) vs `azh/selection/z_selection.py`
  (not wired in, highPtId, pT>35, proper OSSF Z pairing). Pick one, delete the
  other.

## Resources

[columnflow](https://github.com/columnflow/columnflow) ·
[law](https://github.com/riga/law) ·
[order](https://github.com/riga/order) ·
[cmsdb](https://github.com/uhh-cms/cmsdb)
