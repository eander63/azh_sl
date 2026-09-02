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
from azh.config.signals import AZH_SIGNAL_PROCESSES

thisdir = os.path.dirname(os.path.abspath(__file__))

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
        "ttv": "$t\\bar{t}$ + V",
    }

    colors = {
        "dy_hf": "#C7FF33",
        "dy_lf": "#FBFF36",
        "dy_ee": "#C7FF33",
        "dy_mumu": "#FBFF36",
        "du_tautau": "#9ACD32",
        "data": "#000000",  # black
        "tt": "#E04F21",  # red
        "ttv": "#5E8FFC",  # blue
        "ttz": "#6B375A",
        "ttw": "#346532",  
        "w_lnu": "#82FF28",  # green
        "tth": "#FFA500",  # orange
        "higgs": "#984ea3",  # purple
        "st": "#3E00FB",  # dark purple
        "wz": "#FF6B9D",  # hot pink for WZ
        "vv": "#B900FC",  # pink
        "vvv": "#3E6676",
        "azh_htt_zll_a1000_h600": "#C7FF33",
        "azh_htt_zll_a1600_h1500": "#2FC917",
        "azh_htt_zll_a650_h550": "#1752C9",
        "azh_htt_zll_a2100_h1300": "#C9174D",
        "azh_htt_zll_a1000_h330" : "#F74CD8",
        "azh_htt_zll_a430_h330": "#EB973F",
        "other": "#999999",  # grey
    }

    process_names = [
        "dy_hf", "dy_lf", "tt",
        "ttz", "ttw",
        "ttv", "st", "w_lnu", "tth", "wz", "vv", "data",
        *AZH_SIGNAL_PROCESSES,
    ]

    # print(process_names)
    # 2024 has no lepton-inclusive DY sample and no hf/lf children for the
    # flavour-split ones, so register dy_ee / dy_mumu / dy_tautau instead of
    # dy_hf / dy_lf. See the dataset list and the is_dy tagging below.
    # The 2024 campaign also ships no azh.py, so none of the signal processes
    # exist there yet -- drop them rather than failing on procs.get().
    if year == 2024:
        process_names = [p for p in process_names if p not in ("dy_hf", "dy_lf")]
        process_names = [p for p in process_names if not p.startswith("azh_")]
        process_names = ["dy_ee", "dy_mumu", "dy_tautau"] + process_names

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

    dataset_names = [
    # DY
    # 2022/23: inclusive amcatnlo samples (no stitching needed).
    # 2024: no lepton-inclusive DY was produced, so the three flavour-split
    # samples are summed instead. m50toinf is amcatnlo as before; m10to50 only
    # exists as powheg for 2024, so the low-mass generator differs by era.
    *if_not_era(year=2024, values=[
        "dy_m50toinf_amcatnlo",
        "dy_m10to50_amcatnlo",
    ]),
    *if_era(year=2024, values=[
        "dy_ee_m50toinf_amcatnlo",
        "dy_mumu_m50toinf_amcatnlo",
        "dy_tautau_m50toinf_amcatnlo",
        "dy_ee_m10to50_powheg",
        "dy_mumu_m10to50_powheg",
        "dy_tautau_m10to50_powheg",
    ]),

    # TTbar
        "tt_sl_powheg",
        "tt_dl_powheg",
        "tt_fh_powheg",

    # TTZ
        "ttz_zll_m4to50_amcatnlo",
        "ttz_zll_m50toinf_amcatnlo",
    # TTH
        "tth_hbb_powheg",
        "tth_hnonbb_powheg",

    # Single top
    # 2024 splits t-channel into leptonic / hadronic top decays; only the
    # leptonic part can contribute to a 2l/3l selection.
    *if_not_era(year=2024, values=[
        "st_tchannel_t_4f_powheg",
        "st_tchannel_tbar_4f_powheg",
    ]),
    *if_era(year=2024, values=[
        "st_tchannel_t_lep_4f_powheg",
        "st_tchannel_tbar_lep_4f_powheg",
    ]),
        "st_twchannel_t_sl_powheg",
        "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg",
        "st_twchannel_tbar_dl_powheg",

    # Diboson
        "ww_pythia",
        "wz_pythia",
        "zz_pythia",

    # W+jets
    # 2024 has no inclusive w_lnu sample. The available replacements are
    # jet-binned madgraph (1j-4j, no 0j bin) or pt-binned amcatnlo, both of
    # which need stitching weights to be normalised correctly. Rather than ship
    # a mis-normalised sample, W+jets is left out of 2024 for now -- it is a
    # small background in the 2l/3l regions. See README "2024 open items".
    *if_not_era(year=2024, values=[
        "w_lnu_amcatnlo",
    ]),

    *if_era(year=2022, tag="preEE", values=[
        "data_mu_c",
        "data_mu_d",
        "data_egamma_c",
        "data_egamma_d",
        "data_muoneg_c",
        "data_muoneg_d",
        "ttw_amcatnlo",
        "wwz_amcatnlo",
    ]),
    *if_era(year=2022, tag="postEE", values=[
        "data_mu_e",
        "data_mu_f",
        "data_mu_g",
        "data_egamma_e",
        "data_egamma_f",
        "data_egamma_g",
        "data_muoneg_e",
        "data_muoneg_f",
        "data_muoneg_g",
    ]),
    *if_era(year=2023, tag="preBPix", values=[
        "data_mu_c1",
        "data_mu_c2",
        "data_mu_c3",
        "data_mu_c4",
        "data_egamma_c1",
        "data_egamma_c2",
        "data_egamma_c3",
        "data_egamma_c4",
        "data_muoneg_c1",
        "data_muoneg_c2",
        "data_muoneg_c3",
        "data_muoneg_c4",
    ]),
    *if_era(year=2023, tag="postBPix", values=[
        "data_mu_d1",
        "data_mu_d2",
        "data_egamma_d1",
        "data_egamma_d2",
        "data_muoneg_d1",
        "data_muoneg_d2",
    ]),
    # 2024 runs C-I. Note the EGamma primary dataset is called "data_e_*" here,
    # not "data_egamma_*" as in 2022/23 -- see the tagging block below.
    *if_era(year=2024, values=[
        *[f"data_mu_{e}" for e in "cdefghi"],
        *[f"data_e_{e}" for e in "cdefghi"],
        *[f"data_muoneg_{e}" for e in "cdefghi"],
    ]),
    ]
    

    for dataset_name in dataset_names:
        dataset = cfg.add_dataset(campaign.get_dataset(dataset_name))
        if limit_dataset_files:
            for info in dataset.info.values():
                if info.n_files > limit_dataset_files:
                    info.n_files = limit_dataset_files
        if dataset.name.startswith("tt"):
            dataset.add_tag({"is_ttbar"})
        if dataset.name.startswith("dy"):
            if not re.match(r"^dy_(ee|mumu|tautau)_", dataset.name):
                dataset.add_tag({"is_dy"})
        if dataset.name.startswith("azh"):
            dataset.add_tag({"is_signal"})
        if dataset.name.startswith("data_mu"):
            dataset.add_tag("mu")
        if dataset.name.startswith("data_egamma") or dataset.name.startswith("data_e_"):
            dataset.add_tag("egamma")
        if dataset.name.startswith("data_muoneg"):
            dataset.add_tag({"mu", "egamma"})
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
    for ds_name in ["ww_pythia", "wz_pythia", "zz_pythia"]:
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
    cfg.x.default_weight_producer = "all_weights"
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
        "default": ["n_jet", "jet1_pt"],
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

    # lumi values in inverse pb
    # 2022preEE, 2022postEE, 2023preBPix, 2023postBPix all brilcalc verified (jun 29 2026)
    #
    # Uncertainties follow the LUM POG Run 3 covariance matrix (golden JSON):
    #   L = 34.75 +- 0.48 (1.4%) [2022], 28.40 +- 0.36 (1.3%) [2023],
    #       110.11 +- 1.77 (1.6%) [2024]; combined 173.26 +- 2.07 (1.2%).
    # The per-year total is NOT a single nuisance: part of it comes from the vdM
    # methodology and is common to all years, the rest is year-specific. Filing
    # the whole thing under one 'correlated' key (as before) asserts 100%
    # correlation and inflates the combined uncertainty.
    #
    # Decomposing the POG covariance as R_ij = c_i c_j (correlated, one shared
    # nuisance with year-dependent size) + delta_ij u_i^2 (uncorrelated) gives:
    #                    2022       2023       2024
    #   correlated      0.2676%    0.8746%    1.0244%
    #   uncorrelated    1.3530%    0.9356%    1.2368%
    #   quad. sum       1.3792%    1.2807%    1.6060%   (POG: 1.4 / 1.3 / 1.6%)
    # This reproduces every element of the POG matrix, and hence the 1.2%
    # combined figure, to machine precision. NOTE: with three years the rank-1
    # off-diagonal solution is exact by construction (3 equations, 3 unknowns),
    # so re-derive this if a fourth year is added.
    #
    # Both eras of a given year share that year's nuisances -- the luminosity
    # calibration is per-year, not per-era.
    if year == 2022:
        if campaign.x.EE == "pre":
            cfg.x.luminosity = Number(7990, {
                "lumi_13p6TeV_correlated": 0.002676j,
                "lumi_13p6TeV_uncorrelated_2022": 0.013530j,
            })
        elif campaign.x.EE == "post":
            cfg.x.luminosity = Number(26675, {
                "lumi_13p6TeV_correlated": 0.002676j,
                "lumi_13p6TeV_uncorrelated_2022": 0.013530j,
            })
    elif year == 2023:
        if campaign.x.BPix == "pre":
            cfg.x.luminosity = Number(18605, {
                "lumi_13p6TeV_correlated": 0.008746j,
                "lumi_13p6TeV_uncorrelated_2023": 0.009356j,
            })
        elif campaign.x.BPix == "post":
            cfg.x.luminosity = Number(9693, {
                "lumi_13p6TeV_correlated": 0.008746j,
                "lumi_13p6TeV_uncorrelated_2023": 0.009356j,
            })
    elif year == 2024:
        # 2024 golden-JSON integrated luminosity, runs 378981-386951.
        # Not brilcalc-verified locally -- taken from the CMS 2024 recommendation.
        cfg.x.luminosity = Number(109948, {
            "lumi_13p6TeV_correlated": 0.010244j,
            "lumi_13p6TeV_uncorrelated_2024": 0.012368j,
        })
    else:
        raise NotImplementedError(f"Luminosity for year {year} is not defined.")

    # Per-channel effective lumi for `channel_lumi_weight` (see
    # production/channel_lumi_weight.py for derivation procedure).
    # The 2022preEE numbers were derived with brilcalc against the golden
    # JSON Cert_Collisions2022_355100_362760_Golden.json. For the other
    # eras the muon and egamma PDs run end-to-end, so the ratio is ~1.0
    # by default — re-derive with brilcalc per era to refine, then update
    # below. Leaving any entry equal to ``nominal`` is a no-op (SF=1).
    nominal = float(cfg.x.luminosity.nominal)
    if year == 2022 and campaign.x.EE == "pre":
        cfg.x.channel_lumis = {"muon": 7448.0, "egamma": 7989.5, "nominal": nominal}
    elif year == 2022 and campaign.x.EE == "post":
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}
    elif year == 2023 and campaign.x.BPix == "pre":
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}
    elif year == 2023 and campaign.x.BPix == "post":
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}
    elif year == 2024:
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}

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
    # "Total" is the quadrature sum of all ~27 individual sources: one nuisance,
    # no correlation structure. Fine for commissioning.
    #
    # The AN-2022/158 reduced set (Sec. 9.1, l. 734-738) is 11 groups, 6 correlated
    # across years and 5 era-specific, which is what the final fit needs so the
    # fit can pull the barrel and endcap terms independently. Verified present in
    # the 2022 JME file as Summer22_22Sep2023_V4_MC_Regrouped_<name>_AK4PFPuppi.
    #
    # Cost: each source is selection_dependent, so a full
    # Calibrate -> Select -> Reduce -> Produce pass per direction, i.e. ~22 chain
    # passes per dataset versus 2 for "Total".
    #
    # Switching is a one-line change: swap JEC_SOURCES_TOTAL for
    # JEC_SOURCES_REDUCED below. The selector reads the list from the config
    # (azh/selection/default.py), so the new shifts register automatically.
    #
    # TODO: the era-specific names are verified for 2022 only. Confirm the
    # <name>_2023 / <name>_2024 spellings against those campaigns' JME files
    # before processing them -- list the correction keys as we did for 2022.
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
        f"Regrouped_Absolute_{year}",
        f"Regrouped_BBEC1_{year}",
        f"Regrouped_EC2_{year}",
        f"Regrouped_HF_{year}",
        f"Regrouped_RelativeSample_{year}",
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
    from columnflow.production.cms.btag import SplitBTagSFConfig
    if year == 2024:
        cfg.x.btag_sf = SplitBTagSFConfig(
            correction_set=("UParTAK4_light", "UParTAK4_comb"),
            discriminator="btagUParTAK4B",
            corrector_kwargs={"working_point": "M"},
        )
    else:
        cfg.x.btag_sf = SplitBTagSFConfig(
            correction_set=("particleNet_light", "particleNet_comb"),
            discriminator="btagPNetB",
            corrector_kwargs={"working_point": "M"},
        )

    # names of electron correction sets and working points
    # (used in the electron_sf producer)
    if f"{year}{corr_postfix}" == "2022postEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "wp80iso")
        # TODO: UNVERIFIED -- the 2022preEE file names its scale correction
        # EGMScale_ElePTsplit_<era>, so this 2024 name is very likely wrong here
        # too. List the keys in this era's electronSS_EtDependent.json.gz before
        # processing it; electron_ss_setup now reports them on failure.
        cfg.x.electron_ss_names = ("EGMScale_ElePTsplit_2024", "SmearAndSyst")
    elif f"{year}{corr_postfix}" == "2022preEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoBCD", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoBCD", "wp80iso")
        # VERIFIED against Run3-22CDSep23-Summer22-NanoAODv12/2025-12-15/
        # electronSS_EtDependent.json.gz: the scale correction carries an era
        # suffix, 'SmearAndSyst' is a generic alias for EGMSmearAndSyst_ElePT_2022
        # and needs none. The previous value here was the 2024 name, which does
        # not exist in this file (correctionlib raised a bare "IndexError: map::at").
        cfg.x.electron_ss_names = ("EGMScale_ElePTsplit_2022preEE", "SmearAndSyst")
    elif f"{year}{corr_postfix}" == "2023postBPix":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptD", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2023PromptD", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptD", "wp80iso")
        # TODO: UNVERIFIED -- the 2022preEE file names its scale correction
        # EGMScale_ElePTsplit_<era>, so this 2024 name is very likely wrong here
        # too. List the keys in this era's electronSS_EtDependent.json.gz before
        # processing it; electron_ss_setup now reports them on failure.
        cfg.x.electron_ss_names = ("EGMScale_ElePTsplit_2024", "SmearAndSyst")
    elif f"{year}{corr_postfix}" == "2023preBPix":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptC", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptC", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2023PromptC", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptC", "wp80iso")
        # TODO: UNVERIFIED -- the 2022preEE file names its scale correction
        # EGMScale_ElePTsplit_<era>, so this 2024 name is very likely wrong here
        # too. List the keys in this era's electronSS_EtDependent.json.gz before
        # processing it; electron_ss_setup now reports them on failure.
        cfg.x.electron_ss_names = ("EGMScale_ElePTsplit_2024", "SmearAndSyst")
    elif era_key == "2024":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2024Prompt", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2024Prompt", "Reco20to75")
        cfg.x.electron_sf_loreco_names = ("Electron-ID-SF", "2024Prompt", "RecoBelow20")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2024Prompt", "wp80iso")
        cfg.x.electron_ss_names = ("EGMScale_ElePTsplit_2024", "SmearAndSyst")

    # names of muon correction sets and working points
    # (used in the muon producer)
    # TightID muon SF chain (from muon_Z.json):
    # SF(TightID|Tracker) x SF(TightPFIso|TightID) x SF(IsoMu24|TightID+PFIso)
    # Valid down to ~15 GeV (Z tag-and-probe), matching our selection threshold
    cfg.x.muon_sf_id_names = ("NUM_TightID_DEN_TrackerMuons", era_key)
    cfg.x.muon_sf_iso_names = ("NUM_TightPFIso_DEN_TightID", era_key)
    cfg.x.muon_sf_trig_names = ("NUM_IsoMu24_DEN_CutBasedIdTight_and_PFIsoTight", era_key)
    # era-branched HLT electron SF. VERIFY the period string AND the HLT category
    # ("HLT_SF_Ele30_MVAiso80ID") against electronHlt.json per era (introspection cmd).
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
    cfg.x.top_pt_reweighting_params = {
        "a": 0.0615,
        "b": -0.0005,
    }

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
    cfg.add_shift(name="top_pt_up", id=9, type="shape")
    cfg.add_shift(name="top_pt_down", id=10, type="shape")
    add_aliases("top_pt", {"top_pt_weight": "top_pt_weight_{direction}"}, selection_dependent=False)

    cfg.add_shift(name="e_sf_up", id=40, type="shape")
    cfg.add_shift(name="e_sf_down", id=41, type="shape")
    cfg.add_shift(name="e_trig_sf_up", id=42, type="shape")
    cfg.add_shift(name="e_trig_sf_down", id=43, type="shape")
    add_aliases("e_trig_sf", {"electron_trig_weight": "electron_trig_weight_{direction}"}, selection_dependent=False)
    cfg.add_shift(name="mu_trig_sf_up", id=53, type="shape")
    cfg.add_shift(name="mu_trig_sf_down", id=54, type="shape")
    add_aliases("mu_trig_sf", {"muon_trig_weight": "muon_trig_weight_{direction}"}, selection_dependent=False)

    # AN-2022/158 Table 22 uses a single shape nuisance per lepton flavour
    # (CMS_eff_e, CMS_eff_m), correlated across years, covering reco + ID (+ iso).
    # We follow that grouping here: every electron SF column moves coherently
    # under 'e_sf', every muon SF column under 'muon'. Coherent motion is the
    # conservative choice (reco and ID are independent measurements, so a proper
    # treatment would add them in quadrature). To split them later, register a
    # new shift source and move the relevant entries out of these dicts.
    #
    # Column names follow azh/production/weights.py: the base electron_weights /
    # muon_weights producers are derived once per SF, and each derivative emits
    # <weight_name>{,_up,_down} unconditionally.
    add_aliases(
        "e_sf",
        {
            w: f"{w}_{{direction}}"
            for w in [
                "electron_weight",         # reco, pT >= 75
                "electron_mid_weight",     # reco, 20 <= pT < 75
                "electron_loreco_weight",  # reco, 10 <= pT < 20
                "electron_id_weight",      # MVA WP80iso ID
            ]
        },
        selection_dependent=False,
    )

    cfg.add_shift(name="muon_up", id=51, type="shape")
    cfg.add_shift(name="muon_down", id=52, type="shape")
    # NOTE: the previous alias targeted 'muon_weight', which this analysis never
    # produces -- weights.py derives split TightID / TightPFIso producers instead,
    # so the alias silently did nothing.
    add_aliases(
        "muon",
        {
            w: f"{w}_{{direction}}"
            for w in [
                "muon_id_weight",   # TightID SF
                "muon_iso_weight",  # TightPFIso SF
            ]
        },
        selection_dependent=False,
    )

    btag_uncs = []
    for i, unc in enumerate(btag_uncs):
        cfg.add_shift(name=f"btag_{unc}_up", id=100 + 2 * i, type="shape")
        cfg.add_shift(name=f"btag_{unc}_down", id=101 + 2 * i, type="shape")

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
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json", "v1"),  # noqa
                "normtag": ("/afs/cern.ch/user/l/lumipro/public/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2022 and campaign.x.EE == "post":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json", "v1"),  # noqa
                "normtag": ("/afs/cern.ch/user/l/lumipro/public/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCDEFG/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2023 and campaign.x.BPix == "pre":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json", "v1"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/BC/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2023 and campaign.x.BPix == "post":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json", "v1"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/D/pileup_JSON.txt", "v1"),
            },
        }))
    elif year == 2024:
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/Cert_Collisions2024_378981_386951_Golden.json", "v1"),  # noqa
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
            "GenPart.*",
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
        "channel_lumi_weight": [],        # per-channel lumi correction (muon: x0.9344, ee: x1.0023)
        "electron_trig_weight": get_shifts("e_trig_sf"),
        # muon_Z.json HLT SFs valid down to ~15 GeV
        "muon_trig_weight": get_shifts("mu_trig_sf"),
        "electron_weight": get_shifts("e_sf"),            # electron reco above 75
        "electron_mid_weight": get_shifts("e_sf"),        # electron reco 20-75
        "electron_loreco_weight": get_shifts("e_sf"),     # electron reco 10-20
        "electron_id_weight": get_shifts("e_sf"),         # electron MVA WP80iso
        "muon_id_weight": get_shifts("muon"),             # TightID SF
        "muon_iso_weight": get_shifts("muon"),            # TightPFIso SF
        # split_btag_weights is called in weights.py and 'btag_weight*' is kept
        # through reduction, but the column was never listed here -- so the b-tag
        # scale factor was computed, stored, and then silently dropped from the
        # event weight. This is a nominal-yield fix, not a systematics one.
        # Shift list stays empty: the fork's split_btag_weights hardcodes
        # btag_uncs = {} and produces only 'btag_weight', so no varied columns
        # exist yet (see cfg.x.btag_sf_jec_sources for the intended source list).
        "btag_weight": [],
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
        # NOTE: previously guarded on dataset.x("is_ttbar", False), but is_ttbar is
        # set as a *tag*, so that expression was False for every dataset and the top
        # pT weight was computed but never applied.
        if dataset.has_tag("is_ttbar"):
            # The weight itself IS applied (it is a correction, not an option).
            # The *nuisance* is parked at [] pending a decision on the prescription:
            # gen_top.py currently builds the variations as w*1.5 / w*0.5, a flat
            # multiplicative factor. That is a pure +-50% rate change on ttbar with
            # zero shape content (measured total-yield ratio: exactly 1.500000),
            # whereas AN-2022/158 Sec. 9.1 l. 709 and Table 25 specify 'topPtRew' as
            # a SHAPE nuisance whose magnitude is the full weight, i.e. the variation
            # spans "reweighting applied" vs "not applied" (w -> 1 and w -> w^2).
            # Enabling this before the prescription is settled would put a large,
            # shapeless rate nuisance on the dominant background.
            # TODO: restore get_shifts("top_pt") once the method is agreed.
            dataset_weights["top_pt_weight"] = []
        # pythia dibosons have no LHEScaleWeight/LHEPdfWeight branch
        if not dataset.has_tag("no_lhe_weights"):
            for unc in ["mur", "muf", "murmuf_envelope", "pdf"]:
                dataset_weights[f"normalized_{unc}_weight"] = get_shifts(unc)
        if dataset_weights:
            dataset.x.event_weights = dataset_weights

    # v2: selection stats now book per-process sums for the pileup, scale and PDF
    # weight variations, so cf.SelectEvents and everything downstream must rerun.
    prod_version = "v2"

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

    # Override NLO DY xsec with NNLO prediction (DYTurbo + NNPDF 3.1)
    # NLO from amcatnlo: 6275 pb; NNLO: ~6688 pb (k=1.066)
    # Reference: SMP-22-017 uses NNLO normalization
    if cfg.has_process("dy_m50toinf"):
        cfg.get_process("dy_m50toinf").set_xsec(13.6, Number(6688.0, {"tot": 0.02j}))
    if cfg.has_process("dy_m10to50"):
        cfg.get_process("dy_m10to50").set_xsec(13.6, Number(21050.0, {"tot": 0.02j}))

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
    if year == 2022:
        from azh.config.triggers import add_triggers_2022
        add_triggers_2022(cfg)
    if year == 2024:
        from azh.config.triggers import add_triggers_2024
        add_triggers_2024(cfg)

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
