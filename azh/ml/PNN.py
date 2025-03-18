# coding: utf-8

"""
Test model definition.
"""

from __future__ import annotations

import law
import order as od
import pickle
import re

from columnflow.types import Any
from columnflow.ml import MLModel
from columnflow.util import maybe_import, dev_sandbox
from columnflow.columnar_util import Route, set_ak_column, remove_ak_column

ak = maybe_import("awkward")
tf = maybe_import("tensorflow")
np = maybe_import("numpy")
keras = maybe_import("tensorflow.keras")

law.contrib.load("tensorflow")
logger = law.logger.get_logger(__name__)

class PNNModel(MLModel):

    # mark the model as accepting only a single config
    single_config = True
    input_features_namespace = "MLInput"


    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # prepend namespace to input features
        self.input_columns = {
            f"{self.input_features_namespace}.{name}"
            for name in self.input_features
        }

    # -- methods related to task setup & environment

    def setup(self):
        # dynamically add variables for the quantities produced by this model
        if f"{self.cls_name}.output" not in self.config_inst.variables:
            self.config_inst.add_variable(
                name=f"{self.cls_name}.output",
                null_value=-1,
                binning=(20, -1.0, 1.0),
                x_title=f"{self.cls_name} PNN output",
            )

    def sandbox(self, task: law.Task) -> str:
        return dev_sandbox("bash::$AZH_BASE/sandboxes/venv_ml.sh")

    def datasets(self, config_inst: od.Config) -> set[od.Dataset]:
        return {
            config_inst.get_dataset("dy_m50toinf_4j_madgraph"),
            config_inst.get_dataset("dy_m50toinf_3j_madgraph"),
            config_inst.get_dataset("dy_m50toinf_2j_madgraph"),
            config_inst.get_dataset("dy_m50toinf_1j_madgraph"),
            config_inst.get_dataset("tt_sl_powheg"),
            config_inst.get_dataset("tt_dl_powheg"),
            config_inst.get_dataset("tt_fh_powheg"),
            # config_inst.get_dataset("st_tchannel_tbar_4f_powheg"),
            # config_inst.get_dataset("st_tchannel_t_4f_powheg"),
            # config_inst.get_dataset("st_twchannel_tbar_dl_powheg"),
            # "st_twchannel_tbar_fh_powheg",
            # config_inst.get_dataset("st_twchannel_tbar_sl_powheg"),
            # config_inst.get_dataset("st_twchannel_t_dl_powheg"),
            # "st_twchannel_t_fh_powheg",
            # config_inst.get_dataset("st_twchannel_t_sl_powheg"),
            # config_inst.get_dataset("zz_pythia"),
            # config_inst.get_dataset("wz_pythia"),
            # config_inst.get_dataset("ww_pythia"),
            config_inst.get_dataset("ttz_zll_m4to50_amcatnlo"),
            config_inst.get_dataset("ttz_zll_m50toinf_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h850_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1000_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h850_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1050_h950_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h850_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1100_h950_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h1050_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h850_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1150_h950_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h850_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1200_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1300_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1400_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1500_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h1500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1600_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h1600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1700_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h1700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1800_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h1800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a1900_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h1900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2000_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1100_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1200_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1300_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h1900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h2000_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a2100_h900_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a430_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a450_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a450_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a500_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a500_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a500_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a550_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a550_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a550_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a550_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a600_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a600_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a600_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a600_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a600_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a650_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h350_amcatnlo"),
            # config_inst.get_dataset("azh_htt_zll_a700_h370_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a700_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a750_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a800_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a850_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a900_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h330_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h350_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h400_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h450_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h500_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h550_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h600_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h650_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h700_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h750_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h800_amcatnlo"),
            config_inst.get_dataset("azh_htt_zll_a950_h850_amcatnlo"),
        }

    def uses(self, config_inst: od.Config) -> set[Route | str]:
        # print("Using Input Columns:")
        # print({"normalization_weight","category_ids",} | self.input_columns)
        return {"normalization_weight","category_ids",} | self.input_columns

    def produces(self, config_inst: od.Config) -> set[Route | str]:
        return {
            f"{self.cls_name}.output",
        }

    def output(self, task: law.Task) -> law.FileSystemDirectoryTarget:
        return task.target(f"mlmodel_f{task.branch}of{self.folds}", dir=True)

    def open_model(self, target: law.FileSystemDirectoryTarget) -> tf.keras.models.Model:
        return target.load(formatter="tf_keras_model")


    def prepare_inputs(
        self,
        task,
        input,
    ) -> tuple[dict[str, np.array]]:

        # obtain processes from config
        process_insts = [
            self.config_inst.get_process(proc)
            for proc in self.processes
        ]

        proc_n_events = np.array(len(self.processes) * [0])
        proc_custom_weights = np.array(len(self.processes) * [0])
        proc_sum_weights = np.array(len(self.processes) * [0])
        n_sig_events = 0
        n_back_events = 0
        sum_sig_weight = 0
        sum_back_weight = 0
        proc_idx = {}  # bookkeeping which process each dataset belongs to
        mass_params_a = []
        mass_params_h = []

        #
        # determine process of each dataset and count number of events & sum of eventweights for this process
        #

        for dataset, files in input["events"][self.config_inst.name].items():
            dataset_inst = self.config_inst.get_dataset(dataset)
            # print(dataset)
            print("New Dataset:")
            # print(files)
            # print(dataset_inst)
            # print(self.config_inst.get_dataset(dataset).has_tag("is_signal"))
            pattern = r"zll_a(\d+)_h(\d+)"
            if self.config_inst.get_dataset(dataset).has_tag("is_signal"):
                match = re.search(pattern, str(dataset))
                if match:
                    mass_params_a.append(int(match.group(1)))
                    mass_params_h.append(int(match.group(2)))
            # print(mass_params_a)
            # print(mass_params_h)


            # check dataset only belongs to one process
            if len(dataset_inst.processes) != 1:
                raise Exception("only 1 process inst is expected for each dataset")

            # TODO: use stats here instead
            # mlevents = [
            #     ak.from_parquet(inp["mlevents"].fn)
            #     for inp in files
            # ]
            mlevents= ak.Array([])
            #slimming to signal catgory
            for inp in files:
                # print(inp)
                events = ak.from_parquet(inp["mlevents"].path)
                # print("Before slimming:", len(events))
                lens = np.array([len(x) for x in events.category_ids])
                events = events[lens>1]
                # from IPython import embed; embed()
                signal_cats ={12110,12120,22110,22120,13110,13120,23110,23120} 
                # signal = np.bitwise_and(inputs.category_ids[:,1]%10000>1900, inputs.category_ids[:,1]%1000<200)
                # signal = np.bitwise_or(events.category_ids[:,1]==12110, events.category_ids[:,1]==12120,)
                is_signal = np.isin(events.category_ids[:,1],list(signal_cats))
                events = events[is_signal]
                # from IPython import embed; embed()
                # print("After slimming:", len(events))
                if len(mlevents)==0:
                    mlevents = [events]
                else:
                    mlevents = ak.concatenate(mlevents2,events)
            # from IPython import embed; embed()
            n_events = sum(
                len(events)
                for events in mlevents
            )
            sum_weights = sum(
                ak.sum(events.normalization_weight)
                for events in mlevents
            )

            #
            if self.config_inst.get_dataset(dataset).has_tag("is_signal"):
                n_sig_events += n_events
                sum_sig_weight += sum_weights
            else:
                n_back_events += n_events
                sum_back_weight += sum_weights

            for i, proc in enumerate(process_insts):
                # print("LEAF")
                # print(proc)
                proc_custom_weights[i] = self.proc_custom_weights[proc.name]
                leaf_procs = [
                    p for p, _, _ in self.config_inst.get_process(proc).walk_processes(include_self=True)
                ]
                # print(leaf_procs)
                # print(dataset_inst.processes.get_first())
                if dataset_inst.processes.get_first() in leaf_procs:
                # if True:
                    logger.info(f"the dataset *{dataset}* is used for training the *{proc.name}* output node")
                    proc_idx[dataset] = i
                    proc_n_events[i] += n_events
                    proc_sum_weights[i] += sum_weights
                    continue
            # print("Leaving LEAF")

        # fail if no process was found for dataset
            if proc_idx.get(dataset) is None:
                raise Exception(f"dataset {dataset} is not matched to any of the given processes")


        DNN_inputs = {
            "weights": None,
            "inputs": None,
            "target": None,
        }

        # scaler for weights such that the largest are of order 1
        # weights_scaler = min(proc_n_events / proc_custom_weights)
        weights_scaler = min([sum_back_weight,sum_sig_weight])

        sum_nnweights_processes = {}
        for dataset, files in input["events"][self.config_inst.name].items():
            # print(dataset)
            # print(proc_idx)
            this_proc_idx = proc_idx[dataset]
            # print(this_proc_idx)

            this_proc_name = self.processes[this_proc_idx]
            this_proc_n_events = proc_n_events[this_proc_idx]
            this_proc_sum_weights = proc_sum_weights[this_proc_idx]

            logger.info(
                f"dataset: {dataset}, \n"
                f"  #Events: {this_proc_n_events}, \n"
                f"  Sum Eventweights: {this_proc_sum_weights}",
            )
            sum_nnweights = 0

            for inp in files:
                events = ak.from_parquet(inp["mlevents"].path)
                # padded_cats = np.array([np.pad(arr,(0,max(2-len(arr),0)),constant_values=None) for arr in events.category_ids],dtype=object)
                lens = np.array([len(x) for x in events.category_ids])
                events = events[lens>1]
                signal_cats ={12110,12120,22110,22120,13110,13120,23110,23120} 
                # signal = np.bitwise_or(events.category_ids[:,1]==12110, events.category_ids[:,1]==12120,)
                # signal = np.bitwise_and(inputs.category_ids[:,1]%10000>1900, inputs.category_ids[:,1]%1000<200)
                is_signal = np.isin(events.category_ids[:,1],list(signal_cats))
                events = events[is_signal]
                weights = events.normalization_weight
                if self.eqweight:
                        # weights = weights * weights_scaler / this_proc_sum_weights
                        # custom_procweight = self.proc_custom_weights[this_proc_name]
                        # weights = weights * custom_procweight
                    if self.config_inst.get_dataset(dataset).has_tag("is_signal"):
                        weights = weights * weights_scaler / sum_sig_weight
                        custom_procweight = self.proc_custom_weights[this_proc_name]
                        weights = weights * custom_procweight
                    else:
                        weights = weights * weights_scaler / sum_back_weight
                        custom_procweight = self.proc_custom_weights[this_proc_name]
                        weights = weights * custom_procweight
                weights = ak.to_numpy(weights)
                # from IPython import embed; embed()
                if np.any(~np.isfinite(weights)):
                    raise Exception(f"Non-finite values found in weights from dataset {dataset}")

                sum_nnweights += sum(weights)
                sum_nnweights_processes.setdefault(this_proc_name, 0)
                sum_nnweights_processes[this_proc_name] += sum(weights)

                # remove columns not used in training
                input_features = events[self.input_features_namespace]
                for var in input_features.fields:
                    # print(var)
                    if var not in self.input_features:
                        events = remove_ak_column(events, f"{self.input_features_namespace}.{var}")
                h_mass_param = np.ones((len(events), 1))
                a_mass_param = np.ones((len(events), 1))
                # print(self.config_inst.get_dataset(dataset).has_tag("is_signal"))
                events = events[self.input_features_namespace]
                mass_params_h = np.array(mass_params_h)
                mass_params_a = np.array(mass_params_a)
                if self.config_inst.get_dataset(dataset).has_tag("is_signal"):
                    pattern = r"zll_a(\d+)_h(\d+)"
                    # print(re.search(pattern, str(dataset)))
                    match = re.search(pattern, str(dataset))
                    if match:
                        a_mass_param = np.full(len(events),int(match.group(1)))
                        h_mass_param = np.full(len(events),int(match.group(2)))
                else:
                    param_len=len(mass_params_a)
                    idx_array = np.arange(param_len)
                    random_idx = np.random.choice(idx_array,len(events))
                    a_mass_param = mass_params_a[random_idx]
                    h_mass_param = mass_params_h[random_idx]
                # from IPython import embed; embed()
                events = set_ak_column(events,"a_mass_param",a_mass_param)
                events = set_ak_column(events,"h_mass_param",h_mass_param)
                # transform events into numpy ndarray
                # TODO: at this point we should save the order of our input variables
                #       to ensure that they will be loaded in the correct order when
                #       doing the evaluation
                # from IPython import embed; embed()
                events = ak.to_numpy(events)
                events = events.astype(
                    [(name, np.float32) for name in events.dtype.names],
                    copy=False,
                ).view(np.float32).reshape((-1, len(events.dtype)))

                if np.any(~np.isfinite(events)): 
                    raise Exception(f"Non-finite values found in inputs from dataset {dataset}")

                # create the truth values for the output layer
                # target = np.zeros((len(events), len(self.processes)))
                # target[:, this_proc_idx] = 1
                # print("Setting target")
                # print(dataset)
                # print(self.config_inst.get_dataset(dataset))
                # print(self.config_inst.get_dataset(dataset).has_tag("is_ttbar"))
                # print(self.config_inst.get_dataset(dataset).has_tag("is_signal"))
                target = np.ones((len(events), 1)) if self.config_inst.get_dataset(dataset).has_tag("is_signal") else np.zeros((len(events), 1))
                # target = np.ones((len(events), 1))

                if np.any(~np.isfinite(target)):
                    raise Exception(f"Non-finite values found in target from dataset {dataset}")
                # print("Concatenate!")
                # # print(DNN_inputs)
                # print("DNN",DNN_inputs["inputs"])
                # if DNN_inputs["inputs"] is not None:
                #     print("DNN len",len(DNN_inputs["inputs"]))
                #     print("DNN shape",ak.num(DNN_inputs["inputs"],axis=0))
                #     print("DNN shape",ak.num(DNN_inputs["inputs"],axis=1))
                # print("events",events)
                # print("len events",len(events))
                # print("events shape",ak.num(events,axis=0))
                # print("events shape",ak.num(events,axis=1))
                if DNN_inputs["weights"] is None:
                    DNN_inputs["weights"] = weights
                    DNN_inputs["inputs"] = events
                    DNN_inputs["target"] = target
                else:
                    DNN_inputs["weights"] = np.concatenate([DNN_inputs["weights"], weights])
                    DNN_inputs["inputs"] = np.concatenate([DNN_inputs["inputs"], events])
                    DNN_inputs["target"] = np.concatenate([DNN_inputs["target"], target])
                # from IPython import embed; embed()
        #
        # shuffle events and split into train and validation part
        #
        # from IPython import embed; embed()
        inputs_size = sum([arr.size * arr.itemsize for arr in DNN_inputs.values()])
        logger.info(f"inputs size is {inputs_size / 1024**3} GB")
        # from IPython import embed; embed()
        shuffle_indices = np.array(range(len(DNN_inputs["weights"])))
        np.random.shuffle(shuffle_indices)

        n_validation_events = int(self.validation_fraction * len(DNN_inputs["weights"]))

        train, validation = {}, {}
        for k in DNN_inputs.keys():
            DNN_inputs[k] = DNN_inputs[k][shuffle_indices]

            validation[k] = DNN_inputs[k][:n_validation_events]
            train[k] = DNN_inputs[k][n_validation_events:]
        # from IPython import embed; embed()
        return train, validation

    def train(
        self,
        task: law.Task,
        input: dict[str, list[dict[str, law.FileSystemFileTarget]]],
        output: law.FileSystemDirectoryTarget,
    ) -> None:
        # define a dummy NN

            # run on GPU
        gpus = tf.config.list_physical_devices("GPU")

        # restrict to run only on first GPU
        # https://www.tensorflow.org/guide/gpu#limiting_gpu_memory_growth
        try:
            tf.config.experimental.set_memory_growth(gpus[0], True)
        except RuntimeError as e:
            # GPU already initialized -> print warning and continue
            print(e)
        except IndexError:
            print("No GPUs found. Will use CPU.")

        #
        # prepare input
        #

        # TODO: implement
        print("IN THE TRAINING!")
        print(task)
        print(input)
        print("Output from prepare inputs:")
        print(self.prepare_inputs(task, input))
        train, validation = self.prepare_inputs(task, input)

        # check for non-finite values (inf, nan)
        for key in train.keys():
            if np.any(~np.isfinite(train[key])):
                raise Exception(f"Non-finite values found in training {key}")
            if np.any(~np.isfinite(validation[key])):
                raise Exception(f"Non-finite values found in validation {key}")

        #
        # prepare model
        #

        # TODO: implement
        n_inputs = len(self.input_features)
        # from IPython import embed; embed()
        # n_outputs = len(self.processes)
        n_outputs = 1

        # start model definition
        model = keras.Sequential()

        # define input normalization
        model.add(keras.layers.BatchNormalization(input_shape=(n_inputs,)))

        # hidden layers
        for n_nodes in self.layers:
            model.add(keras.layers.Dense(
                units=n_nodes,
                activation="ReLU",
            ))

            # optional dropout after each hidden layer
            if self.dropout:
                model.add(keras.layers.Dropout(self.dropout))

        # output layer
        model.add(keras.layers.Dense(
            n_outputs,
            activation="sigmoid",
        ))

        # optimizer
        # settings from https://github.com/jabuschh/ZprimeClassifier/blob/8c3a8eee/Training.py#L93  # noqa
        optimizer = keras.optimizers.Adam(
            learning_rate=self.learning_rate,
            beta_1=0.9, beta_2=0.999,
            epsilon=1e-6,
            amsgrad=False,
        )

        # compile model
        model.compile(
            loss="binary_crossentropy",
            optimizer=optimizer,
            # metrics = ["accuracy"],
            weighted_metrics=["binary_accuracy","accuracy"],
        )

        #
        # training
        #

        # early stopping criteria
        early_stopping = keras.callbacks.EarlyStopping(
            # stop when validation loss no longer improves
            monitor="val_loss",
            mode="min",
            # minimum change to consider as improvement
            min_delta=0.005,
            # wait this many epochs w/o improvement before stopping
            patience=max(1, int(self.epochs / 4)),  # 100
            # start monitoring from the beginning
            start_from_epoch=0,
            verbose=0,
            restore_best_weights=True,
        )

        # learning rate reduction on plateau
        lr_reducer = keras.callbacks.ReduceLROnPlateau(
            # reduce LR when validation loss stops improving
            monitor="val_loss",
            mode="min",
            # minimum change to consider as improvement
            min_delta=0.001,
            # factor by which the learning rate will be reduced
            factor=0.5,
            # wait this many epochs w/o improvement before reducing LR
            patience=max(1, int(self.epochs / 8)),  # 100
        )

        # construct TF datasets
        with tf.device("CPU"):
            # training
            tf_train = tf.data.Dataset.from_tensor_slices(
                (train["inputs"], train["target"], train["weights"]),
            ).batch(self.batchsize)

            # validation
            tf_validate = tf.data.Dataset.from_tensor_slices(
                (validation["inputs"], validation["target"], validation["weights"]),
            ).batch(self.batchsize)

        # do training
        model.fit(
            tf_train,
            validation_data=tf_validate,
            epochs=self.epochs,
            callbacks=[early_stopping, lr_reducer],
            verbose=2,
        )

        # save trained model and history
        output.parent.touch()
        model.save(output.path)
        with open(f"{output.path}/model_history.pkl", "wb") as f:
            pickle.dump(model.history.history, f)


        # x = tf.keras.Input(shape=(2,))
        # a1 = tf.keras.layers.Dense(10, activation="elu")(x)
        # y = tf.keras.layers.Dense(2, activation="softmax")(a1)
        # model = tf.keras.Model(inputs=x, outputs=y)

        # # the output is just a single directory target
        # output.dump(model, formatter="tf_keras_model")

    def evaluate(
        self,
        task: law.Task,
        events: ak.Array,
        models: list[Any],
        fold_indices: ak.Array,
        events_used_in_training: bool = False,
    ) -> ak.Array:

        ### TODO
        # Implement way to extract m_H_param and m_A_param from dataset

        a_param = 950
        h_param = 850
        # print(events)
        # print(f"{self.cls_name}.output")
        # from IPython import embed; embed()
        # models, history = zip(*models)
        inputs = ak.copy(events)

        # lens = np.array([len(x) for x in inputs.category_ids])
        # inputs = inputs[lens>1]
        # signal = np.bitwise_and(inputs.category_ids[:,1]%10000>1900, inputs.category_ids[:,1]%1000<200)
        # inputs = inputs[signal]
        # mass_params_a = []
        # mass_params_h = []
        # for proc in self.processes:
        #     pattern = r"zll_a(\d+)_h(\d+)"
        #     match = re.search(pattern, str(proc))
        #     if match:
        #         mass_params_a.append(int(match.group(1)))
        #         mass_params_h.append(int(match.group(2)))

        # h_mass_param = np.ones((len(events), 1))
        # a_mass_param = np.ones((len(events), 1))
        # mass_params_h = np.array(mass_params_h)
        # mass_params_a = np.array(mass_params_a)
        # match = re.search(pattern, str(task))
        # if match:
        #     a_mass_param = np.full(len(events),int(match.group(1)))
        #     h_mass_param = np.full(len(events),int(match.group(2)))
        # else:
        #     param_len=len(mass_params_a)
        #     idx_array = np.arange(param_len)
        #     random_idx = np.random.choice(idx_array,len(events))
        #     a_mass_param = mass_params_a[random_idx]
        #     h_mass_param = mass_params_h[random_idx]
        a_mass_param = np.full(len(events),a_param)
        h_mass_param = np.full(len(events),h_param)
        # from IPython import embed; embed()
        input_features = inputs[self.input_features_namespace]
        for var in input_features.fields:
            if var not in self.input_features:
                inputs = remove_ak_column(inputs, f"{self.input_features_namespace}.{var}")
        inputs = inputs[self.input_features_namespace]
        # from IPython import embed; embed()
        inputs = set_ak_column(inputs,"a_mass_param",a_mass_param)
        inputs = set_ak_column(inputs,"h_mass_param",h_mass_param)
        # from IPython import embed; embed()
        inputs = ak.to_numpy(inputs)
        inputs = inputs.astype(
            [(name, np.float32) for name in inputs.dtype.names],
            copy=False,
        ).view(np.float32).reshape((-1, len(inputs.dtype)))
        # from IPython import embed; embed()
        predictions = []
        for i, model in enumerate(models):
            prediction = ak.from_numpy(model.predict_on_batch(inputs))
            predictions.append(prediction)
        outputs = ak.ones_like(predictions[0]) * -1
        # from IPython import embed; embed()
        for i in range(self.folds):
            # reshape mask from N*bool to N*k*bool (TODO: simpler way?)
            idx = ak.to_regular(
                ak.concatenate(
                    [
                        ak.singletons(fold_indices == i),
                    ] ,
                    axis=1,
                ),
            )
            outputs = ak.where(idx, predictions[i], outputs)
        # from IPython import embed; embed()
        # for i in range(100):
        #     print(outputs[i])
        events = set_ak_column(events, f"{self.cls_name}.output", outputs)
        return events


# usable derivations
PNN = PNNModel.derive("PNN", cls_dict={
    "batchsize": 500,
    "dropout": 0.5,
    "epochs": 500,
    "folds": 2,
    "eqweight": True,
    "validation_fraction": 0.25,
    "layers": [512, 512],
    "learning_rate": 0.0005,


    "processes": [
        "tt",
        # "st",
        "dy",
        "ttv",
        # "vv",
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
        "azh_htt_zll_a1400_h1200",
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
        "azh_htt_zll_a1700_h900",
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
       
    ],

    "proc_custom_weights": {
        "tt": 1,
        # "st": 1,
        "dy": 1,
        "ttv":1,
        "vv":1,
        "azh_htt_zll_a1000_h330":1,
        "azh_htt_zll_a1600_h1500":1,
        "azh_htt_zll_a430_h330":1,
        "azh_htt_zll_a2100_h1300":1,
        "azh_htt_zll_a1000_h600":1,
        "azh_htt_zll_a500_h350":1,
        "azh_htt_zll_a1000_h350":1,
        "azh_htt_zll_a1000_h400":1,
        "azh_htt_zll_a1000_h450":1,
        "azh_htt_zll_a1000_h500":1,
        "azh_htt_zll_a1000_h550":1,
        "azh_htt_zll_a1000_h650":1,
        "azh_htt_zll_a1000_h700":1,
        "azh_htt_zll_a1000_h750":1,
        "azh_htt_zll_a1000_h800":1,
        "azh_htt_zll_a1000_h850":1,
        "azh_htt_zll_a1000_h900":1,
        "azh_htt_zll_a1050_h330":1,
        "azh_htt_zll_a1050_h350":1,
        "azh_htt_zll_a1050_h400":1,
        "azh_htt_zll_a1050_h450":1,
        "azh_htt_zll_a1050_h500":1,
        "azh_htt_zll_a1050_h550":1,
        "azh_htt_zll_a1050_h600":1,
        "azh_htt_zll_a1050_h700":1,
        "azh_htt_zll_a1050_h750":1,
        "azh_htt_zll_a1050_h800":1,
        "azh_htt_zll_a1050_h850":1,
        "azh_htt_zll_a1050_h900":1,
        "azh_htt_zll_a1050_h950":1,
        "azh_htt_zll_a1100_h1000":1,
        "azh_htt_zll_a1100_h330":1,
        "azh_htt_zll_a1100_h350":1,
        "azh_htt_zll_a1100_h400":1,
        "azh_htt_zll_a1100_h450":1,
        "azh_htt_zll_a1100_h500":1,
        "azh_htt_zll_a1100_h550":1,
        "azh_htt_zll_a1100_h600":1,
        "azh_htt_zll_a1100_h650":1,
        "azh_htt_zll_a1100_h700":1,
        "azh_htt_zll_a1100_h750":1,
        "azh_htt_zll_a1100_h800":1,
        "azh_htt_zll_a1100_h850":1,
        "azh_htt_zll_a1100_h900":1,
        "azh_htt_zll_a1100_h950":1,
        "azh_htt_zll_a1150_h1050":1,
        "azh_htt_zll_a1150_h330":1,
        "azh_htt_zll_a1150_h350":1,
        "azh_htt_zll_a1150_h450":1,
        "azh_htt_zll_a1150_h550":1,
        "azh_htt_zll_a1150_h650":1,
        "azh_htt_zll_a1150_h750":1,
        "azh_htt_zll_a1150_h850":1,
        "azh_htt_zll_a1150_h950":1,
        "azh_htt_zll_a1200_h1000":1,
        "azh_htt_zll_a1200_h1100":1,
        "azh_htt_zll_a1200_h330":1,
        "azh_htt_zll_a1200_h350":1,
        "azh_htt_zll_a1200_h400":1,
        "azh_htt_zll_a1200_h500":1,
        "azh_htt_zll_a1200_h600":1,
        "azh_htt_zll_a1200_h700":1,
        "azh_htt_zll_a1200_h800":1,
        "azh_htt_zll_a1200_h850":1,
        "azh_htt_zll_a1200_h900":1,
        "azh_htt_zll_a1300_h1000":1,
        "azh_htt_zll_a1300_h1100":1,
        "azh_htt_zll_a1300_h1200":1,
        "azh_htt_zll_a1300_h350":1,
        "azh_htt_zll_a1300_h400":1,
        "azh_htt_zll_a1300_h500":1,
        "azh_htt_zll_a1300_h600":1,
        "azh_htt_zll_a1300_h700":1,
        "azh_htt_zll_a1300_h800":1,
        "azh_htt_zll_a1300_h900":1,
        "azh_htt_zll_a1400_h1000":1,
        "azh_htt_zll_a1400_h1100":1,
        "azh_htt_zll_a1400_h1200":1,
        "azh_htt_zll_a1400_h1300":1,
        "azh_htt_zll_a1400_h350":1,
        "azh_htt_zll_a1400_h400":1,
        "azh_htt_zll_a1400_h500":1,
        "azh_htt_zll_a1400_h600":1,
        "azh_htt_zll_a1400_h700":1,
        "azh_htt_zll_a1400_h800":1,
        "azh_htt_zll_a1400_h900":1,
        "azh_htt_zll_a1500_h1000":1,
        "azh_htt_zll_a1500_h1100":1,
        "azh_htt_zll_a1500_h1200":1,
        "azh_htt_zll_a1500_h1300":1,
        "azh_htt_zll_a1500_h1400":1,
        "azh_htt_zll_a1500_h350":1,
        "azh_htt_zll_a1500_h400":1,
        "azh_htt_zll_a1500_h500":1,
        "azh_htt_zll_a1500_h600":1,
        "azh_htt_zll_a1500_h700":1,
        "azh_htt_zll_a1500_h900":1,
        "azh_htt_zll_a1600_h1000":1,
        "azh_htt_zll_a1600_h1100":1,
        "azh_htt_zll_a1600_h1200":1,
        "azh_htt_zll_a1600_h1300":1,
        "azh_htt_zll_a1600_h1400":1,
        "azh_htt_zll_a1600_h350":1,
        "azh_htt_zll_a1600_h400":1,
        "azh_htt_zll_a1600_h500":1,
        "azh_htt_zll_a1600_h600":1,
        "azh_htt_zll_a1600_h900":1,
        "azh_htt_zll_a1700_h1000":1,
        "azh_htt_zll_a1700_h1100":1,
        "azh_htt_zll_a1700_h1200":1,
        "azh_htt_zll_a1700_h1300":1,
        "azh_htt_zll_a1700_h1400":1,
        "azh_htt_zll_a1700_h1500":1,
        "azh_htt_zll_a1700_h1600":1,
        "azh_htt_zll_a1700_h350":1,
        "azh_htt_zll_a1700_h400":1,
        "azh_htt_zll_a1700_h500":1,
        "azh_htt_zll_a1700_h600":1,
        "azh_htt_zll_a1700_h700":1,
        "azh_htt_zll_a1700_h800":1,
        "azh_htt_zll_a1700_h900":1,
        "azh_htt_zll_a1800_h1000":1,
        "azh_htt_zll_a1800_h1100":1,
        "azh_htt_zll_a1800_h1200":1,
        "azh_htt_zll_a1800_h1300":1,
        "azh_htt_zll_a1800_h1400":1,
        "azh_htt_zll_a1800_h1500":1,
        "azh_htt_zll_a1800_h1600":1,
        "azh_htt_zll_a1800_h1700":1,
        "azh_htt_zll_a1800_h350":1,
        "azh_htt_zll_a1800_h400":1,
        "azh_htt_zll_a1800_h500":1,
        "azh_htt_zll_a1800_h600":1,
        "azh_htt_zll_a1800_h700":1,
        "azh_htt_zll_a1800_h800":1,
        "azh_htt_zll_a1800_h900":1,
        "azh_htt_zll_a1900_h1000":1,
        "azh_htt_zll_a1900_h1100":1,
        "azh_htt_zll_a1900_h1200":1,
        "azh_htt_zll_a1900_h1300":1,
        "azh_htt_zll_a1900_h1400":1,
        "azh_htt_zll_a1900_h1500":1,
        "azh_htt_zll_a1900_h1600":1,
        "azh_htt_zll_a1900_h1700":1,
        "azh_htt_zll_a1900_h1800":1,
        "azh_htt_zll_a1900_h350":1,
        "azh_htt_zll_a1900_h400":1,
        "azh_htt_zll_a1900_h500":1,
        "azh_htt_zll_a1900_h600":1,
        "azh_htt_zll_a1900_h700":1,
        "azh_htt_zll_a1900_h800":1,
        "azh_htt_zll_a1900_h900":1,
        "azh_htt_zll_a2000_h1000":1,
        "azh_htt_zll_a2000_h1100":1,
        "azh_htt_zll_a2000_h1200":1,
        "azh_htt_zll_a2000_h1300":1,
        "azh_htt_zll_a2000_h1400":1,
        "azh_htt_zll_a2000_h1600":1,
        "azh_htt_zll_a2000_h1700":1,
        "azh_htt_zll_a2000_h1800":1,
        "azh_htt_zll_a2000_h1900":1,
        "azh_htt_zll_a2000_h350":1,
        "azh_htt_zll_a2000_h400":1,
        "azh_htt_zll_a2000_h500":1,
        "azh_htt_zll_a2000_h600":1,
        "azh_htt_zll_a2000_h700":1,
        "azh_htt_zll_a2000_h800":1,
        "azh_htt_zll_a2000_h900":1,
        "azh_htt_zll_a2100_h1000":1,
        "azh_htt_zll_a2100_h1100":1,
        "azh_htt_zll_a2100_h1200":1,
        "azh_htt_zll_a2100_h1400":1,
        "azh_htt_zll_a2100_h1500":1,
        "azh_htt_zll_a2100_h1700":1,
        "azh_htt_zll_a2100_h1800":1,
        "azh_htt_zll_a2100_h1900":1,
        "azh_htt_zll_a2100_h2000":1,
        "azh_htt_zll_a2100_h350":1,
        "azh_htt_zll_a2100_h400":1,
        "azh_htt_zll_a2100_h500":1,
        "azh_htt_zll_a2100_h600":1,
        "azh_htt_zll_a2100_h700":1,
        "azh_htt_zll_a2100_h800":1,
        "azh_htt_zll_a2100_h900":1,
        "azh_htt_zll_a450_h330":1,
        "azh_htt_zll_a450_h350":1,
        "azh_htt_zll_a500_h330":1,
        # "azh_htt_zll_a500_h370":1,
        "azh_htt_zll_a500_h400":1,
        "azh_htt_zll_a550_h330":1,
        "azh_htt_zll_a550_h350":1,
        "azh_htt_zll_a550_h400":1,
        "azh_htt_zll_a550_h450":1,
        "azh_htt_zll_a600_h330":1,
        "azh_htt_zll_a600_h350":1,
        "azh_htt_zll_a600_h400":1,
        "azh_htt_zll_a600_h450":1,
        "azh_htt_zll_a600_h500":1,
        "azh_htt_zll_a650_h330":1,
        "azh_htt_zll_a650_h350":1,
        "azh_htt_zll_a650_h400":1,
        "azh_htt_zll_a650_h450":1,
        "azh_htt_zll_a650_h500":1,
        "azh_htt_zll_a650_h550":1,
        "azh_htt_zll_a700_h330":1,
        "azh_htt_zll_a700_h350":1,
        # # "azh_htt_zll_a700_h370":1,
        "azh_htt_zll_a700_h400":1,
        "azh_htt_zll_a700_h450":1,
        "azh_htt_zll_a700_h500":1,
        "azh_htt_zll_a700_h550":1,
        "azh_htt_zll_a750_h330":1,
        "azh_htt_zll_a750_h350":1,
        "azh_htt_zll_a750_h400":1,
        "azh_htt_zll_a750_h450":1,
        "azh_htt_zll_a750_h500":1,
        "azh_htt_zll_a750_h550":1,
        "azh_htt_zll_a750_h600":1,
        "azh_htt_zll_a750_h650":1,
        "azh_htt_zll_a800_h330":1,
        "azh_htt_zll_a800_h350":1,
        "azh_htt_zll_a800_h400":1,
        "azh_htt_zll_a800_h450":1,
        "azh_htt_zll_a800_h500":1,
        "azh_htt_zll_a800_h550":1,
        "azh_htt_zll_a800_h600":1,
        "azh_htt_zll_a800_h650":1,
        "azh_htt_zll_a800_h700":1,
        "azh_htt_zll_a850_h330":1,
        "azh_htt_zll_a850_h350":1,
        "azh_htt_zll_a850_h400":1,
        "azh_htt_zll_a850_h450":1,
        "azh_htt_zll_a850_h500":1,
        "azh_htt_zll_a850_h550":1,
        "azh_htt_zll_a850_h600":1,
        "azh_htt_zll_a850_h650":1,
        "azh_htt_zll_a850_h700":1,
        "azh_htt_zll_a850_h750":1,
        "azh_htt_zll_a900_h330":1,
        "azh_htt_zll_a900_h350":1,
        # "azh_htt_zll_a900_h370":1,
        "azh_htt_zll_a900_h400":1,
        "azh_htt_zll_a900_h450":1,
        "azh_htt_zll_a900_h550":1,
        "azh_htt_zll_a900_h500":1,
        "azh_htt_zll_a900_h600":1,
        "azh_htt_zll_a900_h650":1,
        "azh_htt_zll_a900_h700":1,
        "azh_htt_zll_a900_h750":1,
        "azh_htt_zll_a900_h800":1,
        "azh_htt_zll_a950_h330":1,
        "azh_htt_zll_a950_h350":1,
        "azh_htt_zll_a950_h400":1,
        "azh_htt_zll_a950_h450":1,
        "azh_htt_zll_a950_h500":1,
        "azh_htt_zll_a950_h550":1,
        "azh_htt_zll_a950_h600":1,
        "azh_htt_zll_a950_h650":1,
        "azh_htt_zll_a950_h700":1,
        "azh_htt_zll_a950_h750":1,
        "azh_htt_zll_a950_h800":1,
        "azh_htt_zll_a950_h850":1,
    },

    "input_features": [
    ] + [
        f"jet_{var}_{i + 1}"
        for var in ("energy", "pt", "eta", "btag","mass")
        for i in range(4)
    ] 
     + [
        f"Leptons_{var}_{i + 1}"
        for var in ("energy", "pt", "eta", "phi")
        for i in range(2)
    ]
     + [
        "a_mass_param",
        "h_mass_param",
        "pt_z",
        "m_z",
        "m_a",
        "m_h",
        "del_m",
        # "n_bjets",
        # "n_jets",
        "deltaR_b_z",
        "deltaPhi_MET_Jet1",
        "deltaPhi_MET_Jet2",
        "deltaPhi_MET_Jet3",
        "MET_ht"
    ]

    })
