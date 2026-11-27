#!/usr/bin/env bash
# tc.sh — Emula el escenario de red A o B en una interfaz.
#
# Uso:
#   ./tc.sh eth0 A       # 1 Gbps, 0.5 ms
#   ./tc.sh eth0 B       # 100 Mbps, 2 ms, 0.1 % pérdida
#   ./tc.sh eth0 clear   # elimina la regla
#
# Requiere NET_ADMIN (docker compose ya lo añade) y el módulo sch_netem.
# Verifica con: tc qdisc show dev eth0

set -euo pipefail

IFACE="${1:-eth0}"
SCENARIO="${2:-A}"

case "$SCENARIO" in
  A)
    DELAY="0.5ms"
    LOSS="0%"
    RATE="1000mbit"
    ;;
  B)
    DELAY="2ms"
    LOSS="0.1%"
    RATE="100mbit"
    ;;
  clear)
    tc qdisc del dev "$IFACE" root 2>/dev/null || true
    echo "Regla eliminada en $IFACE"
    tc qdisc show dev "$IFACE"
    exit 0
    ;;
  *)
    echo "Uso: $0 [interfaz] [A|B|clear]" >&2
    exit 1
    ;;
esac

# Limpia cualquier regla previa para que la prueba sea reproducible.
tc qdisc del dev "$IFACE" root 2>/dev/null || true

# netem aplica delay, loss y rate en una sola qdisc.
tc qdisc add dev "$IFACE" root netem delay "$DELAY" loss "$LOSS" rate "$RATE"

echo "Escenario $SCENARIO aplicado en $IFACE: delay=$DELAY loss=$LOSS rate=$RATE"
echo "--- tc qdisc show ---"
tc qdisc show dev "$IFACE"
echo "--- tc -s qdisc show ---"
tc -s qdisc show dev "$IFACE"
