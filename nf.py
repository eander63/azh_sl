from azh.config.analysis_azh_run3 import analysis_azh as A
print("w_lnu n_files:", A.get_config('config_2023pre').get_dataset('w_lnu_amcatnlo').get_info('nominal').n_files)
