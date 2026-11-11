#!/bin/bash
# lists temporaries (calibration, selection, unmerged reduction) of MC datasets that are complete in all 9 passes
# usage: bash ~/azh_cleanup_complete.sh config_2024 [more configs]   -> writes /data/dust/user/eranders/del_complete.txt (deletes nothing)
python3 - "$@" <<'PYEOF'
import os, sys
BASE = "/data/dust/user/eranders/azh_data/cf_store/analysis_azh"
PASSES = ["nominal"] + [f"{v}_{d}" for v in ("e_scale", "e_smear", "mu_scale", "mu_resol") for d in ("up", "down")]
def v9_dirs(root):
    out = []
    for dp, dn, _ in os.walk(root):
        if os.path.basename(dp) == "v9":
            out.append(dp); dn[:] = []
    return out
def has_output(cfg, ds, p):
    return any(os.listdir(d) for d in v9_dirs(f"{BASE}/cf.ProduceColumns/{cfg}/{ds}/{p}") if os.path.isdir(d))
todo, done, busy = [], [], []
for cfg in sys.argv[1:]:
    root = f"{BASE}/cf.CalibrateEvents/{cfg}"
    for ds in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if ds.startswith("data_"):
            continue
        if all(has_output(cfg, ds, p) for p in PASSES):
            done.append(f"{cfg}/{ds}")
            for t in ("cf.CalibrateEvents", "cf.SelectEvents", "cf.ReduceEvents"):
                todo += v9_dirs(f"{BASE}/{t}/{cfg}/{ds}")
        else:
            busy.append(f"{cfg}/{ds}")
print(f"{len(done)} complete, {len(busy)} in progress:", *busy, sep="\n   ")
open("/data/dust/user/eranders/del_complete.txt", "w").write("\n".join(todo) + "\n")
print(f"{len(todo)} directories in /data/dust/user/eranders/del_complete.txt; delete with: xargs rm -rf < /data/dust/user/eranders/del_complete.txt")
PYEOF
