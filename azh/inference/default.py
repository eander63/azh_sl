# coding: utf-8

"""
first version of the hbw inference model.
"""

import itertools
from columnflow.inference import inference_model, ParameterType, ParameterTransformation


def get_process_datasets(config_inst, process):
    """
    Helper function to retrieve all datasets for a process.
    """
    process_insts = [
        p for p, _, _ in config_inst.get_process(process).walk_processes(include_self=True)  # noqa
    ]
    datasets = [
        dataset_inst.name for dataset_inst in config_inst.datasets
        if any(map(dataset_inst.has_process, process_insts))
    ]
    return datasets

@inference_model
def default(self):

    # TODO: smiliar to the DNN

    year = self.config_inst.campaign.x.year  # noqa; not used right now
    ecm = self.config_inst.campaign.ecm

    #
    # categories
    #

    e_categories, mu_categories = [], []

    # NOTE: use ML model inst if possible
    ml_model_name = "PNN"
    ml_model_processes = [
        "azh_htt_zll_a950_h850",
        "tt",
        "ttv",
        "dy",
    ]
    print("appending cats!")
    # from IPython import embed; embed()

    e_categories.append(self.add_category(
        "cat_2e",
        config_category=f"2e",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    ))
    mu_categories.append(self.add_category(
        f"cat_2mu",
        config_category=f"2mu",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    ))

    # e_categories.append(self.add_category(
    #     "cat_2e__SR",
    #     config_category=f"2e__SR",
    #     config_variable=f"{ml_model_name}_output",
    #     mc_stats=True,
    #     config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    # ))
    # mu_categories.append(self.add_category(
    #     f"cat_2mu__SR",
    #     config_category=f"2mu__SR",
    #     config_variable=f"{ml_model_name}_output",
    #     mc_stats=True,
    #     config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    # ))

    e_categories.append(self.add_category(
        "cat_2e_SR_2b_6j",
        config_category=f"2e__SR__2bjets__6jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    ))
    mu_categories.append(self.add_category(
        f"cat_2mu_SR_2b_6j",
        config_category=f"2mu__SR__2bjets__6jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    ))

    e_categories.append(self.add_category(
        "cat_2e_SR_2b_5j",
        config_category=f"2e__SR__2bjets__5jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    ))
    mu_categories.append(self.add_category(
        f"cat_2mu_SR_2b_5j",
        config_category=f"2mu__SR__2bjets__5jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    ))

    e_categories.append(self.add_category(
        "cat_2e_SR_1b_6j",
        config_category=f"2e__SR__1bjets__6jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    ))
    mu_categories.append(self.add_category(
        f"cat_2mu_SR_1b_6j",
        config_category=f"2mu__SR__1bjets__6jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    ))

    e_categories.append(self.add_category(
        "cat_2e_SR_1b_5j",
        config_category=f"2e__SR__1bjets__5jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_egamma_{i}" for i in [ "c", "d"]],
    ))
    mu_categories.append(self.add_category(
        f"cat_2mu_SR_1b_5j",
        config_category=f"2mu__SR__1bjets__5jets",
        config_variable=f"{ml_model_name}_output",
        mc_stats=True,
        config_data_datasets=[f"data_mu_{i}" for i in [ "c", "d"]],
    ))
    #
    # processes
    #
    print("procs!")
    signals_azh = [
        "azh_htt_zll_a950_h850",
    ]

    processes = [
        "azh_htt_zll_a950_h850",
        "tt",
        "ttv",
        "st", 
        "dy",
        # "w_lnu",
        "vv",
        # "vvv",
        # "qcd",
        # "ggZH", "tHq", "tHW", "ggH", "qqH", "ZH", "WH", "VH", "ttH", "bbH",
    ]

    # if process names need to be changed to fit some convention
    inference_procnames = {
        "foo": "bar",
        # "st": "ST",
        # "tt": "TT",
    }
    print("Adding procs")
    # add processes with corresponding datasets to inference model
    for proc in processes:
        if not self.config_inst.has_process(proc):
            raise Exception(f"Process {proc} not included in the config {self.config_inst.name}")
        sub_process_insts = [p for p, _, _ in self.config_inst.get_process(proc).walk_processes(include_self=True)]
        datasets = [
            dataset_inst.name for dataset_inst in self.config_inst.datasets
            if any(map(dataset_inst.has_process, sub_process_insts))
        ]

        self.add_process(
            inference_procnames.get(proc, proc),
            config_process=proc,
            is_signal=("azh_" in proc),
            config_mc_datasets=datasets,
        )

    #
    # parameters
    #

    # groups
    self.add_parameter_group("experiment")
    self.add_parameter_group("theory")
    print("Groups added!")

    # # add QCD scale uncertainties to inference model
    # proc_QCDscale = {
    #     "ttbar": ["tt", "st_tchannel", "st_schannel", "st_twchannel", "ttW", "ttZ"],
    #     "V": ["dy", "w_lnu"],
    #     "VV": ["WW", "ZZ", "WZ", "qqZZ"],
    #     "VVV": ["vvv"],
    #     "ggH": ["ggH"],
    #     "qqH": ["qqH"],
    #     "VH": ["ZH", "WH", "VH"],
    #     "ttH": ["ttH", "tHq", "tHW"],
    #     "bbH": ["bbH"],  # contains also pdf and alpha_s
    #     # "hh_ggf": signals_hh_ggf,  # included in inference model (THU_HH)
    #     "hh_vbf": signals_hh_vbf,
    #     "VHH": [],
    #     "ttHH": [],
    # }

    # TODO: combine scale and mtop uncertainties for specific processes?
    # TODO: some scale/pdf uncertainties should be rounded to 3 digits, others to 4 digits
    # NOTE: it might be easier to just take the recommended uncertainty values from HH conventions at
    #       https://gitlab.cern.ch/hh/naming-conventions instead of taking the values from CMSDB
    # for k, procs in proc_QCDscale.items():
    #     for proc in procs:
    #         if proc not in processes:
    #             continue
    #         process_inst = self.config_inst.get_process(proc)
    #         if "scale" not in process_inst.xsecs[ecm]:
    #             continue
    #         self.add_parameter(
    #             f"QCDscale_{k}",
    #             process=inference_procnames.get(proc, proc),
    #             type=ParameterType.rate_gauss,
    #             effect=tuple(map(
    #                 lambda f: round(f, 3),
    #                 process_inst.xsecs[ecm].get(names=("scale"), direction=("down", "up"), factor=True),
    #             )),
    #         )
    #     self.add_parameter_to_group(f"QCDscale_{k}", "theory")

    # add PDF rate uncertainties to inference model
    # proc_pdf = {
    #     "gg": ["tt", "ttZ", "ggZZ"],
    #     "qqbar": ["st_schannel", "st_tchannel", "dy", "w_lnu", "vvv", "qqZZ", "ttW"],
    #     "qg": ["st_twchannel"],
    #     "Higgs_gg": ["ggH"],
    #     "Higgs_qqbar": ["qqH", "ZH", "WH", "VH"],
    #     # "Higgs_qg": [],  # none so far
    #     "Higgs_ttH": ["ttH", "tHq", "tHW"],
    #     # "Higgs_bbh": ["bbH"],  # removed
    #     "Higgs_hh_ggf": signals_hh_ggf,
    #     "Higgs_hh_vbf": signals_hh_vbf,
    #     "Higgs_VHH": ["HHZ", "HHW+", "HHW-"],
    #     "Higgs_ttHH": ["ttHH"],
    # }

    # for k, procs in proc_pdf.items():
    #     for proc in procs:
    #         if proc not in processes:
    #             continue
    #         process_inst = self.config_inst.get_process(proc)
    #         if "pdf" not in process_inst.xsecs[ecm]:
    #             continue

    #         self.add_parameter(
    #             f"pdf_{k}",
    #             process=inference_procnames.get(proc, proc),
    #             type=ParameterType.rate_gauss,
    #             effect=tuple(map(
    #                 lambda f: round(f, 3),
    #                 process_inst.xsecs[ecm].get(names=("pdf"), direction=("down", "up"), factor=True),
    #             )),
    #         )
    #     self.add_parameter_to_group(f"pdf_{k}", "theory")

    # lumi
    lumi = self.config_inst.x.luminosity
    for unc_name in lumi.uncertainties:
        self.add_parameter(
            unc_name,
            type=ParameterType.rate_gauss,
            effect=lumi.get(names=unc_name, direction=("down", "up"), factor=True),
            transformations=[ParameterTransformation.symmetrize],
        )
    print("lumi added!")
    # minbias xs (TODO: add back when PU weight behaves correctly)
    """
    self.add_parameter(
        f"CMS_pileup_{year}",
        type=ParameterType.shape,
        config_shift_source="minbias_xs",
    )
    self.add_parameter_to_group(f"CMS_pileup_{year}", "experiment")
    """

    # scale + pdf (shape)
    # for proc in processes:
    #     if proc == "qcd":
    #         # no scale/pdf shape uncert. for qcd
    #         continue
    #     for unc in ("murf_envelope", "pdf"):
    #         if proc == "st_tchannel" and unc == "pdf":
    #             # TODO: debugging (unphysically large/small pdf weights in process)
    #             continue
    #         self.add_parameter(
    #             f"{unc}_{proc}",
    #             process=inference_procnames.get(proc, proc),
    #             type=ParameterType.shape,
    #             config_shift_source=f"{unc}",
    #         )
    #         self.add_parameter_to_group(f"{unc}_{proc}", "theory")

    #
    # post-processing
    #
    print("Done!")
    self.cleanup()