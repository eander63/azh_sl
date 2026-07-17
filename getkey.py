from azh.config.analysis_azh_run3 import analysis_azh as A
i = A.get_config('config_2023post').get_dataset('tth_hnonbb_powheg').get_info('nominal')
print('n_files:', i.n_files)
print('keys:', list(i.keys))
