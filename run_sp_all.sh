#!/bin/bash
# SP+CG 全办推广编排: pool / deep / sp 三阶段
# 用法: bash run_sp_all.sh pool|deep|sp
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
STAGE=${1:-all}
LINES="02 03 04 05 06 07 08 09 10 11"

if [ "$STAGE" = "pool" ]; then
  echo "=== Stage 1: 池生成 (5 线并行 x 2 批) ==="
  for batch in "02 03 04 05 06" "07 08 09 10 11"; do
    for lid in $batch; do
      $PY -u run_sp_experiment.py --line $lid --phase pool > /tmp/sp_pool_$lid.log 2>&1 &
    done
    wait
    echo "  批次完成: $batch"
  done
  echo "=== Stage 1 完成 ==="
fi

if [ "$STAGE" = "deep" ]; then
  echo "=== Stage 2: 深度波浪 (每线 v3 2x900s, 8 并发) ==="
  for lid in $LINES; do
    for s in 51 52; do
      echo "$lid $s"
    done
  done | xargs -P 8 -n 2 sh -c '.venv/bin/python -u run_sp_experiment.py --line "$1" --one "alns_v3:$2:900:deep$2_$1" > /tmp/sp_one_${1}_$2.log 2>&1' _
  echo "=== Stage 2 完成 ==="
fi

if [ "$STAGE" = "sp" ]; then
  echo "=== Stage 3: SP+CG 全线 (5 并行) ==="
  for batch in "02 03 04 05" "06 07 08 09 10 11"; do
    for lid in $batch; do
      $PY -u run_sp_experiment.py --line $lid --phase sp > /tmp/sp_final_$lid.log 2>&1 &
    done
    wait
    echo "  批次完成: $batch"
  done
  echo "=== Stage 3 完成 ==="
  $PY -u tools_sp_summary.py || true
fi
