from azh.config.analysis_azh_run3 import analysis_azh as A
for cfg in ['config_2023pre','config_2023post']:
    c=A.get_config(cfg); bad=[]
    for d in c.datasets:
        if d.is_data: continue
        try:
            k=list(d.get_info('nominal').keys)[0]
        except Exception:
            continue
        if 'Summer22' in k:
            bad.append((d.name,k))
    print(f"=== {cfg}: {len(bad)} stale Summer22 keys ===")
    for n,k in bad: print(" ",n,'->',k)
