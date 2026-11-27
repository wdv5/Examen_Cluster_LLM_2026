# Logs

Aquí se guardan las salidas crudas:

- `metricas.jsonl` — una línea por corrida, con hash encadenado.
- `net_before.json` / `net_after.json` — contadores de red.
- `tc_A.txt` / `tc_B.txt` — salida de `tc qdisc show`.
- `ping_A.txt` / `ping_B.txt`, `iperf_A.json` / `iperf_B.json`.
- `nvidia-smi_*.csv`, `docker-stats_*.txt`.
- `master.log`, `worker-1.log`, etc.

No edites estos archivos: el informe debe citarlos tal como se generaron.
