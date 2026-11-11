# production settings (source after ~/azh_env.sh)
SHIFTS="nominal,e_scale_*,e_smear_*,mu_scale_*,mu_resol_*"
COMMON="--version v9 --workflow htcondor --cf.CalibrateEvents-workflow htcondor --cf.SelectEvents-workflow htcondor --cf.ReduceEvents-workflow htcondor --cf.MergeReducedEvents-workflow htcondor --cf.CalibrateEvents-htcondor-memory 9"
# NAF allows 5000 queued jobs per user: keep workers x 500 well below that
CAPS="--cf.CalibrateEvents-parallel-jobs 500 --cf.SelectEvents-parallel-jobs 500 --cf.ReduceEvents-parallel-jobs 500 --cf.MergeReducedEvents-parallel-jobs 500 --cf.ProduceColumns-parallel-jobs 500"
