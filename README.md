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
- `setup.sh` refuses to run twice in one shell. *"the AZH analysis was already
  succesfully setup"* means open a new shell.
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

### Pin the calibration version

The existing store is **not** uniform: `cf.CalibrateEvents` is at `v0`,
everything downstream is at `v1`. To reuse the existing calibration:

```bash
law run cf.PlotVariables1D \
    --config config_2022pre \
    --version v1 \
    --cf.CalibrateEvents-version v0 \
    --datasets tt_sl_powheg \
    --variables m_z
```

**Omit `--cf.CalibrateEvents-version v0` and law will regenerate 1.1 TB of
calibration.** This is the most expensive mistake available in this repo.

Store layout:

```
$CF_DATA/cf_store/analysis_azh/{task}/{config}/{dataset}/{shift}/{calib}/{version}/
```

Disk is tight (2 TB dust quota, `CalibrateEvents` is ~1.1 TB of it). Check with
`my-dust-quota`. The `_limited` configs are ~65 GB and regenerate in minutes.

---

## Before you trust output

Three things are wrong in ways that are invisible from the code path. Details
are in the files; the pointers are here so you don't have to find them by
accident.

1. **No JEC uncertainties exist.** The default calibrator `skip_jecunc` produces
   only nominal JEC, while the config registers `jec_Total_up/down` shifts that
   are never filled. All processed data, all four eras.
   → `azh/calibration/jets.py`

2. **Pileup weights are broken** (values 0–160). Still computed and applied.
   → `azh/config/config_run3.py`, search `fix pu_weight`

3. **There is no inference model.** It was removed; `default_inference_model`
   still points at the deleted `"example"`. Limits need rebuilding from scratch.
   → `azh/config/config_run3.py`, search `default_inference_model`

`modules/columnflow` is a flattened snapshot of ~upstream v0.2.4 with no shared
history — upstream docs describe a newer API. See
`modules/columnflow/VENDORED_FROM`.

---

## Development

```bash
law index -q             # imports every module in law.cfg — the real smoke test
bash tests/run_linting   # flake8 only; there are no unit tests
```

`law index -q` silent = success. The post-commit hook lints but never blocks.

A cleanup removed ~5,900 lines (ML model, inference model, Run 2 config chain,
template examples, debug scripts). All recoverable:

```bash
git show pre-cleanup-full-tree:azh/ml/PNN.py > /tmp/PNN.py
```

## Resources

[columnflow](https://github.com/columnflow/columnflow) ·
[law](https://github.com/riga/law) ·
[order](https://github.com/riga/order) ·
[cmsdb](https://github.com/uhh-cms/cmsdb)
