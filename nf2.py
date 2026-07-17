from azh.config.analysis_azh_run3 import analysis_azh as A
print(A.get_config('config_2023post').get_dataset('tth_hnonbb_powheg').get_info('nominal').n_files)
