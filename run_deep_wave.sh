#!/bin/bash
# 绝对能力验证: 深度波浪 (长跑多路并行) -> SP 终解
# 用法: bash run_deep_wave.sh
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python

echo "=== Wave A+B+C: 8 x 900s 长跑 (并行) ==="
for s in 21 22 23 31 32 33; do
  $PY -u run_sp_experiment.py --one alns_v3:$s:900:v3s$s > /tmp/sp_one_v3s$s.log 2>&1 &
done
$PY -u run_sp_experiment.py --one hgs_pvrp:41:900:hgs41 > /tmp/sp_one_hgs41.log 2>&1 &
$PY -u run_sp_experiment.py --one hgs_pvrp:42:900:hgs42 > /tmp/sp_one_hgs42.log 2>&1 &
wait
echo "=== 深度波浪完成 ==="
echo "=== SP 终解 (含全部列) ==="
$PY -u run_sp_experiment.py --phase sp
