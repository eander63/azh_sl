from azh.config.analysis_azh_run3 import analysis_azh as A
c = A.get_config('config_2023pre')
for d in ['data_mu_c1','data_egamma_c1','data_muoneg_c1']:
    ds = c.get_dataset(d)
    print(d, 'n_files=', ds.get_info('nominal').n_files, 'key=', list(ds.get_info('nominal').keys)[0])
