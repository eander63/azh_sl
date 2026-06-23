"""
Configuration of the Run 2 AZH analysis.
"""

from __future__ import annotations

import os
import re
from typing import Set

import yaml
from scinum import Number
import order as od
import law
import functools

from columnflow.util import DotDict
from cmsdb.util import add_decay_process
# import functools
# from dijet.config.datasets import get_dataset_lfns
from azh.config.analysis_azh_run3 import analysis_azh
from azh.config.categories import add_categories_selection, add_categories_production
from azh.config.variables import add_variables
# from azh.config.cutflow_variables import add_cutflow_variables
from columnflow.config_util import (
    get_root_processes_from_campaign, add_shift_aliases,get_shifts_from_sources
)


thisdir = os.path.dirname(os.path.abspath(__file__))


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
            # print(flavour)
            # print(dy_proc_inst)
            # the 'add_decay_process' function helps us to create all parent-daughter relationships
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
    # validations
    assert campaign.x.year in [2022, 2023]
    if campaign.x.year == 2022:
        assert campaign.x.EE in ["pre", "post"]
    elif campaign.x.year == 2023:
        assert campaign.x.BPix in ["pre", "post"]

    # gather campaign data
    # modify_cmsdb_processes()

    year = campaign.x.year
    year2 = year % 100
    corr_postfix = ""
    if year == 2022:
        corr_postfix = f"{campaign.x.EE}EE"
    elif year == 2023:
        corr_postfix = f"{campaign.x.BPix}BPix"

    implemented_years = [2022,2023]

    if year not in implemented_years:
        raise NotImplementedError("For now, only 2022+2023 campaign is fully implemented")

    # get all root processes
    procs = get_root_processes_from_campaign(campaign)

    # create a config by passing the campaign, so id and name will be identical
    cfg = analysis_azh.add_config(campaign, name=config_name, id=config_id)
    # use custom get_dataset_lfns function
    cfg.x.get_dataset_lfns = get_dataset_lfns
    cfg.x.get_dataset_lfns_sandbox = f"bash::$CF_BASE/sandboxes/venv_columnar_dev.sh"

    # add processes we are interested in

    # set color of some processes
    # set color of some processes
    labels = {
        "tt": "$t\\bar{t}$",
        "ttv": "$t\\bar{t}$ + V",
    }

    colors = {
        # "dy": "#FBFF36",  # yellow
        "dy_hf": "#C7FF33",
        "dy_lf": "#FBFF36",
        "data": "#000000",  # black
        "tt": "#E04F21",  # red
        "ttv": "#5E8FFC",  # blue
        "w_lnu": "#82FF28",  # green
        "higgs": "#984ea3",  # purple
        "st": "#3E00FB",  # dark purple
        "wz": "#FF6B9D",  # hot pink for WZ
        "vv": "#B900FC",  # pink
        # "azh": "#984ea3",
        "azh_htt_zll_a1000_h600": "#C7FF33",
        "azh_htt_zll_a1600_h1500": "#2FC917",
        "azh_htt_zll_a650_h550": "#1752C9",
        "azh_htt_zll_a2100_h1300": "#C9174D",
        "azh_htt_zll_a1000_h330" : "#F74CD8",
        "azh_htt_zll_a430_h330": "#EB973F",
        "other": "#999999",  # grey
    }

    # add datasets we need to study
    process_names = [
        # "dy",
        "dy_hf",
        "dy_lf",
        "tt",
        "ttv",
        "st",
        "w_lnu",
        "wz",
        "vv",
        # "vvv",
        "data",
        "azh_htt_zll_a1000_h330",
        "azh_htt_zll_a1600_h1500",
        "azh_htt_zll_a430_h330",
        "azh_htt_zll_a2100_h1300",
        "azh_htt_zll_a1000_h600",
        "azh_htt_zll_a500_h350",
        "azh_htt_zll_a1000_h350",
        "azh_htt_zll_a1000_h400",
        "azh_htt_zll_a1000_h450",
        "azh_htt_zll_a1000_h500",
        "azh_htt_zll_a1000_h550",
        "azh_htt_zll_a1000_h650",
        "azh_htt_zll_a1000_h700",
        "azh_htt_zll_a1000_h750",
        "azh_htt_zll_a1000_h800",
        "azh_htt_zll_a1000_h850",
        "azh_htt_zll_a1000_h900",
        "azh_htt_zll_a1050_h330",
        "azh_htt_zll_a1050_h350",
        "azh_htt_zll_a1050_h400",
        "azh_htt_zll_a1050_h450",
        "azh_htt_zll_a1050_h500",
        "azh_htt_zll_a1050_h550",
        "azh_htt_zll_a1050_h600",
        "azh_htt_zll_a1050_h700",
        "azh_htt_zll_a1050_h750",
        "azh_htt_zll_a1050_h800",
        "azh_htt_zll_a1050_h850",
        "azh_htt_zll_a1050_h900",
        "azh_htt_zll_a1050_h950",
        "azh_htt_zll_a1100_h1000",
        "azh_htt_zll_a1100_h330",
        "azh_htt_zll_a1100_h350",
        "azh_htt_zll_a1100_h400",
        "azh_htt_zll_a1100_h450",
        "azh_htt_zll_a1100_h500",
        "azh_htt_zll_a1100_h550",
        "azh_htt_zll_a1100_h600",
        "azh_htt_zll_a1100_h650",
        "azh_htt_zll_a1100_h700",
        "azh_htt_zll_a1100_h750",
        "azh_htt_zll_a1100_h800",
        "azh_htt_zll_a1100_h850",
        "azh_htt_zll_a1100_h900",
        "azh_htt_zll_a1100_h950",
        "azh_htt_zll_a1150_h1050",
        "azh_htt_zll_a1150_h330",
        "azh_htt_zll_a1150_h350",
        "azh_htt_zll_a1150_h450",
        "azh_htt_zll_a1150_h550",
        "azh_htt_zll_a1150_h650",
        "azh_htt_zll_a1150_h750",
        "azh_htt_zll_a1150_h850",
        "azh_htt_zll_a1150_h950",
        "azh_htt_zll_a1200_h1000",
        "azh_htt_zll_a1200_h1100",
        "azh_htt_zll_a1200_h330",
        "azh_htt_zll_a1200_h350",
        "azh_htt_zll_a1200_h400",
        "azh_htt_zll_a1200_h500",
        "azh_htt_zll_a1200_h600",
        "azh_htt_zll_a1200_h700",
        "azh_htt_zll_a1200_h800",
        "azh_htt_zll_a1200_h850",
        "azh_htt_zll_a1200_h900",
        "azh_htt_zll_a1300_h1000",
        "azh_htt_zll_a1300_h1100",
        "azh_htt_zll_a1300_h1200",
        "azh_htt_zll_a1300_h350",
        "azh_htt_zll_a1300_h400",
        "azh_htt_zll_a1300_h500",
        "azh_htt_zll_a1300_h600",
        "azh_htt_zll_a1300_h700",
        "azh_htt_zll_a1300_h800",
        "azh_htt_zll_a1300_h900",
        "azh_htt_zll_a1400_h1000",
        "azh_htt_zll_a1400_h1100",
        # "azh_htt_zll_a1400_h1200",
        "azh_htt_zll_a1400_h1300",
        "azh_htt_zll_a1400_h350",
        "azh_htt_zll_a1400_h400",
        "azh_htt_zll_a1400_h500",
        "azh_htt_zll_a1400_h600",
        "azh_htt_zll_a1400_h700",
        "azh_htt_zll_a1400_h800",
        "azh_htt_zll_a1400_h900",
        "azh_htt_zll_a1500_h1000",
        "azh_htt_zll_a1500_h1100",
        "azh_htt_zll_a1500_h1200",
        "azh_htt_zll_a1500_h1300",
        "azh_htt_zll_a1500_h1400",
        "azh_htt_zll_a1500_h350",
        "azh_htt_zll_a1500_h400",
        "azh_htt_zll_a1500_h500",
        "azh_htt_zll_a1500_h600",
        "azh_htt_zll_a1500_h700",
        "azh_htt_zll_a1500_h900",
        "azh_htt_zll_a1600_h1000",
        "azh_htt_zll_a1600_h1100",
        "azh_htt_zll_a1600_h1200",
        "azh_htt_zll_a1600_h1300",
        "azh_htt_zll_a1600_h1400",
         "azh_htt_zll_a1600_h350",
        "azh_htt_zll_a1600_h400",
        "azh_htt_zll_a1600_h500",
        "azh_htt_zll_a1600_h600",
        "azh_htt_zll_a1600_h900",
        "azh_htt_zll_a1700_h1000",
        "azh_htt_zll_a1700_h1100",
        "azh_htt_zll_a1700_h1200",
        "azh_htt_zll_a1700_h1300",
        "azh_htt_zll_a1700_h1400",
        "azh_htt_zll_a1700_h1500",
        "azh_htt_zll_a1700_h1600",
        "azh_htt_zll_a1700_h350",
        "azh_htt_zll_a1700_h400",
        "azh_htt_zll_a1700_h500",
        "azh_htt_zll_a1700_h600",
        "azh_htt_zll_a1700_h700",
        "azh_htt_zll_a1700_h800",
        # "azh_htt_zll_a1700_h900",
        "azh_htt_zll_a1800_h1000",
        "azh_htt_zll_a1800_h1100",
        "azh_htt_zll_a1800_h1200",
        "azh_htt_zll_a1800_h1300",
        "azh_htt_zll_a1800_h1400",
        "azh_htt_zll_a1800_h1500",
        "azh_htt_zll_a1800_h1600",
        "azh_htt_zll_a1800_h1700",
        "azh_htt_zll_a1800_h350",
        "azh_htt_zll_a1800_h400",
        "azh_htt_zll_a1800_h500",
        "azh_htt_zll_a1800_h600",
        "azh_htt_zll_a1800_h700",
        "azh_htt_zll_a1800_h800",
        "azh_htt_zll_a1800_h900",
        "azh_htt_zll_a1900_h1000",
        "azh_htt_zll_a1900_h1100",
        "azh_htt_zll_a1900_h1200",
        "azh_htt_zll_a1900_h1300",
        "azh_htt_zll_a1900_h1400",
        "azh_htt_zll_a1900_h1500",
        "azh_htt_zll_a1900_h1600",
        "azh_htt_zll_a1900_h1700",
        "azh_htt_zll_a1900_h1800",
        "azh_htt_zll_a1900_h350",
        "azh_htt_zll_a1900_h400",
        "azh_htt_zll_a1900_h500",
        "azh_htt_zll_a1900_h600",
        "azh_htt_zll_a1900_h700",
        "azh_htt_zll_a1900_h800",
        "azh_htt_zll_a1900_h900",
        "azh_htt_zll_a2000_h1000",
        "azh_htt_zll_a2000_h1100",
        "azh_htt_zll_a2000_h1200",
        "azh_htt_zll_a2000_h1300",
        "azh_htt_zll_a2000_h1400",
        "azh_htt_zll_a2000_h1600",
        "azh_htt_zll_a2000_h1700",
        "azh_htt_zll_a2000_h1800",
        "azh_htt_zll_a2000_h1900",
        "azh_htt_zll_a2000_h350",
        "azh_htt_zll_a2000_h400",
        "azh_htt_zll_a2000_h500",
        "azh_htt_zll_a2000_h600",
        "azh_htt_zll_a2000_h700",
        "azh_htt_zll_a2000_h800",
        "azh_htt_zll_a2000_h900",
        "azh_htt_zll_a2100_h1000",
        "azh_htt_zll_a2100_h1100",
        "azh_htt_zll_a2100_h1200",
        "azh_htt_zll_a2100_h1400",
        "azh_htt_zll_a2100_h1500",
        "azh_htt_zll_a2100_h1700",
        "azh_htt_zll_a2100_h1800",
        "azh_htt_zll_a2100_h1900",
        "azh_htt_zll_a2100_h2000",
        "azh_htt_zll_a2100_h350",
        "azh_htt_zll_a2100_h400",
        "azh_htt_zll_a2100_h500",
        "azh_htt_zll_a2100_h600",
        "azh_htt_zll_a2100_h700",
        "azh_htt_zll_a2100_h800",
        "azh_htt_zll_a2100_h900",
        "azh_htt_zll_a450_h330",
        "azh_htt_zll_a450_h350",
        "azh_htt_zll_a500_h330",
        # "azh_htt_zll_a500_h370",
        "azh_htt_zll_a500_h400",
        "azh_htt_zll_a550_h330",
        "azh_htt_zll_a550_h350",
        "azh_htt_zll_a550_h400",
        "azh_htt_zll_a550_h450",
        "azh_htt_zll_a600_h330",
        "azh_htt_zll_a600_h350",
        "azh_htt_zll_a600_h400",
        "azh_htt_zll_a600_h450",
        "azh_htt_zll_a600_h500",
        "azh_htt_zll_a650_h330",
        "azh_htt_zll_a650_h350",
        "azh_htt_zll_a650_h400",
        "azh_htt_zll_a650_h450",
        "azh_htt_zll_a650_h500",
        "azh_htt_zll_a650_h550",
        "azh_htt_zll_a700_h330",
        "azh_htt_zll_a700_h350",
        # "azh_htt_zll_a700_h370",
        "azh_htt_zll_a700_h400",
        "azh_htt_zll_a700_h450",
        "azh_htt_zll_a700_h500",
        "azh_htt_zll_a700_h550",
        "azh_htt_zll_a750_h330",
        "azh_htt_zll_a750_h350",
        "azh_htt_zll_a750_h400",
        "azh_htt_zll_a750_h450",
        "azh_htt_zll_a750_h500",
        "azh_htt_zll_a750_h550",
        "azh_htt_zll_a750_h600",
        "azh_htt_zll_a750_h650",
        "azh_htt_zll_a800_h330",
        "azh_htt_zll_a800_h350",
        "azh_htt_zll_a800_h400",
        "azh_htt_zll_a800_h450",
        "azh_htt_zll_a800_h500",
        "azh_htt_zll_a800_h550",
        "azh_htt_zll_a800_h600",
        "azh_htt_zll_a800_h650",
        "azh_htt_zll_a800_h700",
        "azh_htt_zll_a850_h330",
        "azh_htt_zll_a850_h350",
        "azh_htt_zll_a850_h400",
        "azh_htt_zll_a850_h450",
        "azh_htt_zll_a850_h500",
        "azh_htt_zll_a850_h550",
        "azh_htt_zll_a850_h600",
        "azh_htt_zll_a850_h650",
        "azh_htt_zll_a850_h700",
        "azh_htt_zll_a850_h750",
        "azh_htt_zll_a900_h330",
        "azh_htt_zll_a900_h350",
        # "azh_htt_zll_a900_h370",
        "azh_htt_zll_a900_h400",
        "azh_htt_zll_a900_h450",
        "azh_htt_zll_a900_h550",
        "azh_htt_zll_a900_h500",
        "azh_htt_zll_a900_h600",
        "azh_htt_zll_a900_h650",
        "azh_htt_zll_a900_h700",
        "azh_htt_zll_a900_h750",
        "azh_htt_zll_a900_h800",
        "azh_htt_zll_a950_h330",
        "azh_htt_zll_a950_h350",
        "azh_htt_zll_a950_h400",
        "azh_htt_zll_a950_h450",
        "azh_htt_zll_a950_h500",
        "azh_htt_zll_a950_h550",
        "azh_htt_zll_a950_h600",
        "azh_htt_zll_a950_h650",
        "azh_htt_zll_a950_h700",
        "azh_htt_zll_a950_h750",
        "azh_htt_zll_a950_h800",
        "azh_htt_zll_a950_h850",
    ]
    # print(process_names)
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

    ######################################################################################
    dataset_names = [
    # DY — use inclusive amcatnlo samples (no stitching needed)
        "dy_m50toinf_amcatnlo",
        "dy_m10to50_amcatnlo",

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
        "st_tchannel_t_4f_powheg",
        "st_tchannel_tbar_4f_powheg",
        "st_twchannel_t_sl_powheg",
        "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg",
        "st_twchannel_tbar_dl_powheg",

    # Diboson
        "ww_pythia",
        "wz_pythia",
        "zz_pythia",

    # W+jets
        "w_lnu_amcatnlo",

    *if_era(year=2022, tag="preEE", values=[
        "data_mu_c",
        "data_mu_d",
        "data_egamma_c",
        "data_egamma_d",
        "data_muoneg_c",
        "data_muoneg_d",
        "ttw_amcatnlo",
        "wwz_pythia",
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
            dataset.add_tag({"is_dy"})
        if dataset.name.startswith("azh"):
            dataset.add_tag({"is_signal"})
        if dataset.name.startswith("data_mu"):
            dataset.add_tag("mu")
        if dataset.name.startswith("data_egamma"):
            dataset.add_tag("egamma")
        if dataset.name.startswith("data_muoneg"):
            dataset.add_tag({"mu", "egamma"})
        # For 2023, data JEC keys have no run-dependent segment in the JSON
        if dataset.name.startswith("data") and year == 2023:
            dataset.set_aux("jec_era", "")

        # add aux info to datasets
        # if dataset.name.startswith("qcd"):
        #     dataset.x.is_qcd = True

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
        # TODO(2023preBPix): add per-era overrides if needed.
        pass
    elif year == 2023 and campaign.x.BPix == "post":
        # TODO(2023postBPix): add per-era overrides if needed.
        pass

    # default calibrator, selector, producer, ml model and inference model
    cfg.x.default_calibrator = "skip_jecunc"
    cfg.x.default_selector = "default"
    cfg.x.default_producer = "default"
    cfg.x.default_weight_producer = "all_weights"
    # cfg.x.default_ml_model = "default"
    # cfg.x.default_ml_model = None
    cfg.x.default_inference_model = "example"
    cfg.x.default_categories = ["cat_incl"]
    cfg.x.default_variables = ["jet1_pt"]
    # cfg.x.default_selector_steps = "default"
    # cfg.x.selector_step_groups = {
    # "default": ["Lepton","Jet"],
    # "cutflow": ["Lepton","Jet"],
    # }

    # process groups for conveniently looping over certain processs
    # (used in wrapper_factory and during plotting)
    cfg.x.process_groups = {
        "all": ["*"],
    }
    # cfg.x.process_groups["dmuch"] = ["data_mu"] + cfg.x.process_groups["much"]
    # cfg.x.process_groups["dech"] = ["data_e"] + cfg.x.process_groups["ech"]

    # dataset groups for conveniently looping over certain datasets
    # (used in wrapper_factory and during plotting)
    cfg.x.dataset_groups = {
        "all": ["*"],
    }

    # category groups for conveniently looping over certain categories
    # (used during plotting)
    cfg.x.category_groups = {
        "default": ["incl"],
        # "leptons_selection": ["catid_selection_2e","catid_selection_2mu"],
        # "leptons": ["catid_2e","catid_2mu"],
        # "m_z": ["sm"],
        # "fe": ["fe"],
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
    # when drawing DY as a line, use a different type of yellow

    cfg.x.variable_settings_groups = {

    }

    # lumi values in inverse pb
    # https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2?rev=2#Combination_and_correlations
    if year == 2022:
        if campaign.x.EE == "pre":
            cfg.x.luminosity = Number(7971, {
                "lumi_13TeV_correlated": 0.014j,
            })
        elif campaign.x.EE == "post":
            cfg.x.luminosity = Number(26337, {
                "lumi_13TeV_correlated": 0.014j,
            })
    elif year == 2023:
        if campaign.x.BPix == "pre":
            cfg.x.luminosity = Number(18062, {
                "lumi_13TeV_correlated": 0.013j,
            })
        elif campaign.x.BPix == "post":
            cfg.x.luminosity = Number(9693, {
                "lumi_13TeV_correlated": 0.013j,
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
        # TODO(2022postEE): re-derive with brilcalc; both PDs run E/F/G.
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}
    elif year == 2023 and campaign.x.BPix == "pre":
        # TODO(2023preBPix): re-derive with brilcalc on C1..C4.
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}
    elif year == 2023 and campaign.x.BPix == "post":
        # TODO(2023postBPix): re-derive with brilcalc on D1..D2.
        cfg.x.channel_lumis = {"muon": nominal, "egamma": nominal, "nominal": nominal}

    # MET filters
    # TODO: Different Met filters for different years
    # https://twiki.cern.ch/twiki/bin/view/CMS/MissingETOptionalFiltersRun2?rev=158#2018_2017_data_and_MC_UL
    cfg.x.met_filters = {
        "Flag.goodVertices",
        "Flag.globalSuperTightHalo2016Filter",
        # "Flag.HBHENoiseFilter",
        # "Flag.HBHENoiseIsoFilter",
        "Flag.EcalDeadCellTriggerPrimitiveFilter",
        "Flag.BadPFMuonFilter",
        "Flag.BadPFMuonDzFilter",
        "Flag.eeBadScFilter",
        #"Flag.ecalBadCalibFilter",
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

    # if year == 2023:
    #     jerc_postfix = ""

    #     jerc_campaign = f"Summer22_22Sep2023"
    if year ==2023:
        jerc_postfix = ""
        if campaign.x.BPix == "post":
            jerc_postfix = "BPix"

        jerc_campaign = f"Summer{year2}{jerc_postfix}Prompt23"

    jet_type = "AK4PFPuppi"

    jer_campaign = jerc_campaign
    if year == 2023:
        jer_campaign += f"_Run{'Cv1234' if campaign.has_tag('preBPix') else 'D'}"

    # print(jerc_campaign)
    if not jerc_postfix == "BPix":
        cfg.x.jec = DotDict.wrap({
            "campaign": jerc_campaign,
            "version": {2016: "V7", 2017: "V5", 2018: "V5", 2022: "V2", 2023: "V2"}[year],
            "jet_type": jet_type,
            "levels": ["L1FastJet", "L2Relative", "L2L3Residual", "L3Absolute"],
            "levels_for_type1_met": ["L1FastJet"],
            "uncertainty_sources": [
                "Total",
            ],
        })
    else:
        cfg.x.jec = DotDict.wrap({
            "campaign": jerc_campaign,
            "version": {2016: "V7", 2017: "V5", 2018: "V5", 2022: "V2", 2023: "V3"}[year],
            "jet_type": jet_type,
            "levels": ["L1FastJet", "L2Relative", "L2L3Residual", "L3Absolute"],
            "levels_for_type1_met": ["L1FastJet"],
            "uncertainty_sources": [
                "Total",
            ],
        })

    # JER
    # https://twiki.cern.ch/twiki/bin/view/CMS/JetResolution?rev=107
    cfg.x.jer = DotDict.wrap({
        "campaign": jer_campaign,
        "version": {2022: "JRV1", 2023:"JRV1"}[year],
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
    # https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation106XUL16preVFP?rev=6
    # https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation106XUL16postVFP?rev=8
    # https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation106XUL17?rev=15
    # https://twiki.cern.ch/twiki/bin/view/CMS/BtagRecommendation106XUL17?rev=17
    # b-tag working points
    # https://btv-wiki.docs.cern.ch/ScaleFactors/Run3Summer22/
    # https://btv-wiki.docs.cern.ch/ScaleFactors/Run3Summer22EE/
    # TODO: add correct 2022 + 2022preEE WP for deepcsv if needed
    if year == 2022:
        btag_key = f"2022{campaign.x.EE}EE" 
    if year == 2023:
        btag_key = f"2023{campaign.x.BPix}BPix" 

    cfg.x.btag_working_points = DotDict.wrap({
        "deepjet": {
            "loose": {
                "2022preEE": 0.0583, "2022postEE": 0.0614,"2023preBPix": 0.0479, "2023postBPix": 0.048,
            }[btag_key],
            "medium": {
                "2022preEE": 0.3086, "2022postEE": 0.3196,"2023preBPix": 0.2431, "2023postBPix": 0.2435,
            }[btag_key],
            "tight": {
                "2022preEE": 0.7183, "2022postEE": 0.7300,"2023preBPix": 0.6553, "2023postBPix": 0.6563,
            }[btag_key],
        },
        #Dont use deepcsv in 2023, not yet defined properly!!
        "deepcsv": {
            "loose": {
                "2022preEE": 0.1208, "2022postEE": 0.1208,"2023preBPix": 0.0479, "2023postBPix": 0.048,
            }[btag_key],
            "medium": {
                "2022preEE": 0.4168, "2022postEE": 0.4168,"2023preBPix": 0.2431, "2023postBPix": 0.2435,
            }[btag_key],
            "tight": {
                "2022preEE": 0.7665, "2022postEE": 0.7665,"2023preBPix": 0.6553, "2023postBPix": 0.6563,
            }[btag_key],
        },
        "particleNet": {
            "loose": {
                "2022preEE": 0.047, "2022postEE": 0.0499,"2023preBPix": 0.0358, "2023postBPix": 0.0359,
            }[btag_key],
            "medium": {
                "2022preEE": 0.245, "2022postEE": 0.2605,"2023preBPix": 0.1917, "2023postBPix": 0.1919,
            }[btag_key],
            "tight": {
                "2022preEE": 0.6734, "2022postEE": 0.6915,"2023preBPix": 0.6172, "2023postBPix": 0.6133,
            }[btag_key],
        },
    })

    # TODO: check e/mu/btag corrections and implement
    # btag weight configuration
    from columnflow.production.cms.btag import SplitBTagSFConfig
    cfg.x.btag_sf = SplitBTagSFConfig(
        # correction_set=("deepJet_light", "deepJet_comb"),
        correction_set=("deepJet_light", "deepJet_comb"),
        discriminator="btagDeepFlavB",
        corrector_kwargs={"working_point": "M"},
    )
    # cfg.x.btag_sf = ("deepJet_shape", cfg.x.btag_sf_jec_sources)
    # from columnflow.production.cms.btag import BTagSFConfig
    # cfg.x.btag_sf = BTagSFConfig(
    # correction_set="deepJet_comb",
    # jec_sources=cfg.x.btag_sf_jec_sources,
    # discriminator="btagDeepFlavB",
    # corrector_kwargs={"working_point": "T"},
    # )

    # names of electron correction sets and working points
    # (used in the electron_sf producer)
    if f"{year}{corr_postfix}" == "2022postEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "Reco20to75")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "wp80iso")
        cfg.x.electron_ss_names = ("Scale", "Smearing")
    elif f"{year}{corr_postfix}" == "2022preEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoBCD", "Reco20to75")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoBCD", "wp80iso")
        cfg.x.electron_ss_names = ("Scale", "Smearing")
    elif f"{year}{corr_postfix}" == "2023postBPix":
        # VERIFY period/WP strings against the JSON (see introspection cmd)
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptD", "Reco20to75")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptD", "wp80iso")
        cfg.x.electron_ss_names = ("2023PromptD_ScaleJSON", "2023PromptD_SmearingJSON")
    elif f"{year}{corr_postfix}" == "2023preBPix":
        # VERIFY period/WP strings against the JSON (see introspection cmd)
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2023PromptC", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2023PromptC", "Reco20to75")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2023PromptC", "wp80iso")
        cfg.x.electron_ss_names = ("2023PromptC_ScaleJSON", "2023PromptC_SmearingJSON")
    # names of muon correction sets and working points
    # (used in the muon producer)
    # TightID muon SF chain (from muon_Z.json):
    # SF(TightID|Tracker) x SF(TightPFIso|TightID) x SF(IsoMu24|TightID+PFIso)
    # Valid down to ~15 GeV (Z tag-and-probe), matching our selection threshold
    cfg.x.muon_sf_id_names = ("NUM_TightID_DEN_TrackerMuons", f"{year}{corr_postfix}")
    cfg.x.muon_sf_iso_names = ("NUM_TightPFIso_DEN_TightID", f"{year}{corr_postfix}")
    cfg.x.muon_sf_trig_names = ("NUM_IsoMu24_or_Mu50_or_CascadeMu100_or_HighPtTkMu100_DEN_CutBasedIdTight_and_PFIsoTight", f"{year}{corr_postfix}")
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

    cfg.x.top_pt_reweighting_params = {
        "a": 0.0615,
        "b": -0.0005,
    }

    # helper to add column aliases for both shifts of a source
    def add_aliases(shift_source: str, aliases: Set[str], selection_dependent: bool):

        for direction in ["up", "down"]:
            shift = cfg.get_shift(od.Shift.join_name(shift_source, direction))
            # format keys and values
            inject_shift = lambda s: re.sub(r"\{([^_])", r"{_\1", s).format(**shift.__dict__)
            _aliases = {inject_shift(key): inject_shift(value) for key, value in aliases.items()}
            alias_type = "column_aliases_selection_dependent" if selection_dependent else "column_aliases"
            # extend existing or register new column aliases
            shift.set_aux(alias_type, shift.get_aux(alias_type, {})).update(_aliases)

    # register shifts
    # TODO: make shifts year-dependent
    cfg.add_shift(name="nominal", id=0)
    cfg.add_shift(name="tune_up", id=1, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="tune_down", id=2, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="hdamp_up", id=3, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="hdamp_down", id=4, type="shape", tags={"disjoint_from_nominal"})
    cfg.add_shift(name="minbias_xs_up", id=7, type="shape")
    cfg.add_shift(name="minbias_xs_down", id=8, type="shape")
    add_aliases("minbias_xs", {"pu_weight": "pu_weight_{name}"}, selection_dependent=False)
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
    add_aliases("e_sf", {"electron_weight": "electron_weight_{direction}"}, selection_dependent=False)

    cfg.add_shift(name="muon_up", id=51, type="shape")
    cfg.add_shift(name="muon_down", id=52, type="shape")
    add_shift_aliases(cfg, "muon", {"muon_weight": "muon_weight_{direction}"})

    # cfg.add_shift(name="mu_trig_sf_up", id=52, type="shape")
    # cfg.add_shift(name="mu_trig_sf_down", id=53, type="shape")
    # add_aliases("mu_sf", {"muon_weight": "muon_weight_{direction}"}, selection_dependent=False)

    # btag_uncs = [
    #     "hf", "lf", f"hfstats1_{year}", f"hfstats2_{year}",
    #     f"lfstats1_{year}", f"lfstats2_{year}", "cferr1", "cferr2",
    # ]
    btag_uncs = []
    for i, unc in enumerate(btag_uncs):
        cfg.add_shift(name=f"btag_{unc}_up", id=100 + 2 * i, type="shape")
        cfg.add_shift(name=f"btag_{unc}_down", id=101 + 2 * i, type="shape")
        # add_aliases(
        #     f"btag_{unc}",
        #     {
        #         "normalized_btag_weight": f"normalized_btag_weight_{unc}_" + "{direction}",
        #         "normalized_njet_btag_weight": f"normalized_njet_btag_weight_{unc}_" + "{direction}",
        #     },
        #     selection_dependent=False,
        # )

    cfg.add_shift(name="mur_up", id=201, type="shape")
    cfg.add_shift(name="mur_down", id=202, type="shape")
    cfg.add_shift(name="muf_up", id=203, type="shape")
    cfg.add_shift(name="muf_down", id=204, type="shape")
    cfg.add_shift(name="murf_envelope_up", id=205, type="shape")
    cfg.add_shift(name="murf_envelope_down", id=206, type="shape")
    cfg.add_shift(name="pdf_up", id=207, type="shape")
    cfg.add_shift(name="pdf_down", id=208, type="shape")

    for unc in ["mur", "muf", "murf_envelope", "pdf"]:
        # add_aliases(unc, {f"{unc}_weight": f"{unc}_weight_" + "{direction}"}, selection_dependent=False)
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
            {"Jet.pt": "Jet.pt_{name}", "Jet.mass": "Jet.mass_{name}"},
            selection_dependent=True,
        )

    cfg.add_shift(name="jer_up", id=6000, type="shape", tags={"selection_dependent"})
    cfg.add_shift(name="jer_down", id=6001, type="shape", tags={"selection_dependent"})
    add_aliases("jer", {"Jet.pt": "Jet.pt_{name}", "Jet.mass": "Jet.mass_{name}"}, selection_dependent=True)

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
    json_mirror = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration"
    # json_mirror = "/afs/cern.ch/user/m/mrieger/public/mirrors/jsonpog-integration-c9422789"
    local_repo = "/data/dust/user/matthiej/topsf"  # TODO: avoid hardcoding path

    if year == 2022:
        corr_tag = f"{year}_Summer22{jerc_postfix}"
    if year == 2023:
        corr_tag = f"{year}_Summer23{jerc_postfix}"
    cfg.x.external_files = DotDict.wrap({
        # pileup weight corrections
        "pu_sf": (f"{json_mirror}/POG/LUM/{corr_tag}/puWeights.json.gz", "v1"),

        # jet energy correction
        "jet_jerc": (f"{json_mirror}/POG/JME/{corr_tag}/jet_jerc.json.gz", "v1"),

        # electron scale factors
        # "electron_sf": (f"{json_mirror}/POG/EGM/{corr_tag}/electron.json.gz", "v1"),
        "electron_sf": (f"{json_mirror}/POG/EGM/{corr_tag}/electron.json.gz", "v1"),

        # muon scale factors
        "muon_sf": (f"{json_mirror}/POG/MUO/{corr_tag}/muon_Z.json.gz", "v1"),
        "electron_sf_hlt": (f"{json_mirror}/POG/EGM/{corr_tag}/electronHlt.json.gz", "v1"),

        # btag scale factor
        # "btag_sf_corr": (f"{json_mirror}/POG/BTV/{corr_tag}/btagging.json.gz", "v1"),
        "btag_sf_corr": (f"{json_mirror}/POG/BTV/{corr_tag}/btagging.json.gz", "v1"),

        # V+jets reweighting
        #"vjets_reweighting": f"{local_repo}/data/json/vjets_reweighting.json.gz",

        # jet veto map
        "jet_veto_map": (f"{json_mirror}/POG/JME/{corr_tag}/jetvetomaps.json.gz", "v1"),

        # muon Rochester-like scale & smearing — per-era JSON.
        # Run tasks/check_muon_scalesmearing.py at DESY to verify these
        # exist. Source: https://github.com/cms-muon-pog/MuonScaRe
        "muon_scalesmearing": ({
            "2022preEE":   "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2022_Summer22/muon_scalesmearing.json.gz",
            "2022postEE":  "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2022_Summer22EE/muon_scalesmearing.json.gz",
            "2023preBPix": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2023_Summer23/muon_scalesmearing.json.gz",
            "2023postBPix":"/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2023_Summer23BPix/muon_scalesmearing.json.gz",
        }[f"{year}{corr_postfix}"], "v1"),

        # electron scale & smearing
        "electron_ss": (f"{json_mirror}/POG/EGM/{corr_tag}/electronSS.json.gz", "v1"),
    })

    # external files with more complex year dependence
    # TODO: generalize to different years

    if year == 2022 and campaign.x.EE == "pre":
        cfg.x.external_files.update(DotDict.wrap({
            # files from https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideGoodLumiSectionsJSONFile
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json", "v1"),  # noqa
                "normtag": ("/afs/cern.ch/user/l/lumipro/public/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileup_JSON.txt", "v1"),  # noqa
                # "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCDEFG/pileup_JSON.txt", "v1"),  # noqa
                "mc_profile": ("https://raw.githubusercontent.com/cms-sw/cmssw/bb525104a7ddb93685f8ced6fed1ab793b2d2103/SimGeneral/MixingModule/python/Run3_2022_LHC_Simulation_10h_2h_cfi.py", "v1"),  # noqa
                "data_profile": {
                    # "nominal": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileupHistogram-Cert_Collisions2022_355100_357900_eraBCD_GoldenJson-13p6TeV-69200ub-99bins.root", "v1"),  # noqa
                    # "minbias_xs_up": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileupHistogram-Cert_Collisions2022_355100_357900_eraBCD_GoldenJson-13p6TeV-72400ub-99bins.root", "v1"),  # noqa
                    # "minbias_xs_down": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileupHistogram-Cert_Collisions2022_355100_357900_eraBCD_GoldenJson-13p6TeV-66000ub-99bins.root", "v1"),  # noqa
                    "nominal": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-69200ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_up": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-72400ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_down": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-66000ub-100bins.root", "v1"),  # noqa
                },
            },
        }))
    elif year == 2022 and campaign.x.EE == "post":
        cfg.x.external_files.update(DotDict.wrap({
            # files from https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideGoodLumiSectionsJSONFile
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/Cert_Collisions2022_355100_362760_Golden.json", "v1"),  # noqa
                "normtag": ("/afs/cern.ch/user/l/lumipro/public/Normtags/normtag_PHYSICS.json", "v1"),
            },
            "pu": {
                # "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/EFG/pileup_JSON.txt", "v1"),  # noqa
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCDEFG/pileup_JSON.txt", "v1"),  # noqa
                "mc_profile": ("https://raw.githubusercontent.com/cms-sw/cmssw/bb525104a7ddb93685f8ced6fed1ab793b2d2103/SimGeneral/MixingModule/python/Run3_2022_LHC_Simulation_10h_2h_cfi.py", "v1"),  # noqa
                "data_profile": {
                    # data profiles were produced with 99 bins instead of 100 --> use custom produced data profiles instead  # noqa
                    # "nominal": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/EFG/pileupHistogram-Cert_Collisions2022_359022_362760_eraEFG_GoldenJson-13p6TeV-69200ub-99bins.root", "v1"),  # noqa
                    # "minbias_xs_up": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/EFG/pileupHistogram-Cert_Collisions2022_359022_362760_eraEFG_GoldenJson-13p6TeV-72400ub-99bins.root", "v1"),  # noqa
                    # "minbias_xs_down": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/EFG/pileupHistogram-Cert_Collisions2022_359022_362760_eraEFG_GoldenJson-13p6TeV-66000ub-99bins.root", "v1"),  # noqa
                    "nominal": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-69200ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_up": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-72400ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_down": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions22/pileupHistogram-Cert_Collisions2022_355100_362760_GoldenJson-13p6TeV-66000ub-100bins.root", "v1"),  # noqa
                },
            },
        }))
    elif year == 2023 and campaign.x.BPix == "pre":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json", "v1"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_BRIL.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/BCD/pileup_JSON.txt", "v1"),  # noqa
                # TODO(2023): switch mc_profile to the 2023 Simulation file
                # (Run3_2023_LHC_Simulation_*) once you have the right
                # cmssw revision pinned. The 2022 file is used as a
                # fallback here.
                "mc_profile": ("https://raw.githubusercontent.com/cms-sw/cmssw/bb525104a7ddb93685f8ced6fed1ab793b2d2103/SimGeneral/MixingModule/python/Run3_2022_LHC_Simulation_10h_2h_cfi.py", "v1"),  # noqa
                # NOTE: the histograms below currently use the combined
                # 2023 golden-JSON pileup (Collisions2023_366442_370790).
                # For a fully era-resolved correction, regenerate against
                # only the preBPix run range (Cv1234, runs <= 370580)
                # using pileupCalc and update these paths.
                "data_profile": {
                    "nominal": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-69200ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_up": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-72400ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_down": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-66000ub-100bins.root", "v1"),  # noqa
                },
            },
        }))
    elif year == 2023 and campaign.x.BPix == "post":
        cfg.x.external_files.update(DotDict.wrap({
            "lumi": {
                "golden": ("https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/Cert_Collisions2023_366442_370790_Golden.json", "v1"),  # noqa
                "normtag": ("/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags/normtag_BRIL.json", "v1"),
            },
            "pu": {
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions23/PileUp/BCD/pileup_JSON.txt", "v1"),  # noqa
                # See preBPix block above re: mc_profile.
                "mc_profile": ("https://raw.githubusercontent.com/cms-sw/cmssw/bb525104a7ddb93685f8ced6fed1ab793b2d2103/SimGeneral/MixingModule/python/Run3_2022_LHC_Simulation_10h_2h_cfi.py", "v1"),  # noqa
                # NOTE: see preBPix block re: data_profile histograms.
                # For postBPix specifically you want runs >= 370581.
                "data_profile": {
                    "nominal": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-69200ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_up": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-72400ub-100bins.root", "v1"),  # noqa
                    "minbias_xs_down": (f"/afs/cern.ch/user/a/anhaddad/public/Collisions23/pileupHistogram-Cert_Collisions2023_366442_370790_GoldenJson-13p6TeV-66000ub-100bins.root", "v1"),  # noqa
                },
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
            "murf_envelope_weight*", "mur_weight*", "muf_weight*",
            "btag_weight*",
            "Pileup.nTrueInt",
            "LHEScaleWeight",
            "GenPart.*",
        } | set(  # Jets
            f"{jet_obj}.{field}"
            for jet_obj in ["Jet"]
            for field in ["pt", "eta", "phi", "mass", "genJetIdx", "btagDeepFlavB", "hadronFlavour", "rawFactor", "btagDeepFlavQG"]
        ) | set(  # BJets
            f"{jet_obj}.{field}"
            for jet_obj in ["BJet"]
            for field in ["pt", "eta", "phi", "mass", "btagDeepFlavB", "hadronFlavour"]
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
            f"MET.{field}"
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
    cfg.x.event_weights = DotDict({
        "normalization_weight": [],
        "channel_lumi_weight": [],   # per-channel lumi correction (muon: x0.9344, ee: x1.0023)
        "electron_trig_weight": [],
        "muon_trig_weight": [],     # re-enabled: muon_Z.json HLT SFs valid down to ~15 GeV
        "electron_weight": [],       # electron reco above 75
        "electron_mid_weight": [],   # electron reco 20-75
        "electron_id_weight": [],    # electron MVA WP80iso
        "muon_id_weight": [],       # TightID SF (muon_Z.json, valid 15+ GeV)
        "muon_iso_weight": [],      # TightPFIso SF (muon_Z.json, valid 15+ GeV)
        "pu_weight": [],
        #         "zpt_weight": [],
        # "btag_weight": [],
        # mur/muf kept as systematics only, not applied at nominal
        # "mur_weight": get_shifts("mur"),
        # "muf_weight": get_shifts("muf"),
        # "top_pt_weight": [],
        # "muon_weight": get_shifts("muon"),
    })

    for dataset in cfg.datasets:
        if dataset.x("is_ttbar", False):
            dataset.x.event_weights = {"top_pt_weight": []}

    # NOTE: which to use, njet_btag_weight or btag_weight?
    # cfg.x.event_weights["normalized_btag_weight"] = get_shifts(*(f"btag_{unc}" for unc in btag_uncs))
    # TODO: fix pu_weight; takes way too large values (from 0 to 160)
    # cfg.x.event_weights["normalized_pu_weight"] = get_shifts("minbias_xs")
    # for dataset in cfg.datasets:
    #     dataset.x.event_weights = DotDict()
    #     if not dataset.x("is_qcd", False):
    #         # pdf/scale weights for all non-qcd datasets
    #         dataset.x.event_weights["normalized_murf_envelope_weight"] = get_shifts("murf_envelope")
    #         dataset.x.event_weights["normalized_mur_weight"] = get_shifts("mur")
    #         dataset.x.event_weights["normalized_muf_weight"] = get_shifts("muf")
    #         dataset.x.event_weights["normalized_pdf_weight"] = get_shifts("pdf")

    # dev_version = "v0"
    prod_version = "v1"

    # def reduce_version(cls, inst, params):
    #     version = dev_version
    #     if params.get("selector") == "default":
    #         version = prod_version

    #     return version

    # Version of required tasks
    cfg.x.versions = {
        "cf.CalibrateEvents": "v0",
        "cf.SelectEvents": prod_version,
        "cf.MergeSelectionStats": prod_version,
        "cf.MergeSelectionMasks": prod_version,
        "cf.ReduceEvents": prod_version,
        "cf.MergeReductionStats": prod_version,
        "cf.MergeReduceEvents": prod_version,
        "cf.ProvideReducedEvents": prod_version,
        "cf.ProduceColumns": prod_version,
        # "cf.MergeMLEvents": prod_version,
        # "cf.MergeMLStats": prod_version,
        # "cf.PrepareMLEvents": prod_version,
        # "cf.MLTraining": prod_version,
    }

    # add categories

    # add_category(
    #     cfg,
    #     id=1,
    #     name="incl",
    #     selection="cat_incl",
    #     label="inclusive",
    # )

    # add_category(
    #     cfg,
    #     name="2j",
    #     id=2,
    #     selection="cat_2j",
    #     label="2 jets",
    # )

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
    if year == 2023:
        from azh.config.triggers import add_triggers_2023
        add_triggers_2023(cfg)

    # only produce cutflow features when number of dataset_files is limited (used in selection module)
    cfg.x.do_cutflow_features = bool(limit_dataset_files) and limit_dataset_files <= 10
    return cfg
