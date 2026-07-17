import awkward as ak, glob, numpy as np
for cfg in ['config_2022pre','config_2022post','config_2023pre','config_2023post']:
    fs=sorted(glob.glob(f'/data/dust/user/eranders/azh_data/cf_store/**/cf.ProduceColumns/**/{cfg}/**/dy_m50toinf_amcatnlo/**/*.parquet',recursive=True))
    if not fs: print(cfg,'no files'); continue
    a=ak.from_parquet(fs[0]); mc=ak.to_numpy(a['mc_weight']).astype('float64'); W=mc.sum()
    out=f"{cfg}: "
    for c in ['pu_weight','normalized_pu_weight']:
        if c in a.fields:
            out+=f"{c} mc-mean={ (mc*ak.to_numpy(a[c]).astype('float64')).sum()/W :.4f}  "
    print(out)
