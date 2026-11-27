#!/usr/bin/env bash
# netstats.sh — Snapshot de bytes/paquetes de una interfaz.
#
# Uso (dentro del contenedor o con docker exec):
#   ./netstats.sh eth0
#
# Salida: JSON de una línea con timestamp y contadores.
# Ejemplo de uso antes/después de una corrida:
#   ./netstats.sh eth0 > logs/net_before.json
#   ./collect.py ...
#   ./netstats.sh eth0 > logs/net_after.json

set -euo pipefail

IFACE="${1:-eth0}"
BASE="/sys/class/net/${IFACE}/statistics"

if [ ! -d "$BASE" ]; then
  echo "Interfaz no encontrada: $IFACE" >&2
  exit 1
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TX_BYTES="$(cat "$BASE/tx_bytes")"
RX_BYTES="$(cat "$BASE/rx_bytes")"
TX_PACKETS="$(cat "$BASE/tx_packets")"
RX_PACKETS="$(cat "$BASE/rx_packets")"
TX_DROPS="$(cat "$BASE/tx_dropped")"
RX_DROPS="$(cat "$BASE/rx_dropped")"

printf '{"timestamp":"%s","iface":"%s","tx_bytes":%s,"rx_bytes":%s,"tx_packets":%s,"rx_packets":%s,"tx_dropped":%s,"rx_dropped":%s}\n' \
  "$TS" "$IFACE" "$TX_BYTES" "$RX_BYTES" "$TX_PACKETS" "$RX_PACKETS" "$TX_DROPS" "$RX_DROPS"
