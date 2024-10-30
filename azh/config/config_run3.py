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

from columnflow.util import DotDict
# import functools
# from dijet.config.datasets import get_dataset_lfns
from azh.config.analysis_azh_run3 import analysis_azh
from azh.config.categories import add_categories_selection
from azh.config.variables import add_variables
# from azh.config.cutflow_variables import add_cutflow_variables
from columnflow.config_util import (
    get_root_processes_from_campaign, add_shift_aliases,
)


thisdir = os.path.dirname(os.path.abspath(__file__))


def add_config(
    analysis: od.Analysis,
    campaign: od.Campaign,
    config_name: str | None = None,
    config_id: int | None = None,
    limit_dataset_files: int | None = None,
) -> od.Config:
    # validations
    print("Weclome")
    assert campaign.x.year in [2022, 2023]
    if campaign.x.year == 2022:
        assert campaign.x.EE in ["pre", "post"]
    elif campaign.x.year == 2023:
        assert campaign.x.BPix in ["pre", "post"]

    # gather campaign data
    year = campaign.x.year
    year2 = year % 100
    corr_postfix = ""
    if year == 2022:
        corr_postfix = f"{campaign.x.EE}EE"
    elif year == 2023:
        corr_postfix = f"{campaign.x.BPix}BPix"

    implemented_years = [2022]

    if year not in implemented_years:
        raise NotImplementedError("For now, only 2022 campaign is fully implemented")

    # get all root processes
    procs = get_root_processes_from_campaign(campaign)

    # create a config by passing the campaign, so id and name will be identical
    cfg = analysis_azh.add_config(campaign, name=config_name, id=config_id)
    # use custom get_dataset_lfns function
    # cfg.x.get_dataset_lfns = get_dataset_lfns

    # add processes we are interested in

    # set color of some processes
    # set color of some processes
    colors = {
        "dy": "#FBFF36",  # yellow
        "data": "#000000",  # black
        "tt": "#E04F21",  # red
        "ttv": "#5E8FFC",  # blue
        "w_lnu": "#82FF28",  # green
        "higgs": "#984ea3",  # purple
        "st": "#3E00FB",  # dark purple
        "vv": "#B900FC",  # pink
        "other": "#999999",  # grey
    }

    # add datasets we need to study
    process_names = [
        "dy",
        "tt",
        "ttv",
        "st",
        "w_lnu",
        "vv",
        "data",
        # "azh",
    ]
    print(process_names)
    for process_name in process_names:
        cfg.add_process(procs.get(process_name))
        cfg.get_process(process_name).color1 = colors.get(process_name, "#aaaaaa")
        cfg.get_process(process_name).color2 = colors.get(process_name, "#000000")

    dataset_names = [
        # TT
        "tt_sl_powheg",
        "tt_dl_powheg",
        "tt_fh_powheg",
        # # TTV
        "ttz_zll_m4to50_amcatnlo",
        "ttz_zll_m50toinf_amcatnlo",
        # "ttw_amcatnlo",
        # "ttw_wlnu_amcatnlo",
        # "ttz_zqq_amcatnlo",
        # "ttz_zll_m4to50_amcatnlo",
        # "ttz_zll_m50toinf_amcatnlo",
        # "ttw_wqq_amcatnlo",
        # # ST
        "st_tchannel_tbar_4f_powheg",
        "st_tchannel_t_4f_powheg",
        "st_twchannel_tbar_dl_powheg",
        # "st_twchannel_tbar_fh_powheg",
        "st_twchannel_tbar_sl_powheg",
        "st_twchannel_t_dl_powheg",
        # "st_twchannel_t_fh_powheg",
        "st_twchannel_t_sl_powheg",
        # "st_schannel_t_lep_4f_amcatnlo",
        # "st_schannel_tbar_lep_4f_amcatnlo",
        # # WJets
        #empty at the moment
        # "w_lnu_amcatnlo",
        # # DY
        "dy_m50toinf_1j_madgraph",
        "dy_m50toinf_2j_madgraph",
        "dy_m50toinf_3j_madgraph",
        "dy_m50toinf_4j_madgraph",
        # "dy_m50toinf_1j_pt40to100_amcatnlo",
        # "dy_m50toinf_1j_pt100to200_amcatnlo",
        # "dy_m50toinf_1j_pt200to400_amcatnlo",
        # "dy_m50toinf_1j_pt400to600_amcatnlo",
        # "dy_m50toinf_1j_pt600toinf_amcatnlo",
        # "dy_m50toinf_2j_pt40to100_amcatnlo",
        # "dy_m50toinf_2j_pt100to200_amcatnlo",
        # "dy_m50toinf_2j_pt200to400_amcatnlo",
        # "dy_m50toinf_2j_pt400to600_amcatnlo",
        # "dy_m50toinf_2j_pt600toinf_amcatnlo",
        # "dy_m50toinf_ht70to100_madgraph",
        # "dy_m50toinf_ht100to200_madgraph",
        # "dy_m50toinf_ht200to400_madgraph",
        # "dy_m50toinf_ht400to600_madgraph",
        # "dy_m50toinf_ht600to800_madgraph",
        # "dy_m50toinf_ht800to1200_madgraph",
        # "dy_m50toinf_ht1200to2500_madgraph",
        # "dy_m50toinf_ht2500toinf_madgraph",
        # # VV
        "zz_pythia",
        "wz_pythia",
        "ww_pythia",

        # Data
        # # Double Muon
        # "data_doublemu_a",
        # "data_doublemu_b",
        # "data_doublemu_c",
        # # muon
        "data_mu_c",
        "data_mu_d",
        # #  EG
        # "data_egamma_a",
        # "data_egamma_b",
        "data_egamma_c",
        "data_egamma_d",
        # # Muon EG
        # "data_muoneg_a",
        # "data_muoneg_b",
        "data_muoneg_c",
        "data_muoneg_d",

        # Signal
        # AZH
        # "azh_htt_zll_a1000_h330_amcatnlo",
        # "azh_htt_zll_a1000_h350_amcatnlo",
        # "azh_htt_zll_a1000_h400_amcatnlo",
        # "azh_htt_zll_a1000_h450_amcatnlo",
        # "azh_htt_zll_a1000_h500_amcatnlo",
        # "azh_htt_zll_a1000_h550_amcatnlo",
        # "azh_htt_zll_a1000_h600_amcatnlo",
        # "azh_htt_zll_a1000_h650_amcatnlo",
        # "azh_htt_zll_a1000_h700_amcatnlo",
        # "azh_htt_zll_a1000_h750_amcatnlo",
        # "azh_htt_zll_a1000_h800_amcatnlo",
        # "azh_htt_zll_a1000_h850_amcatnlo",
        # "azh_htt_zll_a1000_h900_amcatnlo",
        # "azh_htt_zll_a1050_h330_amcatnlo",
        # "azh_htt_zll_a1050_h350_amcatnlo",
        # "azh_htt_zll_a1050_h400_amcatnlo",
        # "azh_htt_zll_a1050_h450_amcatnlo",
        # "azh_htt_zll_a1050_h500_amcatnlo",
        # "azh_htt_zll_a1050_h550_amcatnlo",
        # "azh_htt_zll_a1050_h600_amcatnlo",
        # "azh_htt_zll_a1050_h700_amcatnlo",
        # "azh_htt_zll_a1050_h750_amcatnlo",
        # "azh_htt_zll_a1050_h800_amcatnlo",
        # "azh_htt_zll_a1050_h850_amcatnlo",
        # "azh_htt_zll_a1050_h900_amcatnlo",
        # "azh_htt_zll_a1050_h950_amcatnlo",
        # "azh_htt_zll_a1100_h1000_amcatnlo",
        # "azh_htt_zll_a1100_h330_amcatnlo",
        # "azh_htt_zll_a1100_h350_amcatnlo",
        # "azh_htt_zll_a1100_h400_amcatnlo",
        # "azh_htt_zll_a1100_h450_amcatnlo",
        # "azh_htt_zll_a1100_h500_amcatnlo",
        # "azh_htt_zll_a1100_h550_amcatnlo",
        # "azh_htt_zll_a1100_h600_amcatnlo",
        # "azh_htt_zll_a1100_h650_amcatnlo",
        # "azh_htt_zll_a1100_h700_amcatnlo",
        # "azh_htt_zll_a1100_h750_amcatnlo",
        # "azh_htt_zll_a1100_h800_amcatnlo",
        # "azh_htt_zll_a1100_h850_amcatnlo",
        # "azh_htt_zll_a1100_h900_amcatnlo",
        # "azh_htt_zll_a1100_h950_amcatnlo",
        # "azh_htt_zll_a1150_h1050_amcatnlo",
        # "azh_htt_zll_a1150_h330_amcatnlo",
        # "azh_htt_zll_a1150_h350_amcatnlo",
        # "azh_htt_zll_a1150_h450_amcatnlo",
        # "azh_htt_zll_a1150_h550_amcatnlo",
        # "azh_htt_zll_a1150_h650_amcatnlo",
        # "azh_htt_zll_a1150_h750_amcatnlo",
        # "azh_htt_zll_a1150_h850_amcatnlo",
        # "azh_htt_zll_a1150_h950_amcatnlo",
        # "azh_htt_zll_a1200_h1000_amcatnlo",
        # "azh_htt_zll_a1200_h1100_amcatnlo",
        # "azh_htt_zll_a1200_h330_amcatnlo",
        # "azh_htt_zll_a1200_h350_amcatnlo",
        # "azh_htt_zll_a1200_h400_amcatnlo",
        # "azh_htt_zll_a1200_h500_amcatnlo",
        # "azh_htt_zll_a1200_h600_amcatnlo",
        # "azh_htt_zll_a1200_h700_amcatnlo",
        # "azh_htt_zll_a1200_h800_amcatnlo",
        # "azh_htt_zll_a1200_h850_amcatnlo",
        # "azh_htt_zll_a1200_h900_amcatnlo",
        # "azh_htt_zll_a1300_h1000_amcatnlo",
        # "azh_htt_zll_a1300_h1100_amcatnlo",
        # "azh_htt_zll_a1300_h1200_amcatnlo",
        # "azh_htt_zll_a1300_h350_amcatnlo",
        # "azh_htt_zll_a1300_h400_amcatnlo",
        # "azh_htt_zll_a1300_h500_amcatnlo",
        # "azh_htt_zll_a1300_h600_amcatnlo",
        # "azh_htt_zll_a1300_h700_amcatnlo",
        # "azh_htt_zll_a1300_h800_amcatnlo",
        # "azh_htt_zll_a1300_h900_amcatnlo",
        # "azh_htt_zll_a1400_h1000_amcatnlo",
        # "azh_htt_zll_a1400_h1100_amcatnlo",
        # "azh_htt_zll_a1400_h1200_amcatnlo",
        # "azh_htt_zll_a1400_h1300_amcatnlo",
        # "azh_htt_zll_a1400_h350_amcatnlo",
        # "azh_htt_zll_a1400_h400_amcatnlo",
        # "azh_htt_zll_a1400_h500_amcatnlo",
        # "azh_htt_zll_a1400_h600_amcatnlo",
        # "azh_htt_zll_a1400_h700_amcatnlo",
        # "azh_htt_zll_a1400_h800_amcatnlo",
        # "azh_htt_zll_a1400_h900_amcatnlo",
        # "azh_htt_zll_a1500_h1000_amcatnlo",
        # "azh_htt_zll_a1500_h1100_amcatnlo",
        # "azh_htt_zll_a1500_h1200_amcatnlo",
        # "azh_htt_zll_a1500_h1300_amcatnlo",
        # "azh_htt_zll_a1500_h1400_amcatnlo",
        # "azh_htt_zll_a1500_h350_amcatnlo",
        # "azh_htt_zll_a1500_h400_amcatnlo",
        # "azh_htt_zll_a1500_h500_amcatnlo",
        # "azh_htt_zll_a1500_h600_amcatnlo",
        # "azh_htt_zll_a1500_h700_amcatnlo",
        # "azh_htt_zll_a1500_h900_amcatnlo",
        # "azh_htt_zll_a1600_h1000_amcatnlo",
        # "azh_htt_zll_a1600_h1100_amcatnlo",
        # "azh_htt_zll_a1600_h1200_amcatnlo",
        # "azh_htt_zll_a1600_h1300_amcatnlo",
        # "azh_htt_zll_a1600_h1400_amcatnlo",
        # "azh_htt_zll_a1600_h1500_amcatnlo",
        # "azh_htt_zll_a1600_h350_amcatnlo",
        # "azh_htt_zll_a1600_h400_amcatnlo",
        # "azh_htt_zll_a1600_h500_amcatnlo",
        # "azh_htt_zll_a1600_h600_amcatnlo",
        # "azh_htt_zll_a1600_h900_amcatnlo",
        # "azh_htt_zll_a1700_h1000_amcatnlo",
        # "azh_htt_zll_a1700_h1100_amcatnlo",
        # "azh_htt_zll_a1700_h1200_amcatnlo",
        # "azh_htt_zll_a1700_h1300_amcatnlo",
        # "azh_htt_zll_a1700_h1400_amcatnlo",
        # "azh_htt_zll_a1700_h1500_amcatnlo",
        # "azh_htt_zll_a1700_h1600_amcatnlo",
        # "azh_htt_zll_a1700_h350_amcatnlo",
        # "azh_htt_zll_a1700_h400_amcatnlo",
        # "azh_htt_zll_a1700_h500_amcatnlo",
        # "azh_htt_zll_a1700_h600_amcatnlo",
        # "azh_htt_zll_a1700_h700_amcatnlo",
        # "azh_htt_zll_a1700_h800_amcatnlo",
        # "azh_htt_zll_a1700_h900_amcatnlo",
        # "azh_htt_zll_a1800_h1000_amcatnlo",
        # "azh_htt_zll_a1800_h1100_amcatnlo",
        # "azh_htt_zll_a1800_h1200_amcatnlo",
        # "azh_htt_zll_a1800_h1300_amcatnlo",
        # "azh_htt_zll_a1800_h1400_amcatnlo",
        # "azh_htt_zll_a1800_h1500_amcatnlo",
        # "azh_htt_zll_a1800_h1600_amcatnlo",
        # "azh_htt_zll_a1800_h1700_amcatnlo",
        # "azh_htt_zll_a1800_h350_amcatnlo",
        # "azh_htt_zll_a1800_h400_amcatnlo",
        # "azh_htt_zll_a1800_h500_amcatnlo",
        # "azh_htt_zll_a1800_h600_amcatnlo",
        # "azh_htt_zll_a1800_h700_amcatnlo",
        # "azh_htt_zll_a1800_h800_amcatnlo",
        # "azh_htt_zll_a1800_h900_amcatnlo",
        # "azh_htt_zll_a1900_h1000_amcatnlo",
        # "azh_htt_zll_a1900_h1100_amcatnlo",
        # "azh_htt_zll_a1900_h1200_amcatnlo",
        # "azh_htt_zll_a1900_h1300_amcatnlo",
        # "azh_htt_zll_a1900_h1400_amcatnlo",
        # "azh_htt_zll_a1900_h1500_amcatnlo",
        # "azh_htt_zll_a1900_h1600_amcatnlo",
        # "azh_htt_zll_a1900_h1700_amcatnlo",
        # "azh_htt_zll_a1900_h1800_amcatnlo",
        # "azh_htt_zll_a1900_h350_amcatnlo",
        # "azh_htt_zll_a1900_h400_amcatnlo",
        # "azh_htt_zll_a1900_h500_amcatnlo",
        # "azh_htt_zll_a1900_h600_amcatnlo",
        # "azh_htt_zll_a1900_h700_amcatnlo",
        # "azh_htt_zll_a1900_h800_amcatnlo",
        # "azh_htt_zll_a1900_h900_amcatnlo",
        # "azh_htt_zll_a2000_h1000_amcatnlo",
        # "azh_htt_zll_a2000_h1100_amcatnlo",
        # "azh_htt_zll_a2000_h1200_amcatnlo",
        # "azh_htt_zll_a2000_h1300_amcatnlo",
        # "azh_htt_zll_a2000_h1400_amcatnlo",
        # "azh_htt_zll_a2000_h1600_amcatnlo",
        # "azh_htt_zll_a2000_h1700_amcatnlo",
        # "azh_htt_zll_a2000_h1800_amcatnlo",
        # "azh_htt_zll_a2000_h1900_amcatnlo",
        # "azh_htt_zll_a2000_h350_amcatnlo",
        # "azh_htt_zll_a2000_h400_amcatnlo",
        # "azh_htt_zll_a2000_h500_amcatnlo",
        # "azh_htt_zll_a2000_h600_amcatnlo",
        # "azh_htt_zll_a2000_h700_amcatnlo",
        # "azh_htt_zll_a2000_h800_amcatnlo",
        # "azh_htt_zll_a2000_h900_amcatnlo",
        # "azh_htt_zll_a2100_h1000_amcatnlo",
        # "azh_htt_zll_a2100_h1100_amcatnlo",
        # "azh_htt_zll_a2100_h1200_amcatnlo",
        # "azh_htt_zll_a2100_h1300_amcatnlo",
        # "azh_htt_zll_a2100_h1400_amcatnlo",
        # "azh_htt_zll_a2100_h1500_amcatnlo",
        # "azh_htt_zll_a2100_h1700_amcatnlo",
        # "azh_htt_zll_a2100_h1800_amcatnlo",
        # "azh_htt_zll_a2100_h1900_amcatnlo",
        # "azh_htt_zll_a2100_h2000_amcatnlo",
        # "azh_htt_zll_a2100_h350_amcatnlo",
        # "azh_htt_zll_a2100_h400_amcatnlo",
        # "azh_htt_zll_a2100_h500_amcatnlo",
        # "azh_htt_zll_a2100_h600_amcatnlo",
        # "azh_htt_zll_a2100_h700_amcatnlo",
        # "azh_htt_zll_a2100_h800_amcatnlo",
        # "azh_htt_zll_a2100_h900_amcatnlo",
        # "azh_htt_zll_a430_h330_amcatnlo",
        # "azh_htt_zll_a450_h330_amcatnlo",
        # "azh_htt_zll_a450_h350_amcatnlo",
        # "azh_htt_zll_a500_h330_amcatnlo",
        # "azh_htt_zll_a500_h350_amcatnlo",
        # "azh_htt_zll_a500_h370_amcatnlo",
        # "azh_htt_zll_a500_h400_amcatnlo",
        # "azh_htt_zll_a550_h330_amcatnlo",
        # "azh_htt_zll_a550_h350_amcatnlo",
        # "azh_htt_zll_a550_h400_amcatnlo",
        # "azh_htt_zll_a550_h450_amcatnlo",
        # "azh_htt_zll_a600_h330_amcatnlo",
        # "azh_htt_zll_a600_h350_amcatnlo",
        # "azh_htt_zll_a600_h400_amcatnlo",
        # "azh_htt_zll_a600_h450_amcatnlo",
        # "azh_htt_zll_a600_h500_amcatnlo",
        # "azh_htt_zll_a650_h330_amcatnlo",
        # "azh_htt_zll_a650_h350_amcatnlo",
        # "azh_htt_zll_a650_h400_amcatnlo",
        # "azh_htt_zll_a650_h450_amcatnlo",
        # "azh_htt_zll_a650_h500_amcatnlo",
        # "azh_htt_zll_a650_h550_amcatnlo",
        # "azh_htt_zll_a700_h330_amcatnlo",
        # "azh_htt_zll_a700_h350_amcatnlo",
        # "azh_htt_zll_a700_h370_amcatnlo",
        # "azh_htt_zll_a700_h400_amcatnlo",
        # "azh_htt_zll_a700_h450_amcatnlo",
        # "azh_htt_zll_a700_h500_amcatnlo",
        # "azh_htt_zll_a700_h550_amcatnlo",
        # "azh_htt_zll_a750_h330_amcatnlo",
        # "azh_htt_zll_a750_h350_amcatnlo",
        # "azh_htt_zll_a750_h400_amcatnlo",
        # "azh_htt_zll_a750_h450_amcatnlo",
        # "azh_htt_zll_a750_h500_amcatnlo",
        # "azh_htt_zll_a750_h550_amcatnlo",
        # "azh_htt_zll_a750_h600_amcatnlo",
        # "azh_htt_zll_a750_h650_amcatnlo",
        # "azh_htt_zll_a800_h330_amcatnlo",
        # "azh_htt_zll_a800_h350_amcatnlo",
        # "azh_htt_zll_a800_h400_amcatnlo",
        # "azh_htt_zll_a800_h450_amcatnlo",
        # "azh_htt_zll_a800_h500_amcatnlo",
        # "azh_htt_zll_a800_h550_amcatnlo",
        # "azh_htt_zll_a800_h600_amcatnlo",
        # "azh_htt_zll_a800_h650_amcatnlo",
        # "azh_htt_zll_a800_h700_amcatnlo",
        # "azh_htt_zll_a850_h330_amcatnlo",
        # "azh_htt_zll_a850_h350_amcatnlo",
        # "azh_htt_zll_a850_h400_amcatnlo",
        # "azh_htt_zll_a850_h450_amcatnlo",
        # "azh_htt_zll_a850_h500_amcatnlo",
        # "azh_htt_zll_a850_h550_amcatnlo",
        # "azh_htt_zll_a850_h600_amcatnlo",
        # "azh_htt_zll_a850_h650_amcatnlo",
        # "azh_htt_zll_a850_h700_amcatnlo",
        # "azh_htt_zll_a850_h750_amcatnlo",
        # "azh_htt_zll_a900_h330_amcatnlo",
        # "azh_htt_zll_a900_h350_amcatnlo",
        # "azh_htt_zll_a900_h370_amcatnlo",
        # "azh_htt_zll_a900_h400_amcatnlo",
        # "azh_htt_zll_a900_h450_amcatnlo",
        # "azh_htt_zll_a900_h550_amcatnlo",
        # "azh_htt_zll_a900_h500_amcatnlo",
        # "azh_htt_zll_a900_h600_amcatnlo",
        # "azh_htt_zll_a900_h650_amcatnlo",
        # "azh_htt_zll_a900_h700_amcatnlo",
        # "azh_htt_zll_a900_h750_amcatnlo",
        # "azh_htt_zll_a900_h800_amcatnlo",
        # "azh_htt_zll_a950_h330_amcatnlo",
        # "azh_htt_zll_a950_h350_amcatnlo",
        # "azh_htt_zll_a950_h400_amcatnlo",
        # "azh_htt_zll_a950_h450_amcatnlo",
        # "azh_htt_zll_a950_h500_amcatnlo",
        # "azh_htt_zll_a950_h550_amcatnlo",
        # "azh_htt_zll_a950_h600_amcatnlo",
        # "azh_htt_zll_a950_h650_amcatnlo",
        # "azh_htt_zll_a950_h700_amcatnlo",
        # "azh_htt_zll_a950_h750_amcatnlo",
        # "azh_htt_zll_a950_h800_amcatnlo",
        # "azh_htt_zll_a950_h850_amcatnlo",
    ]

    for dataset_name in dataset_names:
        dataset = cfg.add_dataset(campaign.get_dataset(dataset_name))
        if limit_dataset_files:
            # apply optional limit on the max. number of files per dataset
            for info in dataset.info.values():
                if info.n_files > limit_dataset_files:
                    info.n_files = limit_dataset_files
        if dataset.name.startswith("tt"):
            dataset.add_tag({"is_ttbar"})

        # add aux info to datasets
        # if dataset.name.startswith("qcd"):
        #     dataset.x.is_qcd = True

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
                "lumi_13TeV_2022": 0.01j,
                "lumi_13TeV_correlated": 0.006j,
            })
        elif campaign.x.EE == "post":
            cfg.x.luminosity = Number(26337, {
                "lumi_13TeV_2022": 0.01j,
                "lumi_13TeV_correlated": 0.006j,
            })
    else:
        raise NotImplementedError(f"Luminosity for year {year} is not defined.")

    # MET filters
    # TODO: Different Met filters for different years
    # https://twiki.cern.ch/twiki/bin/view/CMS/MissingETOptionalFiltersRun2?rev=158#2018_2017_data_and_MC_UL
    cfg.x.met_filters = {
        "Flag.goodVertices",
        "Flag.globalSuperTightHalo2016Filter",
        "Flag.HBHENoiseFilter",
        "Flag.HBHENoiseIsoFilter",
        "Flag.EcalDeadCellTriggerPrimitiveFilter",
        "Flag.BadPFMuonFilter",
        "Flag.BadPFMuonDzFilter",
        "Flag.eeBadScFilter",
        "Flag.ecalBadCalibFilter",
    }

    # minimum bias cross section in mb (milli) for creating PU weights, values from
    # https://twiki.cern.ch/twiki/bin/view/CMS/PileupJSONFileforData?rev=45#Recommended_cross_section
    cfg.x.minbias_xs = Number(69.2, 0.046j)

    # whether to validate the number of obtained LFNs in GetDatasetLFNs
    cfg.x.validate_dataset_lfns = limit_dataset_files is None

    # jec configuration
    # https://twiki.cern.ch/twiki/bin/view/CMS/JECDataMC?rev=201
    jerc_postfix = ""
    if year == 2022 and campaign.x.EE == "post":
        jerc_postfix = "EE"

    jerc_campaign = f"Summer{year2}{jerc_postfix}_22Sep2023"
    jet_type = "AK4PFPuppi"

    print(jerc_campaign)
    cfg.x.jec = DotDict.wrap({
        "campaign": jerc_campaign,
        "version": {2016: "V7", 2017: "V5", 2018: "V5", 2022: "V2"}[year],
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
        "campaign": jerc_campaign,
        "version": {2022: "JRV1"}[year],
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
    btag_key = f"2022{campaign.x.EE}EE" if year == 2022 else year
    cfg.x.btag_working_points = DotDict.wrap({
        "deepjet": {
            "loose": {
                "2022preEE": 0.0583, "2022postEE": 0.0614,
            }[btag_key],
            "medium": {
                "2022preEE": 0.3086, "2022postEE": 0.3196,
            }[btag_key],
            "tight": {
                "2022preEE": 0.7183, "2022postEE": 0.7300,
            }[btag_key],
        },
        "deepcsv": {
            "loose": {
                "2022preEE": 0.1208, "2022postEE": 0.1208,
            }[btag_key],
            "medium": {
                "2022preEE": 0.4168, "2022postEE": 0.4168,
            }[btag_key],
            "tight": {
                "2022preEE": 0.7665, "2022postEE": 0.7665,
            }[btag_key],
        },
    })

    # TODO: check e/mu/btag corrections and implement
    # btag weight configuration
    from columnflow.production.cms.btag import SplitBTagSFConfig
    cfg.x.btag_sf = SplitBTagSFConfig(
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
    elif f"{year}{corr_postfix}" == "2022preEE":
        cfg.x.electron_sf_names = ("Electron-ID-SF", "2022Re-recoBCD", "RecoAbove75")
        cfg.x.electron_sf_mid_names = ("Electron-ID-SF", "2022Re-recoE+PromptFG", "Reco20to75")
        cfg.x.electron_sf_id_names = ("Electron-ID-SF", "2022Re-recoBCD", "wp80iso")
    # names of muon correction sets and working points
    # (used in the muon producer)
    # cfg.x.muon_sf_names = ("NUM_TightRelTkIso_DEN_HighPtID", f"{year}{corr_postfix}_UL")
    cfg.x.muon_sf_id_names = ("NUM_HighPtID_DEN_TrackerMuons", f"{year}{corr_postfix}")
    cfg.x.muon_sf_iso_names = ("NUM_TightRelTkIso_DEN_HighPtID", f"{year}{corr_postfix}")

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
    json_mirror = "/afs/cern.ch/user/j/jmatthie/public/mirrors/jsonpog-integration-49ddc547"
    local_repo = "/nfs/dust/cms/user/matthiej/topsf"  # TODO: avoid hardcoding path

    corr_tag = f"{year}_Summer22{jerc_postfix}"

    cfg.x.external_files = DotDict.wrap({
        # pileup weight corrections
        "pu_sf": (f"{json_mirror}/POG/LUM/{corr_tag}/puWeights.json.gz", "v1"),

        # jet energy correction
        "jet_jerc": (f"{json_mirror}/POG/JME/{corr_tag}/jet_jerc.json.gz", "v1"),

        # electron scale factors
        "electron_sf": (f"{json_mirror}/POG/EGM/{corr_tag}/electron.json.gz", "v1"),

        # muon scale factors
        "muon_sf": (f"{json_mirror}/POG/MUO/{corr_tag}/muon_Z.json.gz", "v1"),

        # btag scale factor
        "btag_sf_corr": (f"{json_mirror}/POG/BTV/{corr_tag}/btagging.json.gz", "v1"),

        # V+jets reweighting
        "vjets_reweighting": f"{local_repo}/data/json/vjets_reweighting.json.gz",
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
                # "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCD/pileup_JSON.txt", "v1"),  # noqa
                "json": (f"https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions22/PileUp/BCDEFG/pileup_JSON.txt", "v1"),  # noqa
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
    else:
        raise NotImplementedError(f"No lumi and pu files provided for year {year}")
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
            "GenPart.*",
        } | set(  # Jets
            f"{jet_obj}.{field}"
            for jet_obj in ["Jet"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "genJetIdx", "btagDeepFlavB", "hadronFlavour", "rawFactor"]
        ) | set(  # BJets
            f"{jet_obj}.{field}"
            for jet_obj in ["BJet"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "btagDeepFlavB", "hadronFlavour"]
        ) | set(  # Muons
            f"{mu_obj}.{field}"
            for mu_obj in ["Muon"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "pdgId"]
        ) | set(  # Electrons
            f"{e_obj}.{field}"
            for e_obj in ["Electron"]
            # NOTE: if we run into storage troubles, skip Bjet and Lightjet
            for field in ["pt", "eta", "phi", "mass", "pdgId", "deltaEtaSC"]
        ) | set(  # MET
            f"MET.{field}"
            for field in ["pt", "phi"]
        ) | set(  # MET
            f"GenMET.{field}"
            for field in ["pt", "phi"]
        ) | set(  # GenJets
            f"{gen_jet_obj}.{field}"
            for gen_jet_obj in ["GenJet"]
            for field in ["pt", "eta", "phi", "mass"]
        )
    )

    # event weight columns as keys in an ordered dict, mapped to shift instances they depend on
    # get_shifts = lambda *keys: sum(([cfg.get_shift(f"{k}_up"), cfg.get_shift(f"{k}_down")] for k in keys), [])
    # get_shifts = functools.partial(get_shifts_from_sources, cfg)
    cfg.x.event_weights = DotDict({
        "normalization_weight": [],
        "electron_weight": [],
        "electron_mid_weight": [],
        "electron_id_weight": [],
        # "muon_weight": [],
        "muon_id_weight": [],
        "muon_iso_weight": [],
        "pu_weight": [],
        "btag_weight": [],
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
    # prod_version = "prod1"

    # def reduce_version(cls, inst, params):
    #     version = dev_version
    #     if params.get("selector") == "default":
    #         version = prod_version

    #     return version

    # Version of required tasks
    cfg.x.versions = {
        "cf.CalibrateEvents": "v0",
        # "cf.SelectEvents": reduce_version,
        # "cf.MergeSelectionStats": reduce_version,
        # "cf.MergeSelectionMasks": reduce_version,
        # "cf.ReduceEvents": reduce_version,
        # "cf.MergeReductionStats": reduce_version,
        # "cf.MergeReducedEvents": reduce_version,
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

    add_variables(cfg)
    add_categories_selection(cfg)
    # add_cutflow_variables(cfg)
    if year == 2022:
        from azh.config.triggers import add_triggers_2022
        add_triggers_2022(cfg)


    # only produce cutflow features when number of dataset_files is limited (used in selection module)
    cfg.x.do_cutflow_features = bool(limit_dataset_files) and limit_dataset_files <= 10
    return cfg
