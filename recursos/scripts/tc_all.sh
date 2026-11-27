#!/usr/bin/env bash
# tc_all.sh — Aplica el escenario A/B a los 4 contenedores desde el host.
#
# Uso:
#   ./tc_all.sh A
#   ./tc_all.sh B
#   ./tc_all.sh clear
#
# Requiere que los contenedores estén corriendo y que tc.sh esté dentro
# de la imagen (o copiarlo con docker cp).

set -euo pipefail

SCENARIO="${1:-A}"
NODES=(master-node worker-1 worker-2 worker-3)

for n in "${NODES[@]}"; do
  echo "===== $n ====="
  docker exec "$n" bash -lc "tc qdisc del dev eth0 root 2>/dev/null || true"
  case "$SCENARIO" in
    A) docker exec "$n" bash -lc "tc qdisc add dev eth0 root netem delay 0.5ms loss 0% rate 1000mbit" ;;
    B) docker exec "$n" bash -lc "tc qdisc add dev eth0 root netem delay 2ms loss 0.1% rate 100mbit" ;;
    clear) ;;
    *) echo "Uso: $0 [A|B|clear]"; exit 1 ;;
  esac
  docker exec "$n" tc qdisc show dev eth0
done
