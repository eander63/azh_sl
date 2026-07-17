import awkward as ak, glob, numpy as np
fs=sorted(glob.glob('/data/dust/user/eranders/azh_data/cf_store/**/cf.ProduceColumns/**/config_2023pre/**/dy_m50toinf_amcatnlo/**/*.parquet',recursive=True))
print("files found:", len(fs))
if fs:
    a=ak.from_parquet(fs[0])
    for c in ['electron_id_weight','electron_weight','electron_trig_weight','electron_mid_weight']:
        if c in a.fields:
            v=ak.to_numpy(a[c]).astype('float64')
            print(f"{c}: mean={v.mean():.4f} min={v.min():.4f} max={v.max():.4f} frac>2={np.mean(v>2):.4f} frac==0={np.mean(v==0):.4f}")
        else:
            print(c, "NOT PRESENT")
