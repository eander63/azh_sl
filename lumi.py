from azh.config.analysis_azh_run3 import analysis_azh as A
for cfg in ['config_2022pre','config_2022post','config_2023pre','config_2023post']:
    print(cfg, 'lumi =', A.get_config(cfg).x.luminosity)
