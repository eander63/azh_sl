# AZH → semileptonic (Run 3)

Search for a heavy pseudoscalar **A → ZH**, with H → tt̄ and Z → ℓℓ, in CMS Run 3
data (2022–2024). Built on [columnflow](https://github.com/columnflow/columnflow).
Directions are for the DESY NAF.

**Status (Nov 2026):** the full 2022–2024 production is complete at store version
**`v9`** (code: tag `production-v9`, if not yet created: `git tag -a production-v9`): all data, and all MC in the configs with the
nominal pass plus all 8 lepton-scale passes. Validated (completeness, Z peaks,
blinding, data yields per fb⁻¹, shift sanity). Next: the jet/MET shift passes,
then the full data/MC plots with uncertainty bands, then datacards.
See [Open items](#open-items).

---

## Contents

- [Setup](#setup) · [Credentials](#credentials)
- [What runs](#what-runs) · [Configs](#configs) · [Physics choices](#physics-choices)
- [Corrections and systematics](#corrections-and-systematics) · [Known data issues and guards](#known-data-issues-and-guards)
- [Categories](#categories)
- [Production](#production) · [Quick checks](#quick-checks) · [Troubleshooting](#troubleshooting)
- [Statistical tools (combine)](#statistical-tools-combine) · [Open items](#open-items)

---

## Setup

### First time

```bash
git clone --recursive git@github.com:eander63/azh_sl.git
cd azh_sl
```

`--recursive` matters: `columnflow`, `cmsdb` and `muonscarekit` are submodules,
and columnflow has its own (`law`, `order`). If you forget it:
`git submodule update --init --recursive`. `muonscarekit` is pinned at commit
**5541977**; do not update it without re-checking the JSON compatibility.

### Every session

In a **fresh shell** (never one where you ran `cmsenv`, see [combine](#statistical-tools-combine)):

```bash
cd /path/to/azh_sl
export CF_DATA=/data/dust/user/$(whoami)/azh_data
export CF_JOB_BASE=/data/dust/user/$(whoami)/azh_jobs
export CF_HTCONDOR_FLAVOR=naf_el9
export CF_WLCG_USE_CACHE=True
export CF_WLCG_CACHE_ROOT=/data/dust/user/$(whoami)/azh_cache
export CF_WLCG_CACHE_CLEANUP=False
export TMPDIR=/data/dust/user/$(whoami)/azh_tmp                 # login-node /tmp is shared and small
export X509_USER_PROXY=/data/dust/user/$(whoami)/.grid/x509up   # proxy on dust, not AFS
source setup.sh
```

- The exports must come **before** `source setup.sh`.
- The first run builds the software stack under `$CF_DATA/software` (slow).
- Everything is written below `$CF_DATA`; batch jobs run on workers that mount `/data/dust`.
- Tip: keep these lines in `~/azh_env.sh` and just `source ~/azh_env.sh`.
- Check with `which law`: it must point into the repo, **not** to `/cvmfs/.../CMSSW_*`.

### Credentials

Three credentials, each with its own lifetime. Most production interruptions so far
were one of them expiring.

| Credential | Needed for | Lifetime | Renew |
|---|---|---|---|
| Kerberos ticket | HTCondor (submit, query) | 1 day, renewable ~2 days | `kinit && aklog` |
| AFS token | reading the AFS home | with the ticket | `aklog` |
| Grid proxy | reading NanoAOD via XRootD, DAS | max. 8 days | see below |

```bash
# grid proxy: in a subshell, so the grid environment does not leak into the analysis shell
bash -c 'source /cvmfs/grid.desy.de/etc/profile.d/grid-ui-env.sh
         export X509_USER_PROXY=/data/dust/user/$(whoami)/.grid/x509up
         voms-proxy-init --voms cms --valid 192:00'
openssl x509 -in "$X509_USER_PROXY" -noout -enddate

# keep the Kerberos ticket alive for a long run (start in the shell that launches law)
kinit && aklog && krenew -b -K 60 -t
klist | grep -A1 krbtgt          # "renew until": a password kinit is needed before then
```

`krenew` renews the ticket cache of the shell it is started from (`$KRB5CCNAME`),
which must be the cache of the running law process. Ticket caches live in the
node-local `/tmp`, so they differ per node and session. **Never delete a
`/tmp/krb5cc_*` file** belonging to a running law process; if it happens, recreate
it with `KRB5CCNAME=<same path> kinit` at once.

---

## What runs

```
cf.GetDatasetLFNs       input NanoAOD files (validated DAS lookup, see below)
    ↓
cf.CalibrateEvents      JEC/JER (+ 11 JES sources), MET propagation, muon and electron
                        scale & smearing (+ variations), guards for non-finite values
    ↓
cf.SelectEvents         triggers, MET filters, jet veto maps, ECAL bad-crystal veto,
                        leptons, jets, b-tagging; MC weights (PU, PDF, scale, PS)
    ↓
cf.ReduceEvents         keep selected events and the keep_columns
    ↓
cf.MergeReducedEvents   merged reduced events (permanent)
    ↓
cf.ProduceColumns       Z/H reconstruction, scale factors, b-tag weights, categories,
                        normalization (permanent)
    ↓
cf.CreateHistograms → cf.MergeHistograms → cf.PlotVariables1D / datacards
```

Defaults (`azh/config/config_run3.py`): calibrator `skip_jecunc`, selector
`default`, producer `default`, weight producer `all_weights`. These names are part
of the store path; renaming them orphans the store.

### Store and versions

```
$CF_DATA/cf_store/analysis_azh/{task}/{config}/{dataset}/{shift}/calib__.../sel__.../red__.../[prod__.../]{version}/
```

Path elements are *names*, not checksums of the code. Any change in behaviour needs
a new `--version`; nothing forces it, and law will reuse a stale store. `--version`
is mandatory on every `law run`.

---

## Configs

Built in `azh/config/analysis_azh_run3.py`, content in `azh/config/config_run3.py`.

| Config | Era | Lumi (pb⁻¹, brilcalc) | NanoAOD | MC datasets | Data datasets |
|---|---|---|---|---|---|
| `config_2022pre` | 2022 preEE (C–D) | 7989.5 | v12 | 19 | 4 |
| `config_2022post` | 2022 postEE (E–G) | 26674.9 | v12 | 19 | 6 |
| `config_2023pre` | 2023 preBPix (C) | 17964.2 | v12 | 20 | 8 |
| `config_2023post` | 2023 postBPix (D) | 9676.7 | v12 | 20 | 4 |
| `config_2024` | 2024 (C–I) | 109710.3 | v15 | 27 | 14 |

Golden JSONs are pinned with absolute paths below `$CF_DATA/lumi/` (absolute
paths keep the batch bundle hash stable). Luminosity uncertainties enter as
`lumi_1/2/3`.

Each era has a `_limited` variant (1 file per dataset) for fast tests;
`config_2022pre` also has `config_2022pre_10files`.

**Signal samples are not yet in the configs.** The AZH signal exists for the v12
eras only (cmsdb `azh_run3`); 2024 has none.

### 2024 specifics

- **b tagging:** no PNet/DeepJet working points from BTV; UParT is used.
  `cfg.x.btag_default` carries the era's `{name, column, wp}`.
- **Jet ID:** v15 NanoAOD has no `Jet_jetId`; it is rebuilt from `jetid.json`.
- **Drell–Yan:** flavour-split samples (`dy_{ee,mumu,tautau}_m50toinf_amcatnlo`,
  `dy_*_m10to50_powheg`); registered as `dy_ee/dy_mumu/dy_tautau` instead of
  `dy_hf/dy_lf`.
- **W+jets:** not included (only samples that need stitching exist).
- **Primary datasets:** EGamma is `data_e_*`; both PDs carry the `egamma` tag.

---

## Physics choices

| Topic | Choice |
|---|---|
| Triggers | `HLT_IsoMu24` OR `HLT_Ele30_WPTight_Gsf` (decision only; MuonEG and dilepton triggers dropped) |
| Electrons | MVA iso WP80; ECAL crack veto, supercluster η |
| Muons | Tight ID + tight PF isolation |
| Jets | AK4 PUPPI, TightLepVeto ID, \|η\| < 2.5, pT > 30 GeV, ΔR < 0.3 cleaning against leptons |
| Candidate jets | `CandJet`: jets carrying all JES/JER variations, for events with ≥ 2 leptons above 8 GeV |
| b tagging | PNet medium (2022/23), UParT (2024); fixed-WP scale factors with MC efficiency maps |
| MET | PuppiMET everywhere |
| Drell–Yan | NLO (amcatnlo); split into `dy_lf` / `dy_hf` by jet flavour (0j_lf 58%, 1j 28%, 2j 10%, ≥3j 4%) |
| Zγ | not included (DY only); overlap with DY measured, decision with the PI |
| Nonprompt | from MC |
| Blinding | data in the signal region (3l + baseline + ≥ 1 b) is removed from all categories |
| Extensions | only the nominal DAS key of each sample is used (`ext1` samples are not processed) |

---

## Corrections and systematics

### Shifts (separate passes through the chain)

| Type | Shifts | Rerun from | Status |
|---|---|---|---|
| Lepton scale/resolution | `e_scale`, `e_smear`, `mu_scale`, `mu_resol` (up/down) | selection | **done** (v9) |
| Jet energy scale | 11 regrouped sources: Absolute, Absolute_*era*, BBEC1, BBEC1_*era*, EC2, EC2_*era*, FlavorQCD, HF, HF_*era*, RelativeBal, RelativeSample_*era* (up/down) | production | to do |
| Jet energy resolution | `jer` (up/down) | production | to do |
| MET unclustered energy | up/down | production | to do |

The jet and MET variations are already stored on `CandJet` and PuppiMET in the
reduced events, so these passes only rerun `cf.ProduceColumns`.

### Weights (in every pass, no rerun)

Pileup; electron reco/ID/trigger SFs; muon ID/iso/trigger SFs (stat and syst);
b-tag (bc and light, correlated and uncorrelated); luminosity; μR/μF and their
envelope; PDF (see below); parton shower ISR/FSR.

### b-tag efficiencies

Fixed-WP method with efficiencies measured in our MC (`btag_wp_count_config`):
pT bins 30/50/70/100/140/200/∞ GeV, **one |η| bin** (a barrel/endcap split left
light jets above 200 GeV in the endcap with zero tagged jets). Efficiency groups:
tt̄ + single top, tt̄X, DY, dibosons + W+jets + tribosons.

### PDF uncertainties (`azh/production/theory.py`)

| Layout | Set | Samples | Uncertainty |
|---|---|---|---|
| 103 weights | NNPDF3.1 NNLO, 5 flavours (LHA 325300) | most samples | Hessian PDF + αs |
| 101 weights | NNPDF3.1 NNLO, 4 flavours (LHA 325500) | single-top t-channel, 2024 WWW/WWZ | Hessian PDF only (no αs members) |
| none | n/a | LO pythia dibosons (`no_lhe_weights` tag) | no PDF/scale variation |

Any other layout raises an error rather than producing a wrong uncertainty.
2023 ttW has 8 instead of 9 scale weights; columnflow handles that.

---

## Known data issues and guards

| Issue | Handling |
|---|---|
| Non-finite PuppiMET (e.g. 2022F, run 360927, lumi 1083, event 2217841979) | `met_finite_guard` sets all PuppiMET columns to −1; the selection step `met_finite` rejects these events (15 in all data) |
| Non-finite MET unclustered variations | set to no variation |
| Non-finite MuScaRe pT variations (seen in 2024 tt̄) | `lepton_variation_guard`: the varied pT falls back to the nominal pT (count printed per chunk) |
| ECAL bad crystals in prompt reco 2022G / 2023C (runs 362433–367144) | event veto |
| Electron scale in data incomplete before the fix (2023D Z peak at 88.8 GeV) | fixed; Z peaks now 90.75–91.25 GeV in all eras |
| DAS errors stored as file names | `get_dataset_lfns` retries, accepts only `/store/...` paths, refuses lists shorter than cmsdb |
| Outdated cmsdb file counts (2022preEE DY: 525 / 448 files) | overridden in the config's era-specific section |
| Bad input files | `broken_files` aux list per dataset in cmsdb/config |

Double counting is removed (`vv ⊃ wz`, `ttv ⊃ ttz, ttw`), and the LO WZ/ZZ pythia
samples stand in for the NLO samples missing in cmsdb for 2022/23 (logged as
`unverified_settings` at config build).

---

## Categories

Three orthogonal axes (`azh/config/categories.py`, `azh/production/categories.py`):

```
multiplicity:  2l (=100)  |  3l (=200)
flavor:        2e (=10)   |  2mu (=20)                           Z candidate flavor
region:        wz_cr (=4000) | sr_1b (=5000) | sr_2b (=6000)     b-jet count (3l only)
```

IDs are additive (`3l__2e__sr_2b` = 6210).

- **Validation:** `2l__2e`, `2l__2mu`: no baseline, high-statistics DY for Z-peak
  and lepton calibration checks. Unblinded.
- **Analysis:** `3l__*__<region>`: full baseline (Z window, MET, ≥ 4 jets) plus the
  b-jet split. Signal regions are blinded in data.

Tunable cuts live in the categories, so they can be retuned by rerunning
production only.

---

## Production

### Status of `v9`

| Era | MC: nominal + 8 lepton passes | Data | Missing |
|---|---|---|---|
| 2022preEE | 19/19 | 4/4 | `data_singlemu_c` (early 2022C muons; needs cmsdb) |
| 2022postEE | 19/19 | 6/6 | |
| 2023preBPix | 20/20 | 8/8 | |
| 2023postBPix | 20/20 | 4/4 | |
| 2024 | 27/27 | 14/14 | |

Permanent footprint: about **3.8 TB** (merged reduced events + produced columns).
Data/MC first look (2023postBPix, 2l): m_ℓℓ data/MC ≈ 1.00 (μμ) and 0.98 (ee);
DY under-predicts ≥ 3 jets; data excess in PuppiMET at 60–200 GeV (to investigate).

### Running a production

Settings in `~/azh_prod_vars.sh` (source after the environment):

```bash
SHIFTS="nominal,e_scale_*,e_smear_*,mu_scale_*,mu_resol_*"
COMMON="--version v9 --workflow htcondor --cf.CalibrateEvents-workflow htcondor --cf.SelectEvents-workflow htcondor --cf.ReduceEvents-workflow htcondor --cf.MergeReducedEvents-workflow htcondor --cf.CalibrateEvents-htcondor-memory 9"
# NAF allows 5000 queued jobs per user: keep (workers x 500) well below
CAPS="--cf.CalibrateEvents-parallel-jobs 500 --cf.SelectEvents-parallel-jobs 500 --cf.ReduceEvents-parallel-jobs 500 --cf.MergeReducedEvents-parallel-jobs 500 --cf.ProduceColumns-parallel-jobs 500"
```

```bash
source ~/azh_env.sh && source ~/azh_prod_vars.sh
echo "${COMMON:0:20}"     # must print text: an empty variable silently drops --version etc.
nohup law run cf.ProduceColumnsWrapper --configs config_2024 --datasets "dy_*" \
    --shifts "$SHIFTS" $COMMON $CAPS --workers 3 > logs_condor/<name>.log 2>&1 &
```

- MC calibration needs **9 GB** (measured peak ~7.3 GB on 2024 tt̄); data runs with 4 GB.
- Launch long runs inside `tmux` on one login node, and start `krenew` there.
- Never run two law processes on the same tasks at once.

### Disk: stage and clean up

Temporaries (calibration, selection, unmerged reduced events) are several times the
permanent outputs; running everything at once does not fit in 5 TB. Process in
stages (by era, or by dataset for the large DY samples, `--workers 1` for the
largest), and clean up each completed dataset immediately:

```bash
bash ~/azh_cleanup_complete.sh config_2024      # lists temporaries of datasets complete in all 9 passes
xargs rm -rf < /data/dust/user/$(whoami)/del_complete.txt
du -sh $CF_DATA                                 # real usage (my-dust-quota lags by hours)
```

**A full disk corrupts files** (see [Troubleshooting](#troubleshooting)). Stay below
~85% and stop runs before the limit.

### Helper scripts

| Script | Purpose |
|---|---|
| `~/azh_env.sh` | environment setup |
| `~/azh_prod_vars.sh` | `SHIFTS`, `COMMON`, `CAPS` |
| `~/azh_status.sh` | credentials, law processes, queue, storage, logs, per-pass completeness |
| `~/azh_cleanup_complete.sh` | lists temporaries of completed datasets |
| `scripts/quick_checks.py` | metadata-only consistency check of the whole store |

(Move the `~/azh_*.sh` scripts into `scripts/` so they are versioned with the code.)

---

## Quick checks

All read metadata or small samples only: minutes, not hours.

```bash
source ~/azh_env.sh
python scripts/quick_checks.py                       # all eras; exit code 1 on any FAIL
```

Per config, it checks that every merged and produced file is non-empty with a
readable footer, that every MC dataset has all 9 passes and every data dataset
nominal, that merged and produced row counts agree, that the lepton-shift passes
are within ±5% of nominal in event count, that `normalization_weight` is finite and
non-zero, and it prints data events per fb⁻¹ (≈ 1.38–1.46 M per fb⁻¹ in `v9`).

Damage *inside* a file (corrupt data pages) is invisible to footer reads, but a
completed `cf.ProduceColumns` has read all of its merged inputs, and filling
histograms reads all produced outputs, so it surfaces there.

Physics sanity checks with expected `v9` values (data, `2l` categories):

| Check | Expected |
|---|---|
| Z peak, ee / μμ | 90.75 / 91.25 GeV in every era |
| Duplicate events across Muon and EGamma PDs | 0 |
| Data events in signal-region categories (IDs 5000–6999) | 0 |
| min PuppiMET in selected events | ≥ 0 |
| ee/μμ yield ratio | 0.64 (2022pre) falling to 0.49 (2024); reproduced by MC in 2023post |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `id: dummy_job_id, error: unknown job id` | submission rejected: expired Kerberos ticket, or more than 5000 queued jobs | renew (`kinit && aklog`), or lower `--workers` / `parallel-jobs` |
| `AUTHENTICATE ... Failed to authenticate` | expired Kerberos ticket | `kinit && aklog` on the law node, for the cache law uses |
| `voms-proxy-info failed` / `Couldn't find a valid proxy` | proxy expired or unreadable (AFS) | new proxy on dust (see [Credentials](#credentials)) |
| `tolerance exceeded` immediately, nothing submitted | stale job record from an earlier run | delete that workflow's `htcondor_jobs_*.json` (path: `law run <task> ... --print-output 0`) |
| `JSONDecodeError: Expecting value` | empty job record (written during a full disk) | delete that empty `htcondor_jobs_*.json` |
| `Parquet file size is 0 bytes` / `magic bytes not found` / `Couldn't deserialize thrift` | damaged output (full disk) | find with `find ... -size 0` and footer or full reads; delete; remove the record of the task that reads it; relaunch |
| Held jobs, `Transfer output files failure ... Disk quota exceeded` | full disk | `condor_rm -constraint 'Owner == "<user>" && JobStatus == 5'` |
| `task family 'cf.X' not found in index` | law index broken (full disk at setup) | `law index --verbose` |
| `ImportError` from plotting; `law` under `/cvmfs/.../CMSSW_*` | CMSSW environment active | fresh shell without `cmsenv` |
| `ENOSPC` in `/tmp` | shared login-node `/tmp` full | `TMPDIR` on dust |
| `pgrep`, `jobs`, `condor_q` show nothing | different login node | `ssh` to the launch node; `condor_q -global` |
| Lists in `/tmp` missing | `/tmp` is per node | write lists to `/data/dust/...` |
| Connection drops during long commands | idle/remote timeouts | `tmux`; `ServerAliveInterval 60` in `~/.ssh/config`; `nohup` for long scans |

**Recovering from a full disk:** stop all law processes and `condor_rm` all jobs;
free space; find empty files (`find <store>/... <jobs>/... -size 0`), truncated
parquet files (footer reads of recently written files) and empty job records;
delete them; rebuild the law index if needed; relaunch.

---

## Statistical tools (combine)

`CMSSW_16_0_0` (el9_amd64_gcc13) with HiggsAnalysis/CombinedLimit **v11.1.0** and
CombineHarvester in `/data/dust/user/$(whoami)/CMSSW_16_0_0`. Use it **only in a
separate shell** (`cmsenv` puts CMSSW's own `law` and Python first in the path).

---

## Open items

**Production**
- Jet/MET shift passes (26 production passes per MC dataset) → histograms → delete
  the shifted production outputs, era by era.
- Full data/MC plots for all eras with all uncertainties.

**Waiting on cmsdb / the PI**
- cmsdb fork: `data_singlemu_c` (2022C), tZq, NLO WZ/ZZ and tribosons (2022/23),
  ttW (mg35x), theory cross sections.
- 2023 ttZ (m > 50) extensions: 10× the nominal statistics (2023preBPix: 5 → 60
  files); include?
- Zγ, trigger turn-on (keep vs. plateau cut), signal samples, b-tag scheme.

**Physics follow-ups**
- DY correction at high jet multiplicity; PuppiMET excess at 60–200 GeV; ee/μμ
  trend across eras in data/MC.
- ML: available inputs are the kept columns (CandJet with PNet/UParT score,
  leptons with ID/iso flags, PuppiMET, gen objects) plus produced columns; other
  taggers, lepton MVA scores, taus/photons/fat jets would need a reprocessing,
  so add them to `keep_columns` before the next one.

**Housekeeping**
- `azh/production/trigger.py` (debug producer, unused), `deepcsv` working points
  (Run 2), template comments in `analysis_azh_run3.py`.

---

## Resources

[columnflow](https://github.com/columnflow/columnflow) ·
[law](https://github.com/riga/law) ·
[order](https://github.com/riga/order) ·
[cmsdb](https://github.com/uhh-cms/cmsdb) ·
[muonscarekit](https://gitlab.cern.ch/cms-muonPOG/muonscarekit) ·
[NAF documentation](https://naf.desy.de)
