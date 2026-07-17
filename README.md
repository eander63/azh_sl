# AZH → semileptonic (Run 3)

Search for a heavy pseudoscalar **A → ZH**, with H → tt̄ and Z → ℓℓ, in CMS Run 3
data (2022 + 2023, NanoAOD v12). Built on
[columnflow](https://github.com/columnflow/columnflow).

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

```bash
law index -q             # imports every module in law.cfg — the real smoke test
bash tests/run_linting   # flake8 only; there are no unit tests
```

`law index -q` silent = success. The post-commit hook lints but never blocks.

## Resources

[columnflow](https://github.com/columnflow/columnflow) ·
[law](https://github.com/riga/law) ·
[order](https://github.com/riga/order) ·
[cmsdb](https://github.com/uhh-cms/cmsdb)
