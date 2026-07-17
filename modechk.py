import awkward as ak, glob, numpy as np
def peak(patt, label):
    fs=sorted(glob.glob(patt,recursive=True))
    if not fs: print(label,"— no files"); return
    a=ak.from_parquet(fs[0])
    col=[c for c in a.fields if c.lower() in ('m_z','mll','dilep_mass','z_mass')]
    if not col: print(label,"cols:",[c for c in a.fields if 'm' in c.lower()][:10]); return
    m=ak.to_numpy(a[col[0]]).astype('float64'); m=m[(m>60)&(m<120)]
    h,e=np.histogram(m,bins=60,range=(60,120))
    print(f"{label}: peak bin center = {(e[h.argmax()]+e[h.argmax()+1])/2:.1f}  (n={len(m)})")
peak('/data/dust/user/eranders/azh_data/cf_store/**/cf.ProduceColumns/**/config_2023pre/**/data_egamma_c1/**/*.parquet','data egamma')
peak('/data/dust/user/eranders/azh_data/cf_store/**/cf.ProduceColumns/**/config_2023pre/**/data_mu_c1/**/*.parquet','data mu')
