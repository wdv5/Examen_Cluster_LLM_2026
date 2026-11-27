# Recursos del examen — Clúster LLM

Este directorio contiene el scaffold para el examen. **No es la solución**: es el punto de partida para que el estudiante no pierda 3 horas instalando dependencias.

## Árbol

```
recursos/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── prompt.txt
├── plantilla_costos.xlsx
├── models/                  # aquí va el GGUF (no se versiona)
├── logs/                    # salida de métricas
└── scripts/
    ├── tc.sh
    ├── tc_all.sh
    ├── collect.py
    ├── netstats.sh
    └── netem_proxy.py
```

## 1. Requisitos

- Linux (Ubuntu 22.04/24.04) o WSL2 con Docker.
- Docker 24+ y Docker Compose v2.
- NVIDIA driver 550+ y `nvidia-container-toolkit`.
- 32 GB de RAM en el host (mínimo 24 GB para el Perfil A).
- GPU(s) con al menos 20 GB de VRAM en total (Perfil A).
- 20 GB de disco libre.

Prueba rápida:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Si falla, instala `nvidia-container-toolkit` antes de continuar.

## 2. Modelo

Perfil A (Qwen2.5-7B-Instruct Q8_0, Apache 2.0):

```bash
mkdir -p models
# Opción 1: huggingface-cli
pip install -U "huggingface_hub[cli]"
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
  qwen2.5-7b-instruct-q8_0.gguf --local-dir models

# Opción 2: curl
curl -L -o models/qwen2.5-7b-instruct-q8_0.gguf \
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q8_0.gguf

sha256sum models/qwen2.5-7b-instruct-q8_0.gguf
ls -lh models/
```

> Si el repo entrega el modelo dividido (`-00001-of-00002.gguf`), únelo con:
> `llama-gguf-split --merge parte-00001-of-00002.gguf modelo.gguf`

Perfil B (Qwen2.5-3B-Instruct Q8_0):

```bash
huggingface-cli download Qwen/Qwen2.5-3B-Instruct-GGUF \
  qwen2.5-3b-instruct-q8_0.gguf --local-dir models
```

Anota el SHA-256 y el tamaño exacto en el informe.

## 3. Construir y levantar

```bash
cp .env.example .env
# Edita .env: MODEL_FILE, LLAMA_CPP_REF (commit), CUDA_ARCHS, memoria
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f master
```

- El build compila `llama.cpp` con CUDA y RPC; tarda 20–40 min.
- Fija `LLAMA_CPP_REF` a un commit/tag; `master` no es reproducible.
- `CUDA_ARCHS`: `61` GTX 1050 Ti, `86` RTX 3060, `89` RTX 4090.
- Si no tienes GPU, elimina el bloque `deploy` del compose y usa `--n-gpu-layers 0`.

Verifica:

```bash
curl -s http://localhost:8080/health
docker exec master-node nvidia-smi
docker exec worker-1 nvidia-smi
```

## 4. Red A/B

Desde el host:

```bash
./scripts/tc_all.sh A
./scripts/tc_all.sh B
./scripts/tc_all.sh clear
```

O dentro de cada contenedor:

```bash
docker exec master-node bash /scripts/tc.sh eth0 A
docker exec worker-1 bash /scripts/tc.sh eth0 B
```

Verifica:

```bash
docker exec master-node tc qdisc show dev eth0
docker exec master-node ping -c 20 worker-1
docker exec master-node iperf3 -c worker-1 -t 10
```

> `tc` requiere `NET_ADMIN` (ya está en el compose). En Docker Desktop/Windows puede fallar; usa WSL2 o el proxy. Si los scripts no tienen permiso de ejecución (común al montar desde Windows), invócalos con `bash`.

## 5. Métricas

Desde el host (el puerto 8080 está publicado):

```bash
python3 scripts/collect.py \
  --label C1-A-r1 \
  --n-predict 300 \
  --prompt-file prompt.txt \
  --out logs/metricas.jsonl \
  --extra '{"scenario":"A","config":{"workers":3,"ctx":4096}}'
```

Antes y después, captura bytes de red:

```bash
docker exec master-node bash /scripts/netstats.sh eth0 > logs/net_before.json
# ... corrida ...
docker exec master-node bash /scripts/netstats.sh eth0 > logs/net_after.json
```

Para RAM/VRAM:

```bash
docker stats --no-stream
docker exec worker-1 nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu \
  --format=csv,noheader
```

## 6. Costos

Abre `plantilla_costos.xlsx`:

- Amarillo = dato de entrada.
- Gris = fórmula.
- Hojas: `CAPEX`, `OPEX`, `TCO`, `Comparacion`, `BreakEven`, `Sensibilidad`.

Completa con precios cotizados y cita la fuente.

## 7. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `rpc-server: not found` | Build sin `-DGGML_RPC=ON` | Revisa el Dockerfile; reconstruye |
| `CUDA out of memory` | Shard demasiado grande | Ajusta `--tensor-split`, baja contexto, KV FP8 |
| `Connection refused` al worker | Worker no arrancó | `docker compose logs worker-1` |
| `tc: Operation not permitted` | Falta `NET_ADMIN` | Usa `cap_add`, Linux/WSL2 |
| `netem: qdisc not found` | Kernel sin `sch_netem` | Usa una VM Linux o `netem_proxy.py` |
| `health` falla | Modelo mal nombrado o OOM | `docker compose logs master`; revisa `.env` |
| Muy lento | CPU offload, PCIe, GPU compartida | `nvidia-smi`, `--n-gpu-layers`, menos batch |
| OOM en master | Modelo + page cache | Sube `MASTER_MEM` o usa `--no-mmap` |

## 8. Google Colab

Colab no permite Docker con `--privileged` ni cgroups de VRAM. Usa el Perfil B:

1. 4 procesos: `llama-server` + 3 `rpc-server` en `127.0.0.1:50052-50054`.
2. `ulimit -v` por proceso (2 GB) y `--no-mmap`.
3. `netem_proxy.py` para latencia/pérdida/ancho de banda.
4. Modelo Qwen2.5-3B Q8 (3.3 GB), que no cabe en 2 GB.
5. T4 como *baseline* de GPU única.

Ejemplo:

```bash
# terminal 1
ulimit -v 2000000
./rpc-server -H 127.0.0.1 -p 50052

# terminal 2 (proxy B)
python3 scripts/netem_proxy.py --listen-port 6001 --target-host 127.0.0.1 \
  --target-port 50052 --delay-ms 2 --loss 0.001 --rate-mbps 100

# terminal 3
./llama-server -m models/qwen2.5-3b-instruct-q8_0.gguf \
  --rpc 127.0.0.1:6001 --tensor-split 1 -c 4096 -n 300 --port 8080
```

## 9. Notas

- El compose asigna `count: all` de GPU a los 4 servicios. Si tienes varias GPU, usa `device_ids` para una por worker. Si tienes una sola, todos la comparten y la partición de VRAM es lógica.
- `mem_limit` es RAM, no VRAM. Para VRAM no hay cgroups estándar en GPU de consumo; usa `--tensor-split` y verifica con `nvidia-smi`.
- No uses swap para LLM: degrada el rendimiento y puede enmascarar OOM.
- Guarda logs crudos; el informe debe citar la línea o el archivo.

## 10. Licencia y atribución

- Código del scaffold: uso educativo.
- `llama.cpp`: licencia MIT.
- Qwen2.5: Apache 2.0. Consulta el `LICENSE` del repo del modelo.
- Cita el libro: Patterson & Hennessy, *Computer Organization and Design*, RISC-V Edition, 2nd ed.
