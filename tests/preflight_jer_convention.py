#!/usr/bin/env python
# coding: utf-8

"""
JER scale-factor uncertainty convention, per era.

patches/cf031-jer-additive.patch makes columnflow use  SF_up/down = SF +- unc
(absolute), based on a Summer22 comparison. The JME changelog for the 2023 payloads
writes SF_up/down = SF * (1 +- unc) (relative). This script repeats the patch's test for
every era: it looks for any older JER payload of the same campaign that still has an
explicit "systematic" axis (nom/up/down), keeps only (eta, pt) points where that
payload's nominal equals the current nominal, and reports how well each convention
reproduces the published up/down there.

    source ~/azh_env.sh
    python tests/preflight_jer_convention.py 2>&1 | tee preflight_jer_convention.log
"""

import glob
import os
import traceback

import correctionlib
import numpy as np

CONFIGS = ["config_2022pre", "config_2022post", "config_2023pre", "config_2023post", "config_2024"]
JSONPOG = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/*/jet_jerc.json.gz"
ETAS = np.round(np.arange(-4.95, 5.0, 0.1), 3)
PTS = [15.0, 20.0, 30.0, 50.0, 100.0, 200.0, 500.0, 1000.0]


def args_for(corr, eta, pt, syst=None):
    out = []
    for i in corr.inputs:
        n = i.name.lower()
        if "eta" in n:
            out.append(eta)
        elif "pt" in n:
            out.append(pt)
        elif "syst" in n:
            out.append(syst)
        else:
            raise KeyError(f"unexpected input {i.name} in {corr.name}")
    return out


def main():
    from azh.config.analysis_azh_run3 import analysis_azh as ana

    for n in CONFIGS:
        try:
            cfg = ana.get_config(n)
            cur_path = cfg.x.external_files.jet_jerc[0]
            cur = correctionlib.CorrectionSet.from_file(cur_path)
            jer_key = next(k for k in cur.keys() if k.endswith("_SFUncertainty_AK4PFPuppi"))
            prefix = jer_key[: -len("SFUncertainty_AK4PFPuppi")]  # e.g. Summer22_22Sep2023_JRV2_MC_
            campaign = prefix.split("_JRV")[0]
            sf_cur, unc_cur = cur[f"{prefix}ScaleFactor_AK4PFPuppi"], cur[jer_key]
            print(f"\n== {n}: current {prefix}* in {cur_path.split('/metadata/')[-1]}")

            candidates = sorted(set(glob.glob(os.path.join(os.path.dirname(os.path.dirname(cur_path)),
                                                           "*", "jet_jerc.json.gz")) + glob.glob(JSONPOG)))
            found = False
            for path in candidates:
                try:
                    cs = correctionlib.CorrectionSet.from_file(path)
                except Exception:
                    continue
                for k in cs.keys():
                    if not (k.startswith(campaign) and k.endswith("_ScaleFactor_AK4PFPuppi")):
                        continue
                    old = cs[k]
                    if not any("syst" in i.name.lower() for i in old.inputs):
                        continue
                    found = True
                    rows = []
                    for eta in ETAS:
                        for pt in PTS:
                            try:
                                nom_new = sf_cur.evaluate(*args_for(sf_cur, eta, pt))
                                unc = unc_cur.evaluate(*args_for(unc_cur, eta, pt))
                                nom_old = old.evaluate(*args_for(old, eta, pt, "nom"))
                                up = old.evaluate(*args_for(old, eta, pt, "up"))
                                down = old.evaluate(*args_for(old, eta, pt, "down"))
                            except Exception:
                                continue
                            if abs(nom_new - nom_old) > 1e-6:
                                continue
                            rows.append((eta, pt, nom_new, unc, up, down))
                    where = path.split("/metadata/")[-1] if "/metadata/" in path else path.split("/POG/")[-1]
                    if not rows:
                        print(f"   {k} ({where}): no points with identical nominal")
                        continue
                    r = np.array(rows)
                    eta, pt, nom, unc, up, down = r.T
                    half = 0.5 * (up - down)  # published symmetric half-width, absolute
                    bulk = (np.abs(eta) < 2.5) & (pt >= 30) & (pt <= 200)
                    print(f"   {k} ({where}): {len(r)} points with identical nominal ({int(bulk.sum())} in bulk)")
                    for label, m in (("all ", np.ones(len(r), bool)), ("bulk", bulk)):
                        ok = m & (half > 1e-4)
                        if not ok.any():
                            continue
                        ra = unc[ok] / half[ok]                  # -> 1 if unc is absolute
                        rm = unc[ok] / (half[ok] / nom[ok])      # -> 1 if unc is relative
                        fa = np.mean(np.abs(ra - 1) < 0.02)
                        fm = np.mean(np.abs(rm - 1) < 0.02)
                        print(f"      {label} unc/abs-halfwidth: median {np.median(ra):.3f}, within 2% {fa:5.1%} | "
                              f"unc/rel-halfwidth: median {np.median(rm):.3f}, within 2% {fm:5.1%}")
                    break  # older payloads of one campaign are identical; one reference suffices
                if found:
                    break
            if not found:
                print("   no older payload with an explicit nom/up/down axis found for this campaign")
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    main()
