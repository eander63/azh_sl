from azh.config.analysis_azh_run3 import analysis_azh as A
c = A.get_config('config_2023pre')
for d in ['data_muoneg_c1','data_muoneg_c2','data_muoneg_c3','data_muoneg_c4']:
    i = c.get_dataset(d).get_info('nominal')
    print(d, 'n_files=', i.n_files, 'keys=', list(i.keys))
