cd /data/dust/user/eranders/AZHtt/azh_semileptonic
export CF_DATA=/data/dust/user/$(whoami)/azh_data
export CF_HTCONDOR_FLAVOR=naf_el9
export CF_JOB_BASE=/data/dust/user/$(whoami)/azh_jobs
export CF_WLCG_USE_CACHE=True
export CF_WLCG_CACHE_ROOT=/data/dust/user/$(whoami)/azh_cache
export CF_WLCG_CACHE_CLEANUP=False
source setup.sh
source modules/columnflow/sandboxes/venv_columnar_dev.sh
export X509_USER_PROXY=/data/dust/user/eranders/.grid/x509up
python -c "import law, correctionlib, uproot, awkward; print('sandbox ok')"
export TMPDIR=/data/dust/user/eranders/azh_tmp
