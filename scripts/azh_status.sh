#!/bin/bash
# overall production status; run on the production node (naf-cms14)
cd /data/dust/user/eranders/AZHtt/azh_semileptonic
STORE=/data/dust/user/eranders/azh_data/cf_store/analysis_azh
echo "===== node: $(hostname -s)   $(date '+%a %d %b %H:%M')"

echo "----- credentials"
klist 2>/dev/null | grep -A1 krbtgt | head -2 | sed 's/^/  kerberos: /'
pgrep -u $USER -x krenew >/dev/null && echo "  krenew: running" || echo "  krenew: NOT running"
echo "  proxy: $(openssl x509 -in "$X509_USER_PROXY" -noout -enddate 2>/dev/null || echo 'NOT FOUND at '$X509_USER_PROXY)"

echo "----- law processes"
pgrep -u $USER -fa "ProduceColumnsWrapper" | grep -v grep | grep -o "\-\-configs [^ ]*\|--datasets [^ ]*" | paste - - | sort | uniq -c

echo "----- batch queue"
condor_q $USER -totals 2>&1 | grep "Total for query\|AUTHENTICATE" | head -2
condor_q $USER -hold -af HoldReason 2>/dev/null | cut -c1-90 | sort | uniq -c | sed 's/^/  held: /'

echo "----- storage"
echo "  real usage: $(du -sh /data/dust/user/eranders/azh_data 2>/dev/null | cut -f1)   ($(my-dust-quota | tail -1 | awk '{print $2" of "$3" TB per quota tool"}'))"

echo "----- logs"
for f in $(ls -t logs_condor/mc_s*.log | head -3); do
  st=$(pgrep -u $USER -f "$(basename $f .log)" >/dev/null; grep -q "Luigi Execution Summary" $f && tail -n 40 $f | grep -o "looks :[()]" | tail -1)
  echo "  $f  [$(grep -c dummy_job_id $f) dummy, $(grep -c 'voms-proxy-info failed\|AUTHENTICATE' $f) auth, $(grep -c 'tolerance exceeded' $f) tolerance]  ${st:-running}"
  grep -E "all: " $f | tail -1 | cut -c1-150 | sed 's/^/      last: /'
done

echo "----- MC datasets with production output, per pass (2022post / 2024)"
for cfg in config_2022post config_2024; do
  find $STORE/cf.ProduceColumns/$cfg -path "*/v9/*" -name "*.parquet" 2>/dev/null \
    | sed "s|.*/cf.ProduceColumns/||" | grep -v "^$cfg/data_" | awk -F/ '{print $3, $2}' | sort -u \
    | awk '{print $1}' | sort | uniq -c | awk -v c=$cfg '{printf "  %-16s %-14s %s\n", c, $2, $1}'
done
