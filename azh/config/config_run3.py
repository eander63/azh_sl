"""
Configuration of the Run 3 AZH analysis.
"""

from __future__ import annotations

import os
import re
import logging
from typing import Set

import yaml
from scinum import Number
import order as od
import law
import functools

from columnflow.util import DotDict
from cmsdb.util import add_decay_process
from azh.config.analysis_azh_run3 import analysis_azh
from azh.config.categories import add_categories_selection, add_categories_production
from azh.config.variables import add_variables
from columnflow.config_util import (
    get_root_processes_from_campaign, get_shifts_from_sources
)

thisdir = os.path.dirname(os.path.abspath(__file__))
# repository root; the pinned golden JSONs live in <repo>/data/lumi/
repo_dir = os.path.dirname(os.path.dirname(thisdir))

logger = logging.getLogger(__name__)

def modify_cmsdb_processes():
    from cmsdb.processes import (
        dy, dy_m10to50, dy_m50toinf, dy_m50toinf_0j, dy_m50toinf_1j, dy_m50toinf_2j,dy_m50toinf_3j,dy_m50toinf_4j,
    )
    decay_map = {
        "lf": {
            "name": "lf",
            "id": 50,
            "label": "(lf)",
            "br": -1,
        },
        "hf": {
            "name": "hf",
            "id": 60,
            "label": "(hf)",
            "br": -1,
        },
    }

    for dy_proc_inst in (
        dy, dy_m10to50, dy_m50toinf, dy_m50toinf_0j, dy_m50toinf_1j, dy_m50toinf_2j,dy_m50toinf_3j,dy_m50toinf_4j,
    ):
        add_production_mode_parent = dy_proc_inst.name != "dy"
        for flavour in ("hf", "lf"):
            add_decay_process(
                dy_proc_inst,
                decay_map[flavour],
                add_production_mode_parent=add_production_mode_parent,
                name_func=lambda parent_name, decay_name: f"{parent_name}_{decay_name}",
                label_func=lambda parent_label, decay_label: f"{parent_label} {decay_label}",
                xsecs=None,
                aux={"flavour": flavour},
            )

modify_cmsdb_processes()

def get_dataset_lfns(
    dataset_inst: od.Dataset,
    shift_inst: od.Shift,
    dataset_key: str,
) -> list[str]:
    """
    Custom LFN retrieval using a global DAS query.
    Filters out broken files registered in cmsdb.
    """
    import subprocess
    broken_files = dataset_inst[shift_inst.name].get_aux("broken_files", [])
    query = f"file dataset={dataset_key}"
    result = subprocess.run(
        ["/cvmfs/cms.cern.ch/common/dasgoclient", f"--query={query}"],
        capture_output=True,
        text=True,
    )
    lfns = [
        line.strip() for line in result.stdout.strip().split("\n")
        if line.strip() and line.strip() not in broken_files
    ]
    return lfns

def add_config(
    analysis: od.Analysis,
    campaign: od.Campaign,
    config_name: str | None = None,
    config_id: int | None = None,
    limit_dataset_files: int | None = None,
) -> od.Config:
    assert campaign.x.year in [2022, 2023, 2024]
    if campaign.x.year == 2022:
        assert campaign.x.EE in ["pre", "post"]
    elif campaign.x.year == 2023:
        assert campaign.x.BPix in ["pre", "post"]
    year = campaign.x.year
    year2 = year % 100
    corr_postfix = ""
    if year == 2022:
        corr_postfix = f"{campaign.x.EE}EE"
    elif year == 2023:
        corr_postfix = f"{campaign.x.BPix}BPix"
    # 2024 is a single, undivided era -> corr_postfix stays ""
    # canonical era key used throughout this function: one of
    # "2022preEE", "2022postEE", "2023preBPix", "2023postBPix", "2024"
    era_key = f"{year}{corr_postfix}"

    implemented_years = [2022, 2023, 2024]

    if year not in implemented_years:
        raise NotImplementedError(f"year {year} is not implemented")

    cfg_unverified = []

    procs = get_root_processes_from_campaign(campaign)

    cfg = analysis_azh.add_config(campaign, name=config_name, id=config_id)
    # use custom get_dataset_lfns function
    cfg.x.get_dataset_lfns = get_dataset_lfns
    cfg.x.get_dataset_lfns_sandbox = f"bash::$CF_BASE/sandboxes/venv_columnar_dev.sh"

    labels = {
        "tt": "$t\\bar{t}$",
        "tzq": "tZq",
        "vvv": "VVV",
    }

    colors = {
        "dy_hf": "#C7FF33",
        "dy_lf": "#FBFF36",
        "dy_ee": "#C7FF33",
        "dy_mumu": "#FBFF36",
        "dy_tautau": "#9ACD32",
        "data": "#000000",  # black
        "tt": "#E04F21",  # red
        "tzq": "#5E8FFC",  # blue
        "ttz": "#6B375A",
        "ttw": "#346532",  
        "w_lnu": "#82FF28",  # green
        "tth": "#FFA500",  # orange
        "higgs": "#984ea3",  # purple
        "st": "#3E00FB",  # dark purple
        "wz": "#FF6B9D",  # hot pink for WZ
        "zz": "#B900FC",
        "ww": "#7A00A6",
        "vvv": "#3E6676",
        "other": "#999999",  # grey
    }

    # Top-level plotting processes. No process may contain another one in this
    # list (the old list had vv > wz and ttv > ttz/ttw, which double counts in
    # stacked plots); tests/preflight_static.py checks this.
    process_names = [
        "dy_hf", "dy_lf", "tt",
        "ttz", "ttw", "tth", "tzq",
        "st", "w_lnu", "wz", "zz", "ww", "vvv", "data",
    ]
    # processes that only exist once the cmsdb fork provides them
    optional_processes = {"tzq", "vvv"}

    # 2024 has no lepton-inclusive DY sample and no hf/lf children for the
    # flavour-split ones, so register dy_ee / dy_mumu / dy_tautau instead of
    # dy_hf / dy_lf. See the dataset list and the is_dy tagging below.
    if year == 2024:
        process_names = [p for p in process_names if p not in ("dy_hf", "dy_lf")]
        process_names = ["dy_ee", "dy_mumu", "dy_tautau"] + process_names

    def _has_proc(name):
        try:
            procs.get(name)
            return True
        except Exception:
            return False

    missing_processes = [p for p in process_names if p in optional_processes and not _has_proc(p)]
    process_names = [p for p in process_names if p not in missing_processes]

    for process_name in process_names:
        cfg.add_process(procs.get(process_name))
        cfg.get_process(process_name).color1 = colors.get(process_name, "#aaaaaa")
        cfg.get_process(process_name).color2 = colors.get(process_name, "#000000")
        cfg.get_process(process_name).label = labels.get(process_name)
    # helper to enable processes / datasets only for a specific era
    def _match_era(
        *,
        run: int | set[int] | None = None,
        year: int | set[int] | None = None,
        postfix: str | set[int] | None = None,
        tag: str | set[str] | None = None,
        nano: int | set[int] | None = None,
        sync: bool = False,
    ) -> bool:
        return (
            (run is None or campaign.x.run in law.util.make_set(run)) and
            (year is None or campaign.x.year in law.util.make_set(year)) and
            (postfix is None or campaign.x.postfix in law.util.make_set(postfix)) and
            (tag is None or campaign.has_tag(tag, mode=any)) and
            (nano is None or campaign.x.version in law.util.make_set(nano))
        )

    def if_era(*, values: list[str | None] | None = None, **kwargs) -> list[str]:
        return list(filter(bool, values or [])) if _match_era(**kwargs) else []

    def if_not_era(*, values: list[str | None] | None = None, **kwargs) -> list[str]:
        return list(filter(bool, values or [])) if not _match_era(**kwargs) else []

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------
    # MC backgrounds follow AN-2022/158 Sec. 3 (Table 20 lists the SR yields):
    # ttZ, ttW, ttH, tZq, WZ, ZZ, VVV, plus DY/ttbar/single top/W+jets as the
    # nonprompt proxy (no data-driven fakes in this round).
    #
    # Several of these are not yet in the cmsdb fork for every era; the DAS
    # keys are listed in PREFLIGHT_CHANGES.md. Rather than silently running
    # without them, every name in `required_mc` is added when the campaign has
    # it and otherwise recorded in cfg.x.missing_datasets, which
    # tests/preflight_static.py reports as a FAIL.
    required_mc = [
        # DY: 2022/23 inclusive amcatnlo; 2024 only has flavour-split samples
        # (m10to50 only as powheg there).
        *if_not_era(year=2024, values=["dy_m50toinf_amcatnlo", "dy_m10to50_amcatnlo"]),
        *if_era(year=2024, values=[
            "dy_ee_m50toinf_amcatnlo", "dy_mumu_m50toinf_amcatnlo", "dy_tautau_m50toinf_amcatnlo",
            "dy_ee_m10to50_powheg", "dy_mumu_m10to50_powheg", "dy_tautau_m10to50_powheg",
        ]),
        # ttbar
        "tt_sl_powheg", "tt_dl_powheg", "tt_fh_powheg",
        # ttZ (Z->ll); the MLL-50 ext1 samples are extra keys of the same dataset
        "ttz_zll_m4to50_amcatnlo", "ttz_zll_m50toinf_amcatnlo",
        # ttW (W->lnu, TTLNu-1Jets mg35x). Deliberately NOT the 2022preEE
        # "ttw_amcatnlo": that dataset is TTLNu but is assigned the inclusive ttW
        # cross section (0.690 pb instead of 0.225 pb), i.e. overscaled 3.07x.
        "ttw_wlnu_amcatnlo",
        # ttH
        "tth_hbb_powheg", "tth_hnonbb_powheg",
        # tZq (TZQB-Zto2L-4FS_MLL-30)
        "tzq_zll_4f_amcatnlo",
        # single top (2024 splits t-channel by top decay; only leptonic matters)
        *if_not_era(year=2024, values=["st_tchannel_t_4f_powheg", "st_tchannel_tbar_4f_powheg"]),
        *if_era(year=2024, values=["st_tchannel_t_lep_4f_powheg", "st_tchannel_tbar_lep_4f_powheg"]),
        "st_twchannel_t_sl_powheg", "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg", "st_twchannel_tbar_dl_powheg",
        # dibosons: NLO powheg WZ->3lnu and ZZ->4l (with LHE weights); WW stays
        # pythia (it only matters for the 2l region)
        "wz_wlnu_zll_powheg", "zz_zll_zll_powheg", "ww_pythia",
        # tribosons
        "www_4f_amcatnlo", "wwz_4f_amcatnlo", "wzz_amcatnlo", "zzz_amcatnlo",
        # W+jets: no inclusive sample in 2024 (jet/pt-binned ones need stitching)
        *if_not_era(year=2024, values=["w_lnu_amcatnlo"]),
    ]
    # LO pythia dibosons, used only if the NLO samples are not in cmsdb yet
    # (still reported as missing, so the substitution cannot go unnoticed)
    mc_fallbacks = {"wz_wlnu_zll_powheg": "wz_pythia", "zz_zll_zll_powheg": "zz_pythia"}

    # Data: Muon and EGamma PDs only. MuonEG is not used: with the single-lepton
    # trigger OR it carries no events the other two do not (cross triggers were
    # measured to add < 0.1% of the 3l acceptance on ttZ MC).
    # 2022C: the Muon PD only starts at run 356426; runs 355862-356386 are in
    # SingleMuon, which is required here (the trigger OR has no dimuon path, so
    # DoubleMuon is not needed). Muon and SingleMuon cover disjoint runs.
    required_data = [
        *if_era(year=2022, tag="preEE", values=[
            "data_singlemu_c", "data_mu_c", "data_mu_d", "data_egamma_c", "data_egamma_d",
        ]),
        *if_era(year=2022, tag="postEE", values=[
            "data_mu_e", "data_mu_f", "data_mu_g", "data_egamma_e", "data_egamma_f", "data_egamma_g",
        ]),
        *if_era(year=2023, tag="preBPix", values=[
            *[f"data_mu_c{i}" for i in range(1, 5)], *[f"data_egamma_c{i}" for i in range(1, 5)],
        ]),
        *if_era(year=2023, tag="postBPix", values=[
            "data_mu_d1", "data_mu_d2", "data_egamma_d1", "data_egamma_d2",
        ]),
        # 2024: the EGamma PD is called data_e_* in cmsdb
        *if_era(year=2024, values=[
            *[f"data_mu_{e}" for e in "cdefghi"], *[f"data_e_{e}" for e in "cdefghi"],
        ]),
    ]

    dataset_names = []
    cfg.x.missing_datasets = []
    for name in required_mc + required_data:
        if campaign.has_dataset(name):
            dataset_names.append(name)
            continue
        cfg.x.missing_datasets.append(name)
        fallback = mc_fallbacks.get(name)
        if fallback and campaign.has_dataset(fallback):
            dataset_names.append(fallback)
            cfg_unverified.append(f"{name} missing from cmsdb, using LO fallback {fallback}")

    for dataset_name in dataset_names:
        dataset = cfg.add_dataset(campaign.get_dataset(dataset_name))
        if limit_dataset_files:
            for info in dataset.info.values():
                if info.n_files > limit_dataset_files:
                    info.n_files = limit_dataset_files
        # ttbar only -- a plain startswith("tt") also caught ttZ, ttW and ttH
        if dataset.name.startswith(("tt_sl", "tt_dl", "tt_fh")):
            dataset.add_tag({"is_ttbar"})
        if dataset.name.startswith("dy"):
            if not re.match(r"^dy_(ee|mumu|tautau)_", dataset.name):
                dataset.add_tag({"is_dy"})
        if dataset.name.startswith("azh"):
            dataset.add_tag({"is_signal"})
        if dataset.name.startswith(("data_mu", "data_singlemu")):
            dataset.add_tag("mu")
        if dataset.name.startswith("data_egamma") or dataset.name.startswith("data_e_"):
            dataset.add_tag("egamma")
        # For 2023, data JEC keys have no run-dependent segment in the JSON
        if dataset.name.startswith("data") and year == 2023:
            dataset.set_aux("jec_era", "")
        # 2024 ships a single combined CDE-reprocessing + FGHI-prompt JEC key,
        # so the run-dependent segment is empty here too.
        if dataset.name.startswith("data") and year == 2024:
            dataset.set_aux("jec_era", "")

    # ------------------------------------------------------------------
    # Era-agnostic dataset patches (apply to every era)
    # ------------------------------------------------------------------
    # tag pythia diboson samples that have no LHEScaleWeight
    for ds_name in ["ww_pythia", "wz_pythia", "zz_pythia"]:  # LO pythia, no LHE weights
        if cfg.has_dataset(ds_name):
            cfg.get_dataset(ds_name).add_tag("no_lhe_weights")
    # remove non-nominal dataset infos (extension, hdamp, tune variations)
    # to avoid indexing errors when running from scratch
    for ds_name in [
        "st_twchannel_t_sl_powheg", "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg", "st_twchannel_tbar_dl_powheg",
        "tt_sl_powheg", "tt_dl_powheg", "tt_fh_powheg",
    ]:
        if not cfg.has_dataset(ds_name):
            continue
        ds = cfg.get_dataset(ds_name)
        for info_name in list(ds.info.keys()):
            if info_name != "nominal":
                del ds.info[info_name]

    # ------------------------------------------------------------------
    # Era-specific dataset overrides
    # ------------------------------------------------------------------
    # These are workarounds for wrong DAS keys / wrong n_files in the
    # cmsdb campaign objects. They are *era-specific* — the values below
    # were derived for 2022preEE and would corrupt other eras if applied
    # blindly. For each new era, either (a) confirm cmsdb already has the
    # right values and leave the branch empty, or (b) re-derive via DAS
    # and add an analogous block.
    if year == 2022 and campaign.x.EE == "pre":
        if cfg.has_dataset("wz_pythia"):
            cfg.get_dataset("wz_pythia").get_info("nominal").n_files = 45
        if cfg.has_dataset("st_twchannel_tbar_sl_powheg"):
            cfg.get_dataset("st_twchannel_tbar_sl_powheg").get_info("nominal").n_files = 49
        if cfg.has_dataset("st_twchannel_tbar_dl_powheg"):
            cfg.get_dataset("st_twchannel_tbar_dl_powheg").get_info("nominal").n_files = 24
        # fix wrong DAS keys for ttz datasets in cmsdb (v3 not v2)
        if cfg.has_dataset("ttz_zll_m50toinf_amcatnlo"):
            cfg.get_dataset("ttz_zll_m50toinf_amcatnlo").get_info("nominal").keys = {
                "/TTLL_MLL-50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3/NANOAODSIM"
            }
            cfg.get_dataset("ttz_zll_m50toinf_amcatnlo").get_info("nominal").n_files = 7
        if cfg.has_dataset("ttz_zll_m4to50_amcatnlo"):
            cfg.get_dataset("ttz_zll_m4to50_amcatnlo").get_info("nominal").keys = {
                "/TTLL_MLL-4to50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3/NANOAODSIM"
            }
            cfg.get_dataset("ttz_zll_m4to50_amcatnlo").get_info("nominal").n_files = 21
        # DY DAS key fixups
        if cfg.has_dataset("dy_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("dy_m50toinf_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v5/NANOAODSIM"}
        if cfg.has_dataset("dy_m10to50_amcatnlo"):
            ds = cfg.get_dataset("dy_m10to50_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v4/NANOAODSIM"}
        # fix wrong DAS key for dy_m50toinf_1j_madgraph in cmsdb
        if cfg.has_dataset("dy_m50toinf_1j_madgraph"):
            ds = cfg.get_dataset("dy_m50toinf_1j_madgraph")
            for info in ds.info.values():
                info.keys = {"/DYto2L-4Jets_MLL-50_1J_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v3/NANOAODSIM"}
    elif year == 2022 and campaign.x.EE == "post":
        # cmsdb has these samples pinned to -v2, but DAS shows the
        # campaign was reprocessed: DY -> -v5, TTZ -> -v3. Override.
        if cfg.has_dataset("dy_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("dy_m50toinf_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v5/NANOAODSIM"}
                info.n_files = 1682
        if cfg.has_dataset("dy_m10to50_amcatnlo"):
            ds = cfg.get_dataset("dy_m10to50_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v5/NANOAODSIM"}
                info.n_files = 1573
        if cfg.has_dataset("ttz_zll_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("ttz_zll_m50toinf_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v3/NANOAODSIM"}
            ds.get_info("nominal").n_files = 50
        if cfg.has_dataset("ttz_zll_m4to50_amcatnlo"):
            # cmsdb also has a trailing-space bug in this key (postEE);
            # setting it explicitly cleans both issues at once.
            ds = cfg.get_dataset("ttz_zll_m4to50_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-4to50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v3/NANOAODSIM"}
            ds.get_info("nominal").n_files = 40
    elif year == 2023 and campaign.x.BPix == "pre":
        if cfg.has_dataset("dy_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("dy_m50toinf_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v14-v2/NANOAODSIM"}
                info.n_files = 506
        if cfg.has_dataset("dy_m10to50_amcatnlo"):
            ds = cfg.get_dataset("dy_m10to50_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v14_ext1-v4/NANOAODSIM"}
                info.n_files = 657
        if cfg.has_dataset("ttz_zll_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("ttz_zll_m50toinf_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v3/NANOAODSIM"}
            ds.get_info("nominal").n_files = 5
        if cfg.has_dataset("ttz_zll_m4to50_amcatnlo"):
            ds = cfg.get_dataset("ttz_zll_m4to50_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-4to50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23NanoAODv12-130X_mcRun3_2023_realistic_v15-v4/NANOAODSIM"}
            ds.get_info("nominal").n_files = 18
    elif year == 2023 and campaign.x.BPix == "post":
        if cfg.has_dataset("dy_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("dy_m50toinf_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2-v4/NANOAODSIM"}
                info.n_files = 312
        if cfg.has_dataset("dy_m10to50_amcatnlo"):
            ds = cfg.get_dataset("dy_m10to50_amcatnlo")
            for info in ds.info.values():
                info.keys = {"/DYto2L-2Jets_MLL-10to50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v2_ext1-v4/NANOAODSIM"}
                info.n_files = 342
        if cfg.has_dataset("ttz_zll_m50toinf_amcatnlo"):
            ds = cfg.get_dataset("ttz_zll_m50toinf_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v3/NANOAODSIM"}
            ds.get_info("nominal").n_files = 7
        if cfg.has_dataset("ttz_zll_m4to50_amcatnlo"):
            ds = cfg.get_dataset("ttz_zll_m4to50_amcatnlo")
            ds.get_info("nominal").keys = {"/TTLL_MLL-4to50_TuneCP5_13p6TeV_amcatnlo-pythia8/Run3Summer23BPixNanoAODv12-130X_mcRun3_2023_realistic_postBPix_v6-v3/NANOAODSIM"}
            ds.get_info("nominal").n_files = 7
        if cfg.has_dataset("tth_hnonbb_powheg"):
            cfg.get_dataset("tth_hnonbb_powheg").get_info("nominal").n_files = 135

    # default calibrator, selector, producer, ml model and inference model
    cfg.x.default_calibrator = "skip_jecunc"
    cfg.x.default_selector = "default"
    cfg.x.default_producer = "default"
    cfg.x.default_reducer = "cf_default"
    cfg.x.default_hist_producer = "all_weights"
    cfg.x.default_inference_model = "default"
    cfg.x.default_categories = ["cat_incl"]
    cfg.x.default_variables = ["jet1_pt"]

    # process groups for conveniently looping over certain processs
    # (used in wrapper_factory and during plotting)
    cfg.x.process_groups = {
        "all": ["*"],
    }

    # dataset groups for conveniently looping over certain datasets
    # (used in wrapper_factory and during plotting)
    cfg.x.dataset_groups = {
        "all": ["*"],
    }

    # category groups for conveniently looping over certain categories
    # (used during plotting)
    cfg.x.category_groups = {
        "default": ["incl"],
    }

    # variable groups for conveniently looping over certain variables
    # (used during plotting)
    cfg.x.variable_groups = {
        "default": ["cf_n_jet", "jet1_pt"],
    }

    # shift groups for conveniently looping over certain shifts
    # (used during plotting)
    cfg.x.shift_groups = {
        "jer": ["nominal", "jer_up", "jer_down"],
    }

    # selector step groups for conveniently looping over certain steps
    # (used in cutflow tasks)
    cfg.x.selector_step_groups = {
        "default": ["azh"],
    }

    cfg.x.selector_step_labels = {
        "json": r"JSON",
        "trigger": r"Trigger",
        "met_filter": r"MET filters",
    }

    # plotting settings groups
    cfg.x.general_settings_groups = {
        "default_norm": {"shape_norm": True, "yscale": "log"},
    }
    cfg.x.process_settings_groups = {
        "Jet": r"$N_{jets}^{AK4} \geq 3$",
    }

    cfg.x.variable_settings_groups = {

    }

    # ------------------------------------------------------------------
    # Luminosity (inverse pb)
    # ------------------------------------------------------------------
    # Recorded luminosity of exactly the runs this config processes, from
    #   brilcalc lumi -c web --normtag normtag_PHYSICS.json -u /pb
    #            -i <current golden JSON> --begin <first> --end <last>
    # with the golden JSON pinned below (the post-TrkML2026-review version;
    # the local files are md5-identical to the DQM certification server).
    # First/last runs are the union of this config's Muon and EGamma datasets.
    # Era B of each year is in the golden JSON but not processed, which is why
    # the eras sum to less than LUM's year totals (34.75 / 28.40 / 110.11 /fb).
    #
    #   config      runs            recorded /pb
    #   2022pre     355862-357900     7989.5
    #   2022post    359356-362760    26674.9
    #   2023pre     367094-369694    17964.2   (was 18605: matched neither JSON)
    #   2023post    369844-370790     9676.7   (was 9693: old JSON)
    #   2024        379415-386951   109815.6 - 105.3 = 109710.3
    #
    # 2024: golden runs 386615-386617 (105.3 /pb) exist only in prompt-reco
    # datasets, not in the MINIv6NANOv15 reprocessing used here, so no data
    # event can come from them; they are subtracted.
    #
    # Uncertainties: the LUM POG nuisances for a 2022+2023+2024 combination,
    # verbatim (lnN, relative):
    #   lumi_1: 2022 1.38%, 2023 0.17%, 2024 0.20%
    #   lumi_2:             2023 1.27%, 2024 0.68%
    #   lumi_3:                         2024 1.44%
    # These reproduce the LUM covariance matrix. Both eras of a year share the
    # year's values (the calibration is per year).
    lumi_uncertainties = {
        2022: {"lumi_1": 0.0138j},
        2023: {"lumi_1": 0.0017j, "lumi_2": 0.0127j},
        2024: {"lumi_1": 0.0020j, "lumi_2": 0.0068j, "lumi_3": 0.0144j},
    }[year]
    lumi_values = {
        "2022preEE": 7989.5,
        "2022postEE": 26674.9,
        "2023preBPix": 17964.2,
        "2023postBPix": 9676.7,
        "2024": 109710.3,
    }
    cfg.x.luminosity = Number(lumi_values[era_key], lumi_uncertainties)

    # MET filters
    cfg.x.met_filters = {
    "Flag.goodVertices",
    "Flag.globalSuperTightHalo2016Filter",
    "Flag.EcalDeadCellTriggerPrimitiveFilter",
    "Flag.BadPFMuonFilter",
    "Flag.BadPFMuonDzFilter",
    "Flag.hfNoisyHitsFilter",
    "Flag.eeBadScFilter",
    "Flag.ecalBadCalibFilter",
    # HBHENoiseFilter / HBHENoiseIsoFilter: removed, "no longer needed" in Run 3
    }

    # minimum bias cross section in mb (milli) for creating PU weights, values from
    # https://twiki.cern.ch/twiki/bin/view/CMS/PileupJSONFileforData?rev=45#Recommended_cross_section
    cfg.x.minbias_xs = Number(69.2, 0.046j)

    # whether to validate the number of obtained LFNs in GetDatasetLFNs
    cfg.x.validate_dataset_lfns = False

    # jec configuration
    # https://twiki.cern.ch/twiki/bin/view/CMS/JECDataMC?rev=201
    if year == 2022:
        jerc_postfix = ""
        if year == 2022 and campaign.x.EE == "post":
            jerc_postfix = "EE"

        jerc_campaign = f"Summer{year2}{jerc_postfix}_22Sep2023"

    if year ==2023:
        jerc_postfix = ""
        if campaign.x.BPix == "post":
            jerc_postfix = "BPix"

        jerc_campaign = f"Summer{year2}{jerc_postfix}Prompt23"

    if year == 2024:
        jerc_postfix = ""
        jerc_campaign = f"Summer{year2}Prompt24"

    jet_type = "AK4PFPuppi"

    jer_campaign = jerc_campaign
    if year == 2023:
        jer_campaign += f"_Run{'Cv1234' if campaign.has_tag('preBPix') else 'D'}"

    # JES uncertainty sources.
    #
    # Era suffix used by JME for the era-specific Regrouped_* sources. This is
    # the JERC postfix, NOT the bare year: the files contain
    # Regrouped_Absolute_2022EE and Regrouped_Absolute_2023BPix. Verified
    # against all five campaigns by tests/validate_configs.py.
    jec_era = f"{year}{jerc_postfix}"

    JEC_SOURCES_TOTAL = ["Total"]
    JEC_SOURCES_REDUCED = [
        # correlated across years
        "Regrouped_Absolute",
        "Regrouped_BBEC1",
        "Regrouped_EC2",
        "Regrouped_FlavorQCD",
        "Regrouped_HF",
        "Regrouped_RelativeBal",
        # era-specific
        f"Regrouped_Absolute_{jec_era}",
        f"Regrouped_BBEC1_{jec_era}",
        f"Regrouped_EC2_{jec_era}",
        f"Regrouped_HF_{jec_era}",
        f"Regrouped_RelativeSample_{jec_era}",
    ]
    jec_uncertainty_sources = JEC_SOURCES_TOTAL

    # print(jerc_campaign)
    if not jerc_postfix == "BPix":
        cfg.x.jec = DotDict.wrap({
            "campaign": jerc_campaign,
            "version": {
                2016: "V7", 2017: "V5", 2018: "V5", 2022: "V4", 2023: "V4", 2024: "V5",
            }[year],
            "jet_type": jet_type,
            "levels": ["L1FastJet", "L2Relative", "L2L3Residual", "L3Absolute"],
            "levels_for_type1_met": ["L1FastJet"],
            "uncertainty_sources": jec_uncertainty_sources,
        })
    else:
        cfg.x.jec = DotDict.wrap({
            "campaign": jerc_campaign,
            "version": {
                2016: "V7", 2017: "V5", 2018: "V5", 2022: "V4", 2023: "V4", 2024: "V5",
            }[year],
            "jet_type": jet_type,
            "levels": ["L1FastJet", "L2Relative", "L2L3Residual", "L3Absolute"],
            "levels_for_type1_met": ["L1FastJet"],
            "uncertainty_sources": jec_uncertainty_sources,
        })

    # JER
    # https://twiki.cern.ch/twiki/bin/view/CMS/JetResolution?rev=107
    cfg.x.jer = DotDict.wrap({
        "campaign": jer_campaign,
            "version": {2022: "JRV2", 2023: "JRV3", 2024: "JRV2"}[year],
        "jet_type": jet_type,
    })


    # JEC uncertainty sources propagated to btag scale factors
    # (names derived from contents in BTV correctionlib file)
    cfg.x.btag_sf_jec_sources = [
        "",  # total
        "Absolute",
        "AbsoluteMPFBias",
        "AbsoluteScale",
        "AbsoluteStat",
        f"Absolute_{year}",
        "BBEC1",
        f"BBEC1_{year}",
        "EC2",
        f"EC2_{year}",
        "FlavorQCD",
        "Fragmentation",
        "HF",
        f"HF_{year}",
        "PileUpDataMC",
        "PileUpPtBB",
        "PileUpPtEC1",
        "PileUpPtEC2",
        "PileUpPtHF",
        "PileUpPtRef",
        "RelativeBal",
        "RelativeFSR",
        "RelativeJEREC1",
        "RelativeJEREC2",
        "RelativeJERHF",
        "RelativePtBB",
        "RelativePtEC1",
        "RelativePtEC2",
        "RelativePtHF",
        "RelativeSample",
        f"RelativeSample_{year}",
        "RelativeStatEC",
        "RelativeStatFSR",
        "RelativeStatHF",
        "SinglePionECAL",
        "SinglePionHCAL",
        "TimePtEta",
    ]

    # b-tag working points
    # BTV published no ParticleNet / DeepJet working points for 2024; the
    # recommended Run-3 2024 tagger is UParT (btagUParTAK4B). Hence the
    # per-era dicts below are None where a tagger is not supported, and
    # cfg.x.btag_default selects the era-appropriate one.
    btag_key = era_key

    cfg.x.btag_working_points = DotDict.wrap({
        "deepjet": {
            "loose": {
                "2022preEE": 0.0583, "2022postEE": 0.0614,"2023preBPix": 0.0479, "2023postBPix": 0.048, "2024": None,
            }[btag_key],
            "medium": {
                "2022preEE": 0.3086, "2022postEE": 0.3196,"2023preBPix": 0.2431, "2023postBPix": 0.2435, "2024": None,
            }[btag_key],
            "tight": {
                "2022preEE": 0.7183, "2022postEE": 0.7300,"2023preBPix": 0.6553, "2023postBPix": 0.6563, "2024": None,
            }[btag_key],
        },
        "particlenet": {
            "loose": {
                "2022preEE": 0.047, "2022postEE": 0.0499,"2023preBPix": 0.0358, "2023postBPix": 0.0359, "2024": None,
            }[btag_key],
            "medium": {
                "2022preEE": 0.245, "2022postEE": 0.2605,"2023preBPix": 0.1917, "2023postBPix": 0.1919, "2024": None,
            }[btag_key],
            "tight": {
                "2022preEE": 0.6734, "2022postEE": 0.6915,"2023preBPix": 0.6172, "2023postBPix": 0.6133, "2024": None,
            }[btag_key],
         },
        # 2024 only; values correspond to the "UParTAK4_wp_values" correction
        # set in the BTV correctionlib file.
        "upart": {
            "loose": {
                "2022preEE": None, "2022postEE": None, "2023preBPix": None, "2023postBPix": None,
                "2024": 0.0246,
            }[btag_key],
            "medium": {
                "2022preEE": None, "2022postEE": None, "2023preBPix": None, "2023postBPix": None,
                "2024": 0.1272,
            }[btag_key],
            "tight": {
                "2022preEE": None, "2022postEE": None, "2023preBPix": None, "2023postBPix": None,
                "2024": 0.4648,
            }[btag_key],
        },
    })

    # Era-appropriate tagger, consumed by jet_selection / higgs_reco / variables
    # instead of hard-coding a discriminator column. For 2022/23 this resolves to
    # exactly the previous behaviour (ParticleNet medium), so existing stores stay
    # valid and no version bump is needed for those configs.
    _btag_name = "upart" if year == 2024 else "particlenet"
    cfg.x.btag_default = DotDict.wrap({
        "name": _btag_name,
        "column": "btagUParTAK4B" if year == 2024 else "btagPNetB",
        "wp": cfg.x.btag_working_points[_btag_name].medium,
    })
    # NanoAOD v15 removed the Jet.jetId branch; the decision must be recomputed
    # from the PF energy fractions and multiplicities using the JME correctionlib
    # payload. v12 (2022/23) still stores the bitmap, so keep reading it there --
    # this resolves to the previous behaviour for those eras.
    cfg.x.jet_id = DotDict.wrap({
        "from_correctionlib": year == 2024,
        "tight": "AK4PUPPI_Tight",
        "tight_lepveto": "AK4PUPPI_TightLeptonVeto",
    })

    # btag weight configuration
    #
    # BTV ships no merged correction set for any Run 3 era -- every
    # btagging.json.gz provides *_comb (b/c) and *_light (udsg) separately --
    # so columnflow's btag_wp_weights, whose correction_set is a single string,
    # cannot be used directly. azh/production/btag.py derives from it and
    # replaces only the corrector lookup.
    from azh.production.btag import SplitBTagWPSFConfig
    from columnflow.selection.cms.btag import BTagWPCountConfig

    if year == 2024:
        btag_cs_heavy, btag_cs_light = "UParTAK4_comb", "UParTAK4_light"
    else:
        btag_cs_heavy, btag_cs_light = "particleNet_comb", "particleNet_light"

    # Binning of the MC tagging efficiency measurement, eff = N(pass WP)/N(total)
    # per (pt, |eta|, flavour) bin. AN-2022/158 Sec. 4.5 defines the same
    # quantity; the Run 2 analysis measured it in ttZ samples only, whereas the
    # dataset_groups below derive it per process group (see note in the wiring
    # doc). Bins that come out empty raise in the producer with the offending
    # (flavor, pt, abs_eta) values listed.
    # Plot styling. The data/MC ratio panel defaults to (0.72, 1.28) in columnflow
    # (plotting/plot_all.py); widen it so larger deviations stay visible.
    cfg.x.custom_style_config_groups = {
        "default": {"rax_cfg": {"ylim": (0.5, 1.5), "ylabel": "Data / MC"}},
    }
    cfg.x.default_custom_style_config = "default"

    cfg.x.btag_wp_count_config = BTagWPCountConfig(
        jet_name="Jet",
        btag_column=cfg.x.btag_default.column,
        btag_wps={"medium": cfg.x.btag_default.wp},
        pt_edges=(30, 50, 70, 100, 140, 200, 300, 10_000),
        abs_eta_edges=(0.0, 1.5, 2.5),
    )

    # Only the medium WP is corrected: catid_sr_1b / sr_2b / wz_cr all split on
    # medium-WP counts (AN Table 16). Adding working points the analysis never
    # cuts on would only dilute the per-bin statistics of the efficiency map.
    # Efficiency groups are built from the datasets actually in this config:
    # columnflow raises on a group member that is not a config dataset
    # (production/cms/btag.py), which crashed every 2024 single-top dataset.
    def _group(*prefixes):
        return [d.name for d in cfg.datasets if d.is_mc and d.name.startswith(prefixes)]
    btag_dataset_groups = [g for g in (
        _group("tt_"),
        _group("ttz_", "ttw_", "tth_", "tzq_"),
        _group("dy_"),
        _group("st_"),
        _group("wz_", "zz_", "ww_", "www_", "wwz_", "wzz_", "zzz_"),
        _group("w_lnu"),
    ) if g]

    cfg.x.btag_wp_sf_config = SplitBTagWPSFConfig(
        jet_name="Jet",
        btag_column=cfg.x.btag_default.column,
        correction_set=btag_cs_heavy,
        correction_set_light=btag_cs_light,
        btag_wps={"medium": cfg.x.btag_default.wp},
        weight_name="btag_weight",
        # BTV multi-era scheme: b/c and light separately, each split into a
        # component correlated across eras and one uncorrelated (per era in the
        # datacard). "bc_"/"light_" prefixes are resolved by SplitBTagWPCorrector.
        systs={
            f"{flav}_{d}_{kind}": f"{flav}_{d}_{kind}"
            for flav in ("bc", "light")
            for d in ("up", "down")
            for kind in ("correlated", "uncorrelated")
        },
        dataset_groups=btag_dataset_groups,
    )

    # names of electron correction sets and working points
    # (used in the electron_sf producer)
    if f"{year}{corr_postfix}" == "2022postEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "wp80iso")
    elif f"{year}{corr_postfix}" == "2022preEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoBCD", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoBCD", "wp80iso")
    elif f"{year}{corr_postfix}" == "2023postBPix":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptD", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2023PromptD", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptD", "wp80iso")
    elif f"{year}{corr_postfix}" == "2023preBPix":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptC", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptC", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2023PromptC", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptC", "wp80iso")
    elif era_key == "2024":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2024Prompt", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2024Prompt", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2024Prompt", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2024Prompt", "wp80iso")

    # electron scale & smearing (electronSS_EtDependent.json.gz, every era):
    # data use the compound "Scale" (all six stages), MC the plain
    # "SmearAndSyst" (smearing + escale/esmear uncertainties)
    cfg.x.electron_ss_names = ("Scale", "SmearAndSyst")

    # names of muon correction sets and working points
    # (used in the muon producer)
    # TightID muon SF chain (from muon_Z.json):
    # SF(TightID|Tracker) x SF(TightPFIso|TightID) x SF(IsoMu24|TightID+PFIso)
    # Valid down to ~15 GeV (Z tag-and-probe), matching our selection threshold
    cfg.x.muon_sf_id_names = ("NUM_TightID_DEN_TrackerMuons", era_key)
    cfg.x.muon_sf_iso_names = ("NUM_TightPFIso_DEN_TightID", era_key)
    cfg.x.muon_sf_trig_names = ("NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight", era_key)
    # Lower edge of the muon_Z.json ID/iso pT binning. 2022/23 start at 15;
    # 2024 extends to 10. Masking above the true floor silently assigns SF = 1
    # to muons that do have a measured scale factor.
    cfg.x.muon_sf_pt_min = 10.0 if year == 2024 else 15.0
    # era-branched HLT electron SF / efficiency keys (verified against
    # electronHlt.json: Path HLT_SF_Ele30_MVAiso80ID exists in every era)
    if f"{year}{corr_postfix}" == "2022preEE":
        cfg.x.electron_sf_trig_names = ("Electron-HLT-SF", "2022Re-recoBCD", "HLT_SF_Ele30_MVAiso80ID")
    elif f"{year}{corr_postfix}" == "2022postEE":
        cfg.x.electron_sf_trig_names = ("Electron-HLT-SF", "2022Re-recoE+PromptFG", "HLT_SF_Ele30_MVAiso80ID")
    elif f"{year}{corr_postfix}" == "2023preBPix":
        cfg.x.electron_sf_trig_names = ("Electron-HLT-SF", "2023PromptC", "HLT_SF_Ele30_MVAiso80ID")
    elif f"{year}{corr_postfix}" == "2023postBPix":
        cfg.x.electron_sf_trig_names = ("Electron-HLT-SF", "2023PromptD", "HLT_SF_Ele30_MVAiso80ID")
    elif era_key == "2024":
        cfg.x.electron_sf_trig_names = (
            "Electron-HLT-SF", "2024Prompt", "HLT_SF_Ele30_MVAiso80ID",
        )
    # HLT efficiency eta input: supercluster eta (as for the other EGM SFs)
    # until EGM confirms what "electron eta" in electronHlt.json means
    cfg.x.electron_hlt_use_sc_eta = True

    # helper to add column aliases for both shifts of a source
    def add_aliases(shift_source: str, aliases: Set[str], selection_dependent: bool):
        """
        Register column aliases for both directions of *shift_source*.

        NOTE: aliases always go into the 'column_aliases' aux, which is the only
        key columnflow reads (tasks/{selection,reduction,production,histograms,
        cutflow,ml}.py all do local_shift_inst.x("column_aliases", {})). The
        'column_aliases_selection_dependent' key this helper used to write for
        selection_dependent=True is read by NOTHING -- it is a leftover from an
        older columnflow API. Every JEC and JER alias in this config was silently
        inert as a result: the shifted columns would have been produced and then
        never substituted, giving shifted histograms identical to nominal.

        *selection_dependent* is kept because it is still meaningful information:
        it records that the shift changes which events pass the selection, so the
        full Calibrate -> Select -> Reduce chain must rerun rather than just
        re-reading columns. It is now expressed as a shift tag instead.
        """
        for direction in ["up", "down"]:
            shift = cfg.get_shift(od.Shift.join_name(shift_source, direction))
            # format keys and values
            inject_shift = lambda s: re.sub(r"\{([^_])", r"{_\1", s).format(**shift.__dict__)
            _aliases = {inject_shift(key): inject_shift(value) for key, value in aliases.items()}
            # extend existing or register new column aliases
            shift.set_aux("column_aliases", shift.get_aux("column_aliases", {})).update(_aliases)
            if selection_dependent:
                shift.add_tag("selection_dependent")

    # register shifts
    # TODO: make shifts year-dependent
    cfg.add_shift(name="nominal", id=0)
    cfg.add_shift(name="tune_up", id=1, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="tune_down", id=2, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="hdamp_up", id=3, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="hdamp_down", id=4, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="minbias_xs_up", id=7, type="shape")
    cfg.add_shift(name="minbias_xs_down", id=8, type="shape")
    # what enters the event weight is the per-process-normalized column, so the
    # alias has to target that, not the raw pu_weight
    add_aliases(
        "minbias_xs",
        {"normalized_pu_weight": "normalized_pu_weight_{direction}"},
        selection_dependent=False,
    )

    # trigger SF (production/trigger_weights.py): one event-level weight, three
    # independent variations
    for i, src in enumerate(("e_trig", "mu_trig_stat", "mu_trig_syst")):
        cfg.add_shift(name=f"{src}_up", id=42 + 2 * i, type="shape")
        cfg.add_shift(name=f"{src}_down", id=43 + 2 * i, type="shape")
        add_aliases(src, {"trigger_weight": f"trigger_weight_{src}_" + "{direction}"}, selection_dependent=False)

    # Lepton efficiency SFs. Reco and ID are separate measurements and hence
    # separate nuisances (EGM: uncorrelated; decorrelated per era in the
    # datacard, see cfg.x.shift_correlations). The three reco pT bins are one
    # measurement and move together.
    cfg.add_shift(name="e_reco_up", id=40, type="shape")
    cfg.add_shift(name="e_reco_down", id=41, type="shape")
    add_aliases(
        "e_reco",
        {w: f"{w}_{{direction}}" for w in ["electron_weight", "electron_mid_weight", "electron_loreco_weight"]},
        selection_dependent=False,
    )
    cfg.add_shift(name="e_id_up", id=48, type="shape")
    cfg.add_shift(name="e_id_down", id=49, type="shape")
    add_aliases("e_id", {"electron_id_weight": "electron_id_weight_{direction}"}, selection_dependent=False)

    # Muon ID / iso: MUO wants stat (per era) and syst (correlated) separately
    # (production/muon_sf.py writes <w>_{stat,syst}_{up,down})
    for i, (src, col, kind) in enumerate((
        ("mu_id_stat", "muon_id_weight", "stat"),
        ("mu_id_syst", "muon_id_weight", "syst"),
        ("mu_iso_stat", "muon_iso_weight", "stat"),
        ("mu_iso_syst", "muon_iso_weight", "syst"),
    )):
        cfg.add_shift(name=f"{src}_up", id=50 + 2 * i, type="shape")
        cfg.add_shift(name=f"{src}_down", id=51 + 2 * i, type="shape")
        add_aliases(src, {col: f"{col}_{kind}_" + "{direction}"}, selection_dependent=False)

    # Lepton momentum scale / resolution (calibration/corrections.py writes the
    # varied pt columns for MC). These change which leptons pass the pT floor,
    # so they are selection dependent: the selector registers them and
    # Calibrate -> Select -> Reduce reruns per shift (8 passes in total).
    for i, (src, coll, var) in enumerate((
        ("e_scale", "Electron", "scale"),
        ("e_smear", "Electron", "smear"),
        ("mu_scale", "Muon", "scale"),
        ("mu_resol", "Muon", "resol"),
    )):
        cfg.add_shift(name=f"{src}_up", id=300 + 2 * i, type="shape")
        cfg.add_shift(name=f"{src}_down", id=301 + 2 * i, type="shape")
        add_aliases(src, {f"{coll}.pt": f"{coll}.pt_{var}_" + "{direction}"}, selection_dependent=True)
    cfg.x.lepton_shift_sources = ["e_scale", "e_smear", "mu_scale", "mu_resol"]

    # b-tag fixed-WP SF uncertainties (BTV, more than one era): btag_bc_* and
    # btag_light_*, each correlated (across eras) and uncorrelated (per era).
    # Columns come from SplitBTagWPSFConfig.systs: btag_weight_<flav>_<dir>_<kind>.
    for i, (flav, kind) in enumerate((
        ("bc", "correlated"), ("bc", "uncorrelated"), ("light", "correlated"), ("light", "uncorrelated"),
    )):
        src = f"btag_{flav}_{kind}"
        cfg.add_shift(name=f"{src}_up", id=61 + 2 * i, type="shape")
        cfg.add_shift(name=f"{src}_down", id=62 + 2 * i, type="shape")
        add_aliases(src, {"btag_weight": f"btag_weight_{flav}_" + "{direction}" + f"_{kind}"}, selection_dependent=False)

    cfg.add_shift(name="mur_up", id=201, type="shape")
    cfg.add_shift(name="mur_down", id=202, type="shape")
    cfg.add_shift(name="muf_up", id=203, type="shape")
    cfg.add_shift(name="muf_down", id=204, type="shape")
    # NOTE: named 'murmuf_envelope', not 'murf_envelope' -- the columnflow producer
    # writes murmuf_envelope_weight{,_up,_down} and the alias has to match exactly.
    cfg.add_shift(name="murmuf_envelope_up", id=205, type="shape")
    cfg.add_shift(name="murmuf_envelope_down", id=206, type="shape")
    cfg.add_shift(name="pdf_up", id=207, type="shape")
    cfg.add_shift(name="pdf_down", id=208, type="shape")

    for unc in ["mur", "muf", "murmuf_envelope", "pdf"]:
        add_aliases(
            unc,
            {f"normalized_{unc}_weight": f"normalized_{unc}_weight_" + "{direction}"},
            selection_dependent=False,
        )

    with open(os.path.join(thisdir, "jec_sources.yaml"), "r") as f:
        all_jec_sources = yaml.load(f, yaml.Loader)["names"]
    for jec_source in cfg.x.jec["uncertainty_sources"]:
        idx = all_jec_sources.index(jec_source)
        cfg.add_shift(name=f"jec_{jec_source}_up", id=5000 + 2 * idx, type="shape")
        cfg.add_shift(name=f"jec_{jec_source}_down", id=5001 + 2 * idx, type="shape")
        add_aliases(
            f"jec_{jec_source}",
            {
                "Jet.pt": "Jet.pt_{name}",
                "Jet.mass": "Jet.mass_{name}",
                # Type-1 propagation targets PuppiMET (see calibration/corrections.py)
                "PuppiMET.pt": "PuppiMET.pt_{name}",
                "PuppiMET.phi": "PuppiMET.phi_{name}",
            },
            selection_dependent=True,
        )

    cfg.add_shift(name="jer_up", id=6000, type="shape", tags={"selection_dependent"})
    cfg.add_shift(name="jer_down", id=6001, type="shape", tags={"selection_dependent"})
    add_aliases(
        "jer",
        {
            "Jet.pt": "Jet.pt_{name}",
            "Jet.mass": "Jet.mass_{name}",
            "PuppiMET.pt": "PuppiMET.pt_{name}",
            "PuppiMET.phi": "PuppiMET.phi_{name}",
        },
        selection_dependent=True,
    )

    def make_jme_filename(jme_aux, sample_type, name, era=None):
        """
        Convenience function to compute paths to JEC files.
        """
        # normalize and validate sample type
        sample_type = sample_type.upper()
        if sample_type not in ("DATA", "MC"):
            raise ValueError(f"invalid sample type '{sample_type}', expected either 'DATA' or 'MC'")

        jme_full_version = "_".join(s for s in (jme_aux.campaign, era, jme_aux.version, sample_type) if s)

        return f"{jme_aux.source}/{jme_full_version}/{jme_full_version}_{name}_{jme_aux.jet_type}.txt"

    # external files
    # CMS Analysis Corrections (CAT). This replaces the jsonpog-integration
    # rsync mirror, which froze at 2025-09-24 and is missing everything POGs
    # published since. Campaign names are not derivable from year/postfix and
    # each POG pins its own snapshot date, so the mapping is explicit.
    cat_root = "/cvmfs/cms-griddata.cern.ch/cat/metadata"

    cat_campaign = {
        "2022preEE":    "Run3-22CDSep23-Summer22-NanoAODv12",
        "2022postEE":   "Run3-22EFGSep23-Summer22EE-NanoAODv12",
        "2023preBPix":  "Run3-23CSep23-Summer23-NanoAODv12",
        "2023postBPix": "Run3-23DSep23-Summer23BPix-NanoAODv12",
        "2024":         "Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15",
    }[era_key]

    # pinned snapshot per POG, per era
    cat_date = {
        "2022preEE":    {"LUM": "2024-01-31", "BTV": "2025-08-20", "MUO": "2026-06-18", "EGM": "2025-12-15", "JME": "2026-06-05"},  # noqa
        "2022postEE":   {"LUM": "2024-01-31", "BTV": "2025-08-20", "MUO": "2026-06-18", "EGM": "2025-12-15", "JME": "2026-06-05"},  # noqa
        "2023preBPix":  {"LUM": "2024-01-31", "BTV": "2025-08-20", "MUO": "2026-06-18", "EGM": "2025-12-15", "JME": "2026-07-15"},  # noqa
        "2023postBPix": {"LUM": "2024-01-31", "BTV": "2025-08-20", "MUO": "2026-06-18", "EGM": "2025-12-15", "JME": "2026-07-15"},  # noqa
        "2024": {
            "LUM": "2026-04-15",
            "BTV": "2026-03-10",
            "MUO": "2026-06-18",
            "EGM": "2025-12-15",
            "JME": "2026-07-16",
        },
    }[era_key]

    def cat(pog: str, filename: str) -> str:
        return f"{cat_root}/{pog}/{cat_campaign}/{cat_date[pog]}/{filename}"

    # 2024 ships era-split pileup files; C-I matches the data eras in this
    # config (there is also a BCDEFGHI variant, which includes era B and does
    # not). 2022/23 ship a single file.
    pu_file = "puWeights_CDEFGHI.json.gz" if year == 2024 else "puWeights.json.gz"
    cfg.x.external_files = DotDict.wrap({
        # pileup weight corrections
        "pu_sf": (cat("LUM", pu_file), "v1"),

        # jet energy correction
        "jet_jerc": (cat("JME", "jet_jerc.json.gz"), "v1"),

        # electron scale factors
        "electron_sf": (cat("EGM", "electron.json.gz"), "v1"),

        # muon scale factors
        "muon_sf": (cat("MUO", "muon_Z.json.gz"), "v1"),
        "electron_sf_hlt": (cat("EGM", "electronHlt.json.gz"), "v1"),

        # btag scale factor
        "btag_sf_corr": (cat("BTV", "btagging.json.gz"), "v1"),

        # V+jets reweighting
        # "vjets_reweighting": f"{local_repo}/data/json/vjets_reweighting.json.gz",

        # jet veto map
        "jet_veto_map": (cat("JME", "jetvetomaps.json.gz"), "v1"),

        # jet ID (NanoAOD v15 no longer stores Jet.jetId)
        "jet_id": (cat("JME", "jetid.json.gz"), "v1"),

        # muon Rochester-like scale & smearing
        # Source: https://github.com/cms-muon-pog/MuonScaRe
        "muon_scalesmearing": (cat("MUO", "muon_scalesmearing.json.gz"), "v1"),

        # electron scale & smearing
        "electron_ss": (cat("EGM", "electronSS_EtDependent.json.gz"), "v1"),
    })

    # LUM publishes exactly one correction per pileup file, but name it
    # explicitly so a future second entry fails loudly rather than silently.
    if year == 2024:
        cfg.x.pu_correction_name = "Collisions24_CDEFGHI_goldenJSON"

    # Golden json and pu weights
    if year == 2022 and campaign.x.EE == "pre":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": (os.path.join(repo_dir, "data", "lumi", "Cert_Collisions2022_355100_362760_Golden.json"), "v2"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2022 and campaign.x.EE == "post":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": (os.path.join(repo_dir, "data", "lumi", "Cert_Collisions2022_355100_362760_Golden.json"), "v2"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCDEFG/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2023 and campaign.x.BPix == "pre":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": (os.path.join(repo_dir, "data", "lumi", "Cert_Collisions2023_366442_370790_Golden.json"), "v2"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/BC/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2023 and campaign.x.BPix == "post":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": (os.path.join(repo_dir, "data", "lumi", "Cert_Collisions2023_366442_370790_Golden.json"), "v2"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/D/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2024:
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": (os.path.join(repo_dir, "data", "lumi", "Cert_Collisions2024_378981_386951_Golden.json"), "v2"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/PileUp/pileup_JSON-2024CDEFGHI_Golden.txt", "v1"),  # noqa
            },
        }))
    
    # columns to keep after certain steps
    cfg.x.keep_columns = DotDict.wrap({
        "cf.SelectEvents": {"mc_weight"},
        "cf.MergeSelectionMasks": {
            "mc_weight", "normalization_weight", "process_id", "category_ids", "cutflow.*",
        },
    })

    cfg.x.keep_columns["cf.ReduceEvents"] = (
        {
            # general event information
            "run", "luminosityBlock", "event", "cutflow.*",
            # columns added during selection, required in general
            "mc_weight", "PV.npvs", "process_id", "category_ids", "deterministic_seed",
            # weight-related columns
            "pu_weight*", "pdf_weight*",
            "murmuf_envelope_weight*", "mur_weight*", "muf_weight*",
            "btag_weight*",
            "Pileup.nTrueInt",
            "LHEScaleWeight",
        } | set(  # Jets
            f"{jet_obj}.{field}"
            for jet_obj in ["Jet"]
            for field in ["pt", "eta", "phi", "mass", "genJetIdx", cfg.x.btag_default.column, "hadronFlavour", "rawFactor", "btagDeepFlavQG"]  # noqa
        ) | set(  # BJets
            f"{jet_obj}.{field}"
            for jet_obj in ["BJet"]
            for field in [
                "pt", "eta", "phi", "mass", cfg.x.btag_default.column, "hadronFlavour",
            ]
        )
          | set(  # Muons
            f"{mu_obj}.{field}"
            for mu_obj in ["Muon"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "pdgId", "charge", "tightId", "pfRelIso04_all"]
        ) | set(  # Electrons
            f"{e_obj}.{field}"
            for e_obj in ["Electron"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "pdgId", "deltaEtaSC", "charge", "mvaIso_WP80"]
        ) | set(  # MET
            f"PuppiMET.{field}"
            for field in ["pt", "phi"]
        ) | set(  # MET
            f"GenMET.{field}"
            for field in ["pt", "phi"]
        ) | set(  # GenJets
            f"{gen_jet_obj}.{field}"
            for gen_jet_obj in ["GenJet"]
            for field in ["pt", "eta", "phi", "mass", "hadronFlavour"]
        )
    )

    # event weight columns as keys in an ordered dict, mapped to shift instances they depend on
    # get_shifts = lambda *keys: sum(([cfg.get_shift(f"{k}_up"), cfg.get_shift(f"{k}_down")] for k in keys), [])
    get_shifts = functools.partial(get_shifts_from_sources, cfg)
    # The shift lists are what make a weight systematic real: the 'all_weights'
    # weight producer turns them into its own 'shifts' set, and a task whose
    # dependency tree does not declare a shift silently falls back to nominal.
    # An empty list therefore means "computed, stored, but never varied".
    cfg.x.event_weights = DotDict({
        "normalization_weight": [],
        "btag_weight": get_shifts(
            "btag_bc_correlated", "btag_bc_uncorrelated", "btag_light_correlated", "btag_light_uncorrelated",
        ),
        "trigger_weight": get_shifts("e_trig", "mu_trig_stat", "mu_trig_syst"),
        "electron_weight": get_shifts("e_reco"),          # electron reco above 75
        "electron_mid_weight": get_shifts("e_reco"),      # electron reco 20-75
        "electron_loreco_weight": get_shifts("e_reco"),   # electron reco 10-20
        "electron_id_weight": get_shifts("e_id"),         # electron MVA WP80iso
        "muon_id_weight": get_shifts("mu_id_stat", "mu_id_syst"),     # TightID SF
        "muon_iso_weight": get_shifts("mu_iso_stat", "mu_iso_syst"),  # TightPFIso SF
        "normalized_pu_weight": get_shifts("minbias_xs"),
    })

    # Dataset-level weights. These live here rather than in cfg.x.event_weights
    # because they do not exist for every dataset, and only the dataset-level
    # loops in all_weights / event_weight guard with has_ak_column -- a
    # config-level entry that is missing for one dataset raises instead.
    for dataset in cfg.datasets:
        if not dataset.is_mc:
            continue
        dataset_weights = {}
        # Top pT reweighting is OFF: no Run 3 prescription has been agreed yet.
        # When it comes back, apply it to tt_* only (the is_ttbar tag), never to
        # ttZ / ttW / ttH, and normalize it so the inclusive ttbar yield is kept.
        # pythia dibosons have no LHEScaleWeight/LHEPdfWeight branch
        if not dataset.has_tag("no_lhe_weights"):
            for unc in ["mur", "muf", "murmuf_envelope", "pdf"]:
                dataset_weights[f"normalized_{unc}_weight"] = get_shifts(unc)
        if dataset_weights:
            dataset.x.event_weights = dataset_weights

    # v2: selection stats now book per-process sums for the pileup, scale and PDF
    # weight variations, so cf.SelectEvents and everything downstream must rerun.
    prod_version = "v5"

    # Version of required tasks
    # v1: jet_energy now runs jec_full (uncertainty sources) instead of jec_nominal
    # for MC, so CalibrateEvents writes additional Jet.pt_jec_*/Jet.mass_jec_*
    # columns and its outputs are no longer compatible with v0.
    calib_version = "v1"
    cfg.x.versions = {
        "cf.CalibrateEvents": calib_version,
        "cf.SelectEvents": prod_version,
        "cf.MergeSelectionStats": prod_version,
        "cf.MergeSelectionMasks": prod_version,
        "cf.ReduceEvents": prod_version,
        "cf.MergeReductionStats": prod_version,
        "cf.MergeReduceEvents": prod_version,
        "cf.ProvideReducedEvents": prod_version,
        "cf.ProduceColumns": prod_version,
    }

    # DY stays at the NLO cross sections from cmsdb in every era (6282.6 pb for
    # m50, 19768.5 pb for m10to50; the 2024 flavour-split samples sum to the
    # same). The former NNLO override here never applied (it looked up
    # "dy_m50toinf", which is not a config process) and was removed: the group
    # will derive its own DY correction from the 2l region.

    add_variables(cfg)
    add_categories_selection(cfg)
    # build the combined leaf categories (and the 'unblinded' group) at config-build
    # time so --categories resolves them during task param resolution, not only
    # after producer init. @call_once_on_config makes the later producer call a no-op.
    add_categories_production(cfg)

    # unblinded group: all 0b leaf categories. Data is blinded in >=1 b-jet
    # regions, so plots of data use --categories unblinded. MC/inference may
    # still use the 1b/2b SR leaves, which remain defined.
    def _walk_cats(cats):
        for c in cats:
            yield c
            yield from _walk_cats(c.categories)
    cfg.x.category_groups["unblinded"] = sorted(
        {c.name for c in _walk_cats(cfg.categories) if "0bjets" in c.name.split("__")}
    )
    # add_cutflow_variables(cfg)
    from azh.config.triggers import add_triggers
    add_triggers(cfg)

    # surface everything that still needs checking against the real files
    if cfg_unverified:
        logger.warning(
            f"config '{cfg.name}' uses {len(cfg_unverified)} unverified setting(s):\n" +
            "\n".join(f"  - {s}" for s in cfg_unverified),
        )
    cfg.x.unverified_settings = cfg_unverified

    # only produce cutflow features when number of dataset_files is limited (used in selection module)
    cfg.x.do_cutflow_features = bool(limit_dataset_files) and limit_dataset_files <= 10
    return cfg
