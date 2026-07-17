from azh.config.analysis_azh_run3 import analysis_azh as A
ds = A.get_config('config_2023pre').get_dataset('data_muoneg_c2')
i = ds.get_info('nominal')
print('n_files:', i.n_files)
print('n_events:', i.n_events)
print('keys:', list(i.keys))
