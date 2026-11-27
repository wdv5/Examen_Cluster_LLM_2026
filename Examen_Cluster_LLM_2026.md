# Examen parcial integrador — Clúster distribuido de inferencia LLM

**UNIVERSIDAD TECNOLÓGICA DE BOLÍVAR**
Arquitectura de Computadores · *Computer Organization and Design, RISC-V*, 2.ª ed.
Capítulos 4, 5 y 6 · Diseño, medición y costo de un clúster de inferencia

| Campo | Valor |
|---|---|
| Modalidad | Individual, take-home |
| Tiempo | 24 horas (8–10 h efectivas) |
| Entrega | Informe + repositorio + logs + hoja de costos |
| Peso | 100 puntos + 10 de bonificación |
| Fecha | ____________________________ |
| Estudiante | ____________________________ |
| Código | ____________________________ |

> No hay una única respuesta correcta. Se califica la coherencia entre el modelo, la medición y la decisión. La mejor nota es para quien logre el mejor rendimiento normalizado y la justificación más clara, con gráficos y tablas comparativas.

---

## Nota para el estudiante

No hay una única respuesta correcta. Todas las configuraciones técnicamente coherentes son válidas. La mejor calificación se reserva para quien demuestre el **mejor rendimiento normalizado** (no el absoluto: depende del hardware que le tocó), el **menor costo total en pesos** para el nivel de servicio exigido y, sobre todo, la **justificación más clara y concisa** de por qué usa cada componente del clúster y cómo esa elección mejora el rendimiento.

El informe debe sostenerse con gráficos y tablas comparativas: topología, descomposición de memoria, A vs. B, Pareto costo/rendimiento, sensibilidad y break-even. Una conclusión sin datos vale poco; un dato sin explicación vale menos.

Se permite usar asistentes de IA para programar o depurar, pero debe declararse qué se usó y cada número debe ser reproducible a partir de los logs entregados. La defensa oral de 3–5 minutos es obligatoria y puede ser solicitada para verificar autoría.

---

## 1. Resultados de aprendizaje

Al finalizar, el estudiante podrá:

1. Dimensionar memoria, VRAM y almacenamiento para cargar un LLM cuantizado y decidir si cabe en un nodo o debe particionarse (CAP 5).
2. Diseñar una topología maestro-trabajadores y justificar *pipeline parallelism* vs. *tensor parallelism* (CAP 6).
3. Modelar el rendimiento con la ecuación de CPU, AMAT, roofline y la Ley de Amdahl (CAP 4, 5 y 6).
4. Emular una red realista y medir su impacto en TTFT, tokens/s y transferencia (CAP 6).
5. Calcular el costo total de propiedad (TCO) en COP, el costo por millón de tokens y el punto de equilibrio frente a una API o un servidor GPU único (CAP 6).
6. Analizar cuellos de botella y recomendar una actualización con criterio costo/beneficio.

---

## 2. Escenario

**Andina AI** es una empresa de análisis financiero en Cartagena. Quiere ejecutar un asistente LLM en su oficina, porque los prompts contienen datos de clientes que no pueden salir del edificio. Ya tiene:

- 1 servidor principal (**master**) con 32 GB de RAM, 8 GB de VRAM (RTX 3060) y 1 TB NVMe.
- 3 computadores de oficina (**workers**) con 16 GB de RAM, 4 GB de VRAM (GTX 1050 Ti) y 512 GB SSD SATA.
- 1 switch Ethernet Gigabit (1 Gbps) de 8 puertos y cableado Cat6.

**Presupuesto de inversión:** COP 15 000 000 (sin incluir el hardware que ya tiene).
**Tarifa de energía:** COP 800/kWh; **internet:** COP 120 000/mes.
**Jornada de uso:** 8 h/día, 250 días/año.

### Carga de trabajo

| Parámetro | Valor |
|---|---|
| Solicitudes | 500/día; pico 3 req/s |
| Prompt | 300 tokens |
| Respuesta | 300 tokens |
| Contexto | 4 096 tokens |
| SLO de latencia | TTFT ≤ 6 s; TPOT ≤ 150 ms (≥ 6.7 tok/s por usuario) |
| Disponibilidad | 99 % en horario laboral |
| Privacidad | Obligatoria: los datos no pueden salir de la oficina |

El equipo de TI quiere saber si el clúster es viable, cuánto cuesta realmente y qué conviene actualizar primero. También evaluará dos alternativas: un servidor GPU único y una API en la nube (esta última solo como referencia, porque viola la restricción de privacidad).

---

## 3. Restricciones y criterios de éxito

1. El modelo **no debe caber en un solo nodo**. Debe particionarse entre al menos dos nodos. Si un nodo intenta cargarlo completo, debe fallar por OOM (VRAM o RAM).
2. El estudiante debe entregar evidencia de la partición: logs de `llama.cpp`, `nvidia-smi`, `docker stats` y `OOMKilled`.
3. La red debe emularse con `tc netem` (o el proxy provisto en el perfil Colab) en dos escenarios:
   - **A — Oficina estándar:** 1 000 Mbps, 0.5 ms de latencia por salto.
   - **B — Red degradada:** 100 Mbps, 2 ms de latencia, 0.1 % de pérdida.
4. Se deben evaluar **al menos 4 configuraciones** (por ejemplo: 2 vs. 3 workers, contexto 2K vs. 4K) en ambos escenarios. La combinación ganadora debe cumplir el SLO y minimizar el costo por millón de tokens.
5. El costo es parte del examen: CAPEX, OPEX, TCO a 3 años, costo por 1M de tokens y break-even.

---

## 4. Perfiles de hardware (elige uno)

El examen se adapta al hardware disponible. El profesor asigna el perfil o el estudiante lo declara y justifica.

### Perfil A — Referencia (recomendado)

| Nodo | CPU/RAM | GPU/VRAM | Disco | Rol |
|---|---|---|---|---|
| master | Ryzen 7, 32 GB | RTX 3060, 8 GB | 1 TB NVMe | Servidor HTTP + coordinador + posible shard |
| worker-1 | i5-4590, 16 GB | GTX 1050 Ti, 4 GB | 512 GB SATA | rpc-server |
| worker-2 | i5-4590, 16 GB | GTX 1050 Ti, 4 GB | 512 GB SATA | rpc-server |
| worker-3 | i5-4590, 16 GB | GTX 1050 Ti, 4 GB | 512 GB SATA | rpc-server |

- **Red Docker:** `10.0.50.0/24`.
- **Modelo:** Qwen2.5-7B-Instruct Q8_0 (~8.1 GB). No cabe en 8 GB (master) ni en 4 GB (workers): la partición es obligatoria.
- **Contexto de trabajo:** 4 096 tokens.

### Perfil B — Bajo recurso / Google Colab

| Proceso | Límite | Rol |
|---|---|---|
| master | 4 GB RAM | Servidor HTTP + coordinador |
| worker-1..3 | 2 GB RAM c/u | rpc-server (CPU) |
| Opcional | T4 16 GB | Baseline de GPU única |

- **Modelo:** Qwen2.5-3B-Instruct Q8_0 (~3.3 GB). No cabe en 2 GB: se parte en 2–3 workers.
- Sin Docker: 4 procesos + `ulimit -v` + proxy de red en espacio de usuario.
- Este perfil no reproduce cgroups/tc fielmente; se evalúa la coherencia del modelo y la comparación, no la fidelidad del contenedor.

### Perfil C — Avanzado (opcional, para equipos con 4×24 GB)

- **Modelo:** Qwen2.5-72B-Instruct Q4_K_M (~41 GB).
- 4 nodos con 24 GB VRAM; red 10 Gbps o InfiniBand.
- Sirve para estudiar *tensor parallelism* y el cruce red/cómputo. No es obligatorio.

> **Regla de selección del modelo:** el tamaño del archivo cuantizado debe ser **mayor** que la VRAM del nodo más grande (para forzar la partición) y **menor** que la suma de VRAM de todos los nodos (para que quepa). Si tu hardware no cumple, elige el perfil B o documenta la adaptación.

---

## 5. Modelo y software

### 5.1 Modelo de referencia: Qwen2.5-7B-Instruct Q8_0

| Parámetro | Valor |
|---|---|
| Parámetros | 7.62 B |
| Capas | 28 |
| Cabezas de atención | 28 |
| Cabezas KV (GQA) | 4 |
| head_dim | 128 |
| Dimensión oculta | 3 584 |
| Vocabulario | 152 064 |
| Contexto nativo | 32 768 |
| Tamaño Q8_0 | ≈ 8.1 GB |
| Licencia | Apache 2.0 |

KV por token (FP16):

```
KV = 2 × 28 capas × 4 cabezas KV × 128 × 2 B = 57 344 B ≈ 56 KiB/token
```

| Contexto | KV por sesión |
|---|---|
| 2 048 | 112 MiB |
| 4 096 | 224 MiB |
| 8 192 | 448 MiB |
| 32 768 | 1.75 GiB |

**Alternativa permitida:** Mistral-7B-Instruct-v0.3 Q8_0 (~7.7 GB, Apache 2.0) o Llama-3.1-8B-Instruct Q8_0 (~8.5 GB, licencia Llama). Si usas otra, entrega su model card y justifica.

### 5.2 Software

| Componente | Versión / nota |
|---|---|
| Docker + Compose | 24+ / v2 |
| NVIDIA driver | 550+ |
| nvidia-container-toolkit | Instalado y probado con `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` |
| llama.cpp | Compilado con `-DGGML_RPC=ON -DGGML_CUDA=ON`; anota el commit |
| tc / iproute2 | Para emular red |
| iperf3, curl, jq, python3 | Medición y recolección |

El repositorio `recursos/` incluye `Dockerfile`, `docker-compose.yml`, `tc.sh`, `collect.py`, `netstats.sh`, `netem_proxy.py` y la plantilla de costos.

---

## 6. Parte 0 — Pre-lab: modelo, memoria y costos (5 puntos)

Se entrega antes de la sesión práctica (o como primera mitad del take-home).

### Tareas

1. **Descarga y verifica el modelo:**
   - Tamaño exacto del archivo (GB).
   - SHA-256.
   - Licencia.
   - Tiempo de descarga a 100 Mbps y 1 Gbps (calculado y, si puedes, medido).
2. **Calcula para el perfil asignado:**
   - Bytes de pesos = `N × bytes_por_parámetro`.
   - KV por token y KV para 2K, 4K y 8K.
   - Memoria total para batch 1 y batch 8: `pesos + KV + runtime + activaciones`.
   - ¿Cabe en el nodo más grande? ¿Por qué no?
3. **Contexto máximo por worker:**

   ```
   max_ctx = (RAM_límite − runtime − shard − activaciones) / KV_por_token
   ```

   Usa el shard que te toque según `--tensor-split`.
4. **Llena la hoja de costos** (`plantilla_costos.xlsx`):
   - CAPEX con precios cotizados en Colombia (fuente, tienda, fecha).
   - OPEX: energía, internet, mantenimiento, depreciación.
   - TCO a 3 años.
5. **Declara el perfil elegido y por qué.**

### Entregables

- `prelab.md` (máx. 2 páginas) con fórmulas y tablas.
- `costos.xlsx` con la hoja CAPEX/OPEX completa.

---

## 7. Parte 1 — Topología y partición (15 puntos)

### Tareas

1. **Levanta 4 nodos** en la red `10.0.50.0/24`: master en `10.0.50.11`, workers en `.12`, `.13`, `.14`.
   - Límites de memoria: master 16 GB RAM; workers 8 GB RAM (Perfil A). Ajusta si usas otro perfil y documéntalo.
   - GPU: asigna una GPU por worker si el host tiene varias; si solo hay una, documenta que la partición es lógica y usa CPU para los workers o MIG si está disponible.
2. **Configura llama.cpp en modo RPC:**
   - En cada worker: `rpc-server -H 0.0.0.0 -p 50052`.
   - En el master: `llama-server -m <modelo> --rpc worker-1:50052,worker-2:50052,worker-3:50052 --tensor-split ... -c 4096 -n 300`.
   - Ajusta `--tensor-split` según la VRAM/RAM de cada nodo y justifícalo.
3. **Demuestra la partición:**
   - `nvidia-smi` en cada nodo mostrando el shard cargado (o logs de `rpc-server`).
   - `docker stats` con el uso de RAM/VRAM.
   - `docker inspect` con `OOMKilled`.
4. **Prueba OOM:** intenta cargar el modelo completo en un worker (sin RPC) con `llama-cli --n-gpu-layers 99`. Captura:
   - Código de salida (`137`).
   - `OOMKilled: true`.
   - Mensaje de error (*CUDA out of memory* o *Killed*).
   - Explica por qué el master tampoco puede cargarlo solo.
5. **Diagrama de topología** con IPs, roles, shards, sentidos de las flechas y cuellos de botella esperados.

### Evidencia mínima

- `docker compose ps`, `docker inspect`, logs de `llama-server` y `rpc-server`.
- `nvidia-smi` de cada nodo.
- Captura del OOM.
- Diagrama (PNG/SVG o Mermaid).

---

## 8. Parte 2 — Emulación de red (15 puntos)

### Tareas

1. **Aplica `tc netem`** en la interfaz `eth0` de todos los nodos (egress):

   **Escenario A:**

   ```bash
   tc qdisc del dev eth0 root 2>/dev/null || true
   tc qdisc add dev eth0 root netem delay 0.5ms loss 0% rate 1000mbit
   tc qdisc show dev eth0
   ```

   **Escenario B:**

   ```bash
   tc qdisc del dev eth0 root 2>/dev/null || true
   tc qdisc add dev eth0 root netem delay 2ms loss 0.1% rate 100mbit
   tc qdisc show dev eth0
   ```

2. **Verifica con:**
   - `ping -c 20 worker-1` (RTT promedio, desviación, pérdida).
   - `iperf3 -c worker-1 -t 10 -J` (throughput real vs. nominal).
   - `tc -s qdisc show dev eth0` (paquetes descartados).
3. **Documenta la diferencia entre el nominal y el medido.** ¿Por qué el RTT no es exactamente 0.5 ms? ¿Por qué el throughput no es exactamente 1 Gbps?
4. **Explica cómo aplicarías la regla en un switch físico real** (p. ej., *police* / *shaper* en el puerto) y qué limitación tiene emular en el host.

### Evidencia mínima

- Salida de `tc qdisc show` en A y B.
- `ping` e `iperf3` en JSON o tabla.
- Captura de `tc -s`.

---

## 9. Parte 3 — Métricas y configuraciones (20 puntos)

### 9.1 Prompt estandarizado

Usa el prompt de `recursos/prompt.txt` (200 palabras, en español, con una tarea de análisis). **No lo cambies entre corridas.**

Parámetros del servidor:

- `temperature = 0`
- `seed = 42`
- `n_predict = 300`
- `context = 4096`
- `stream = true`

### 9.2 Protocolo

- 1 corrida de calentamiento (se descarta).
- 3 repeticiones medidas; reporta **mediana e IQR**.
- Entre A y B, limpia la caché de modelo y reinicia los servidores para evitar *warm start*.
- Cierra aplicaciones de fondo; no uses modo ahorro de energía.
- Registra la temperatura/clock de la GPU si es posible (`nvidia-smi --query-gpu=...`).

### 9.3 Configuraciones a evaluar (mínimo 4)

| # | Workers | Contexto | Tensor split | KV | Nota |
|---|---|---|---|---|---|
| C1 | 3 | 2 048 | igual | FP16 | Línea base |
| C2 | 3 | 4 096 | igual | FP16 | Más contexto |
| C3 | 2 | 2 048 | proporcional | FP16 | Menos nodos |
| C4 | 3 | 4 096 | proporcional a VRAM | FP16/FP8 | Optimizada |

Puedes añadir C5 (por ejemplo, 3 workers con `--tensor-split` desbalanceado) si tu hardware lo permite. No se trata de correr todo, sino de elegir un espacio de búsqueda y justificarlo.

### 9.4 Métricas por corrida

| Métrica | Cómo se obtiene |
|---|---|
| TTFT | Tiempo desde el POST hasta el primer chunk de texto (cliente) |
| Prompt eval tok/s | `timings.prompt_per_second` de llama-server |
| Generación tok/s | `timings.predicted_per_second` |
| TPOT | 1 / generación_tok/s (ms/token) |
| Tiempo total | Último chunk − inicio |
| RAM pico | `docker stats` muestreado cada 0.5 s |
| VRAM pico | `nvidia-smi --query-gpu=memory.used --format=csv` |
| Bytes de red | `/sys/class/net/eth0/statistics/{tx,rx}_bytes` antes/después, o `iftop` / `tcpdump` |
| Paquetes perdidos | `tc -s qdisc show` |

Guarda cada corrida en `logs/metricas.jsonl` con: configuración, escenario, repetición, timestamps, métricas y hash del log anterior.

### 9.5 Tabla y gráficos obligatorios

1. Tabla comparativa de las 4 configuraciones × 2 escenarios: TTFT, tok/s, TPOT, RAM, VRAM, bytes, SLO (sí/no).
2. Barras A vs. B para TTFT y tokens/s.
3. Serie temporal de tokens/s o de bytes de red durante una generación.
4. Descomposición de memoria (pesos, KV, runtime, libre) por nodo.
5. Pareto costo por 1M de tokens vs. tokens/s (o vs. TPOT).

---

## 10. Parte 4 — Almacenamiento y memoria (10 puntos)

### Tareas

1. **Tiempo de carga del modelo:**

   ```
   t_descarga = tamaño_modelo / ancho_banda_red
   t_carga = tamaño_shard / ancho_banda_almacenamiento
   t_cold_start ≈ t_carga + t_distribución_RPC
   ```

   Calcula para NVMe, SATA SSD y HDD. Compara con el tiempo medido.
2. **Impacto en TTFT:** mide el primer request después de reiniciar (*cold start*) y compáralo con el segundo (*warm start*). ¿Cuánto del TTFT es carga y cuánto es cómputo?
3. **Contexto máximo real:** calcula `max_ctx` para cada worker y verifica si 4K cabe. Si no, propone: KV en FP8, menos contexto, más RAM o modelo más pequeño.
4. **Costo por GB:** compara NVMe vs. SATA vs. HDD y recomienda el nivel de almacenamiento para el modelo, los logs y los checkpoints.
5. **Concurrencia:** calcula cuántas sesiones de 4K caben en la VRAM/RAM restante. ¿Puedes atender 3 req/s con el contexto completo? Si no, ¿qué sacrificas?

### Evidencia mínima

- Tabla de tiempos calculados vs. medidos.
- Gráfico de cold start vs. warm start.
- Cálculo de `max_ctx` y sesiones concurrentes.

---

## 11. Parte 5 — TCO en COP (20 puntos)

### 11.1 CAPEX

Llena la hoja CAPEX con:

| Ítem | Cantidad | Precio unitario COP | Total COP | Fuente (tienda, URL, fecha) |
|---|---|---|---|---|
| Master | 1 | | | |
| Workers | 3 | | | |
| Switch | 1 | | | |
| Cableado | 1 | | | |
| UPS | 1 | | | |
| Mano de obra | 1 | | | |
| **Total** | | | | |

### 11.2 OPEX

| Concepto | Cálculo | COP/año |
|---|---|---|
| Energía | W × h/día × días/año × COP/kWh / 1000 | |
| Internet | COP/mes × 12 | |
| Mantenimiento | % × CAPEX | |
| Depreciación | CAPEX / vida_útil | |
| **Total** | | |

### 11.3 TCO y costo por token

```
TCO(3 años) = CAPEX + 3 × OPEX_anual
tokens_año = tok/s × 3600 × h/día × días/año × utilización
costo_por_1M = TCO(3 años) / (3 × tokens_año / 1e6)
```

Calcula para tres escenarios de utilización: **25 %, 50 % y 100 %** de la jornada. Explica por qué el costo por token depende de la utilización (y por qué un clúster ocioso es carísimo).

Además, calcula el costo con la **demanda real** (no solo con la capacidad máxima):

```
tokens/año (demanda) = 500 req/día × 300 tokens × 250 días = 37.5 M
```

Compara ese valor con la capacidad máxima del clúster y explica la diferencia. Un clúster que solo usa el 40 % de su capacidad tiene un COP/1M mucho mayor que uno saturado.

### 11.4 Comparación de tres opciones

| Opción | CAPEX | OPEX/año | TCO 3 años | tok/s | COP/1M | Latencia | Privacidad | Riesgo |
|---|---|---|---|---|---|---|---|---|
| A. Clúster 4 nodos (medido) | | | | | | | Sí | |
| B. Servidor GPU único (RTX 4090/3090, 24 GB) | | | | | | | Sí | |
| C. API en la nube | 0 | por uso | por uso | | | | No | |

Para la opción B, puedes medir si tienes la GPU o estimar con roofline; declara cuál usaste. Para la opción C, usa precios actuales de al menos dos proveedores (por ejemplo, DeepSeek, OpenAI, Anthropic o un proveedor local) y cita la fuente y la fecha.

### 11.5 Break-even

1. Grafica costo por 1M de tokens vs. tokens/año para las tres opciones.
2. Calcula el punto de equilibrio:
   - ¿Cuántos tokens/año necesita el clúster para igualar el costo de la API?
   - ¿Es alcanzable con el hardware medido? Si no, dilo claramente.
3. Haz un análisis de sensibilidad (tornado o tabla) para:
   - Precio de la energía (COP 600 / 800 / 1 000 por kWh).
   - Utilización (25 / 50 / 100 %).
   - Throughput (± 30 %).
   - Precio de la API (± 50 %).
4. **Conclusión economics:** ¿el clúster se justifica por costo, por privacidad o por ninguna de las dos? Si la privacidad es obligatoria, compara contra el servidor GPU único, no contra la API.

> **Pista:** un clúster de PCs viejas suele no ser más barato que una API para 7B; el argumento real es soberanía del dato. Si tu conclusión es “no lo construyas; usa una GPU única o la API”, es una respuesta válida si la justificas con números.

---

## 12. Parte 6 — Análisis y preguntas de arquitectura (10 puntos)

Responde con tus datos, no con teoría genérica. Cada respuesta debe citar una tabla, figura o entrada de log.

1. **Cuello de botella A vs. B.** ¿Qué fase se degradó más: prefill (prompt eval) o decode (token a token)? Explica con bytes transferidos y RTT. Si el resultado no coincide con tu intuición, ¿por qué?
2. **Escalabilidad.** Si se añadieran 4 workers más bajo el mismo switch de 1 Gbps, ¿aumentaría la velocidad de generación? Distingue capacidad de memoria (cargar un modelo más grande) de velocidad (tokens/s). Aplica la Ley de Amdahl y el concepto de etapa más lenta.
3. **Pipeline vs. tensor.** ¿Qué técnica usaste? ¿Qué cambiaría con 10 Gbps? Calcula el punto de cruce en el que la red deja de ser el cuello de botella para tu modelo.
4. **Upgrade prioritario.** Con base en tus métricas, ¿qué actualizarías primero: RAM del master, CPUs de los workers, GPUs, switch de 10 Gbps o almacenamiento NVMe? Cuantifica: COP invertidos / reducción de COP por 1M de tokens o / mejora de tok/s. Incluye el costo del upgrade en el TCO.
5. **Viabilidad económica.** ¿El clúster es racional para Andina AI? ¿Bajo qué condiciones (volumen, privacidad, modelo, utilización) sí lo sería? ¿Qué opción recomiendas y por qué?
6. **Validez del experimento.** ¿Qué supuestos del montaje (un solo host, contenedores, red emulada, cuantización) limitan la generalización? ¿Qué medirías en un clúster físico para validar?

---

## 13. Entregables

| Archivo | Contenido |
|---|---|
| `informe.pdf` | 8–12 páginas, con las secciones de la rúbrica, figuras y tablas |
| `codigo/` | `docker-compose.yml`, `Dockerfile`, `tc.sh`, `collect.py`, `config.json` |
| `logs/` | `metricas.jsonl`, logs de llama-server / rpc-server, nvidia-smi, docker stats, tc, iperf3 |
| `costos.xlsx` | CAPEX, OPEX, TCO, comparación, break-even, sensibilidad |
| `video.mp4` | 3–5 min de defensa (opcional pero recomendado) |
| `README.md` | Hardware, versiones, cómo reproducir, qué falló y cómo se resolvió |

### Formato del informe

1. Resumen ejecutivo (máx. 1 página): configuración ganadora, costo/1M, conclusión.
2. Arquitectura y topología (diagrama).
3. Metodología y validez (hardware, versiones, protocolo).
4. Resultados A vs. B (tablas y figuras).
5. Almacenamiento y memoria (cold start, `max_ctx`, concurrencia).
6. Costos en COP y break-even.
7. Análisis, recomendación y riesgos.
8. Anexos: logs, configuraciones, comandos.

---

## 14. Rúbrica (100 puntos + 10 bonus)

### 14.1 Gates eliminatorios (pasan o no)

| Gate | Criterio |
|---|---|
| G1. Topología | 4 nodos en `10.0.50.0/24`, límites de memoria, `rpc-server` y `llama-server` funcionando |
| G2. Partición | Evidencia de shards en ≥2 nodos; el modelo no cabe en un nodo |
| G3. OOM | Prueba de carga completa en un worker con `OOMKilled`/exit 137 y explicación |
| G4. Red | `tc qdisc show` en A y B; `ping`/`iperf3` coherentes |
| G5. Datos crudos | `metricas.jsonl` con timestamps y logs; no se aceptan números sin respaldo |
| G6. Reproducibilidad | README permite repetir al menos una configuración |

Si falla un gate, la parte correspondiente vale 0. Los gates G1–G4 pueden recuperarse en la defensa oral con una demostración en vivo.

### 14.2 Puntos

| Componente | Puntos | Excelente (100 %) | Aceptable (60 %) | Insuficiente (0–30 %) |
|---|---|---|---|---|
| Pre-lab (modelo, memoria, CAPEX) | 5 | Fórmulas correctas, unidades claras, CAPEX con fuentes | Cálculos parciales | Sin pre-lab o incoherente |
| Topología y partición | 15 | Diagrama claro, shards justificados por VRAM, OOM reproducible, logs completos | Topología funciona, pero la partición no está justificada | No se evidencia partición u OOM |
| Red A/B | 15 | `tc` correcto, `iperf3`/`ping` medidos, análisis de jitter/pérdida | Reglas aplicadas, medición parcial | Sin `tc` o sin verificación |
| Métricas | 20 | ≥4 configuraciones × 2 escenarios, 3 reps, mediana/IQR, gráficos claros | Menos configuraciones o sin repeticiones | Métricas inventadas o incompletas |
| Almacenamiento/memoria | 10 | Cold/warm start, `max_ctx`, concurrencia, costo/GB | Cálculos parciales | Sin cálculo o incoherente |
| TCO en COP | 20 | CAPEX/OPEX completos, TCO, costo/1M, break-even, sensibilidad, fuentes | Faltan sensibilidad o fuentes | Sin costos o unidades incorrectas |
| Análisis | 10 | Responde con datos, distingue capacidad/velocidad, propone upgrade cuantificado | Responde genérico | No usa datos |
| Calidad del informe | 5 | Claro, conciso, figuras y tablas bien rotuladas, reproducible | Legible pero desordenado | Incompleto |
| Bonus: rendimiento | +5 | η ≥ 0.70 del roofline | η ≈ 0.50 | η < 0.30 |
| Bonus: costo | +5 | Menor COP/1M entre los que cumplen SLO | En el rango medio | Muy por encima |

### 14.3 Fórmulas de bonificación

**Eficiencia roofline:**

```
techo(B) = min( BW_efectivo / (W + B × KV), Peak_FP / (2N) )
η = tok/s_medido / techo(B)
bonus_rendimiento = 5 × clamp((η − 0.30) / (0.70 − 0.30), 0, 1)
```

- `W` = bytes de pesos; `KV` = bytes de KV por token × contexto; `B` = batch.
- `BW_efectivo` se mide con `iperf3` o con el benchmark de memoria; no se inventa.
- Si `η > 1.05`, revisa unidades o el techo: probablemente hay un error.

**Costo:**

```
bonus_costo = 5 × clamp((C_ref − C_estudiante) / (C_ref − 0.7 × C_ref), 0, 1)
```

- `C_ref` = costo/1M de la configuración de referencia del profesor (Perfil A, 3 workers, 4K).
- Solo se compara entre configuraciones que cumplen el SLO.

---

## 15. Cronograma sugerido (24 h)

| Bloque | Horas | Actividad |
|---|---|---|
| 1 | 0–2 | Leer, elegir perfil, descargar modelo, verificar SHA, llenar CAPEX |
| 2 | 2–4 | Construir imagen, levantar topología, probar RPC |
| 3 | 4–6 | OOM, `nvidia-smi`, `docker stats`, diagrama |
| 4 | 6–8 | `tc` A/B, `ping`, `iperf3`, verificación |
| 5 | 8–12 | Corridas C1–C4 × A/B, recolección de métricas |
| 6 | 12–14 | Almacenamiento, cold start, `max_ctx`, concurrencia |
| 7 | 14–18 | Costos, TCO, break-even, sensibilidad |
| 8 | 18–21 | Gráficos, Pareto, análisis |
| 9 | 21–24 | Informe, video, revisión de gates, buffer |

---

## 16. Anexo A — Formulario

### CPU (CAP 4)

```
CPU_time = IC × CPI × T_ciclo = IC × CPI / f
CPI = CPI_base + stalls_por_instrucción
IPC = 1 / CPI
```

### Pipeline (CAP 4)

```
Aceleración ideal ≈ Nº de etapas
T_pipe = T_no_pipe / Nº de etapas
CPI = CPI_ideal + ciclos_de_stall / instrucción
```

### Jerarquía de memoria (CAP 5)

```
AMAT = Hit_time + Miss_rate × Miss_penalty
CPU_time = (CPU_cycles + Memory_stall_cycles) × T_ciclo
Memory_stall_cycles = (Accesos/programa) × Miss_rate × Miss_penalty
```

### Caché (CAP 5)

```
Nº de conjuntos = Tamaño / (Bloque × Asociatividad)
Bits de índice = log2(Nº de conjuntos)
Bits de offset = log2(Tamaño de bloque)
Bits de tag = Bits de dirección − índice − offset
max_ctx = (RAM_límite − runtime − shard − activaciones) / KV_por_token
```

### LLM (CAP 5/6)

```
Pesos = N × bytes_por_parámetro
KV_por_token = 2 × capas × cabezas_KV × head_dim × bytes_KV
FLOPs_prefill ≈ 2 × N × T_in
FLOPs_decode ≈ 2 × N (por token)
Intensidad_aritmética ≈ 2N / (W + B × KV × T_ctx)
t_prefill ≈ 2 × N × T_in / (η_c × Peak_FP)
t_step ≈ max( (W + B × KV × T_ctx) / BW, 2 × N × B / Peak_FP )
tok/s_total = B / t_step
TPOT = t_step
TTFT ≈ t_cola + t_prefill + t_step/2
```

### Paralelismo (CAP 6)

```
Aceleración (Amdahl) = 1 / [(1 − f) + f / n]
Eficiencia TP ≈ 1 / (1 + c × (n − 1))
Roofline: GFLOP/s = min( BW × AI, Peak_FP )
```

### Costos

```
CAPEX = Σ equipos + cableado + UPS + mano de obra
OPEX/año = energía + internet + mantenimiento + depreciación
TCO(3a) = CAPEX + 3 × OPEX
tokens/año = tok/s × 3600 × h/día × días/año × utilización
COP/1M = TCO(3a) / (3 × tokens/año / 1e6)
```

### Red

```
t_transferencia = bytes / BW
t_total ≈ t_transferencia + saltos × RTT
Bisection BW (anillo) = 2 × BW_enlace
```

---

## 17. Anexo B — Model card resumida (Qwen2.5-7B-Instruct)

| Campo | Valor |
|---|---|
| Arquitectura | Transformer decoder-only, GQA, RoPE, SwiGLU |
| Parámetros | 7.62 B |
| Capas | 28 |
| hidden_size | 3 584 |
| Cabezas de atención | 28 |
| Cabezas KV | 4 |
| head_dim | 128 |
| Vocabulario | 152 064 |
| Contexto | 32 768 |
| Cuantización | Q8_0 (8 bits por peso, bloque 32) |
| Tamaño | ≈ 8.1 GB |
| Licencia | Apache 2.0 |
| Idioma | Multilingüe; buen desempeño en español |

KV/token: 56 KiB (FP16). 4K: 224 MiB. 8K: 448 MiB.

---

## 18. Anexo C — BOM de referencia (a cotizar)

| Ítem | Cant. | COP unitario | COP total |
|---|---|---|---|
| Master: Ryzen 7, 32 GB DDR5, 1 TB NVMe, RTX 3060 8 GB | 1 | 4 500 000 | 4 500 000 |
| Worker: i5-4590, 16 GB DDR3, 512 GB SSD, GTX 1050 Ti 4 GB | 3 | 1 600 000 | 4 800 000 |
| Switch Gigabit 8 puertos | 1 | 150 000 | 150 000 |
| Cableado Cat6 + patch panel | 1 | 120 000 | 120 000 |
| UPS 1000 VA | 1 | 450 000 | 450 000 |
| Mano de obra/ensamble | 1 | 800 000 | 800 000 |
| **CAPEX** | | | **10 820 000** |

| OPEX/año | COP |
|---|---|
| Energía: 750 W × 8 h × 250 × 0.8 / 1000 | 1 200 000 |
| Internet: 120 000 × 12 | 1 440 000 |
| Mantenimiento: 5 % × CAPEX | 541 000 |
| **Total** | **3 181 000** |

**TCO 3 años ≈ COP 20.4 M** (sin valor residual).

Estos valores son referencia; el estudiante debe cotizar y citar fuente. Si no consigue precios locales, use estos y justifique.

---

## 19. Anexo D — docker-compose.yml (resumen)

El archivo completo está en `recursos/docker-compose.yml`. Puntos clave:

- 4 servicios: `master`, `worker-1`, `worker-2`, `worker-3`.
- Red `cluster` con subnet `10.0.50.0/24`.
- `mem_limit` y `memswap_limit` para evitar swap.
- `cap_add: [NET_ADMIN]` para `tc`.
- `deploy.resources.reservations.devices` para GPU (ajusta `device_ids`).
- `volumes: ./models:/models:ro`, `./logs:/logs`.

Comando del master:

```bash
llama-server -m /models/qwen2.5-7b-instruct-q8_0.gguf \
  --rpc worker-1:50052,worker-2:50052,worker-3:50052 \
  --tensor-split 1,1,1 -c 4096 -n 300 \
  --host 0.0.0.0 --port 8080
```

Comando de cada worker:

```bash
rpc-server -H 0.0.0.0 -p 50052
```

---

## 20. Anexo E — tc.sh (resumen)

```bash
#!/usr/bin/env bash
set -euo pipefail
IFACE="${1:-eth0}"
SCENARIO="${2:-A}"
case "$SCENARIO" in
  A) DELAY="0.5ms"; LOSS="0%"; RATE="1000mbit" ;;
  B) DELAY="2ms"; LOSS="0.1%"; RATE="100mbit" ;;
  clear) tc qdisc del dev "$IFACE" root 2>/dev/null || true; exit 0 ;;
  *) echo "Uso: $0 [eth0] [A|B|clear]"; exit 1 ;;
esac
tc qdisc del dev "$IFACE" root 2>/dev/null || true
tc qdisc add dev "$IFACE" root netem delay "$DELAY" loss "$LOSS" rate "$RATE"
tc qdisc show dev "$IFACE"
```

Verifica con `ping` e `iperf3`. Si `netem` no está disponible, usa `netem_proxy.py` (Perfil B). Si el archivo no tiene permiso de ejecución, usa `bash tc.sh`.

---

## 21. Anexo F — collect.py (resumen)

El script:

1. Lee el prompt de `prompt.txt`.
2. Hace un POST streaming a `http://localhost:8080/completion`.
3. Registra `t0`, `t_first`, `t_last`, número de chunks y tiempos.
4. Parsea el bloque `timings` final (`prompt_per_second`, `predicted_per_second`).
5. Escribe una línea JSON en `logs/metricas.jsonl` con la configuración y un hash del registro anterior.

Uso:

```bash
python3 collect.py --label C1-A-r1 --n-predict 300 --out logs/metricas.jsonl
```

---

## 22. Anexo G — Ruta Google Colab / bajo recurso

**Respuesta corta:** Colab no permite el laboratorio completo (no hay Docker con `--privileged`, no hay cgroups de VRAM, y `tc` suele estar bloqueado). Sí permite una versión adaptada:

1. **4 procesos en la misma VM:** `llama-server` + 3 `rpc-server` en `127.0.0.1:50052-50054`.
2. **Límites de RAM** con `ulimit -v` o `prlimit --as` por proceso. Usa `--no-mmap` para que el límite sea efectivo.
3. **Red:** intenta `tc` en `lo`; si falla, usa `netem_proxy.py` para añadir latencia, pérdida y ancho de banda entre el master y cada worker.
4. **Modelo:** Qwen2.5-3B-Instruct Q8_0 (~3.3 GB) con workers de 2 GB → se parte en 2–3.
5. **Baseline:** corre el mismo modelo en la T4 (16 GB) como “servidor GPU único”. Compara latencia, throughput y costo.
6. **OOM:** demuéstralo con `ulimit -v` y el log de “Killed”/`MemoryError`; no con `OOMKilled` de Docker.
7. **Costos:** usa el precio de Colab Pro/GPUs en la nube o el costo de tu laptop; declara el supuesto.

En el Perfil B se evalúa la coherencia del modelo de capacidad y la comparación A/B, no la fidelidad de cgroups/tc. El informe debe declarar esta limitación.

---

## 23. Anexo H — Checklist de entrega

- [ ] `prelab.md` con modelo, memoria y CAPEX.
- [ ] `docker-compose.yml` y `Dockerfile` (o scripts de Colab).
- [ ] Diagrama de topología con IPs y shards.
- [ ] Evidencia de OOM (`OOMKilled`, exit 137, log).
- [ ] `tc qdisc show` en A y B.
- [ ] `ping` e `iperf3` en A y B.
- [ ] ≥4 configuraciones × 2 escenarios × 3 repeticiones.
- [ ] `metricas.jsonl` crudo, sin editar.
- [ ] Tabla comparativa y 5 gráficos obligatorios.
- [ ] Cálculo de `max_ctx` y concurrencia.
- [ ] `costos.xlsx` con CAPEX, OPEX, TCO, comparación y sensibilidad.
- [ ] Break-even y conclusión economics.
- [ ] Respuestas a las 6 preguntas de arquitectura con datos.
- [ ] `README.md` reproducible.
- [ ] Video de 3–5 min (opcional).
- [ ] Declaración de uso de IA.

---

## 24. Anexo I — Integridad académica y uso de IA

- El trabajo es **individual**. Puedes discutir conceptos, pero los datos, el montaje y el informe deben ser tuyos.
- IA permitida para programar, depurar o redactar, **con declaración** de qué se usó y verificación de cada número.
- Los logs deben ser crudos y con timestamps; no se aceptan capturas editadas.
- La defensa oral puede incluir preguntas como: “muéstrame en tus logs por qué el escenario B degradó el prefill”, “calcula el techo roofline de tu configuración”, “¿por qué no usaste tensor parallelism?”.
- Copiar el informe de otro estudiante o inventar métricas implica **anulación**.

---

## 25. Anexo J — Glosario

| Término | Significado |
|---|---|
| TTFT | Time To First Token: tiempo hasta el primer token |
| TPOT | Time Per Output Token: tiempo por token generado |
| Prefill | Fase de procesamiento del prompt (paralelizable, ancho de banda) |
| Decode | Fase autorregresiva, token a token (latencia) |
| KV cache | Caché de claves/valores de atención |
| GQA | Grouped-Query Attention: menos cabezas KV, menos memoria |
| Q8_0 | Cuantización de 8 bits por peso, bloque de 32 |
| Pipeline parallelism | El modelo se corta por capas; cada nodo procesa una etapa |
| Tensor parallelism | Cada capa se divide entre nodos; requiere all-reduce |
| RPC | Remote Procedure Call: llama.cpp reparte el modelo entre procesos |
| Roofline | Modelo de techo: min(BW × AI, Peak_FP) |
| Amdahl | Ley que limita la aceleración por la parte secuencial |
| TCO | Total Cost of Ownership: CAPEX + OPEX a 3 años |
| CAPEX / OPEX | Inversión de capital / gasto operativo |
| Break-even | Punto en que dos opciones cuestan lo mismo |
| Pareto | Frontera de configuraciones no dominadas (costo vs. rendimiento) |
| Cold start | Primera ejecución tras cargar el modelo desde disco |
| Swap | Memoria de intercambio en disco; mala para LLM |

---

## 26. Preguntas frecuentes

**¿Puedo usar una GPU en la nube?**
Sí, si el proveedor permite Docker y `tc` (por ejemplo, una VM Linux con GPU). Incluye el costo de la VM en el TCO y declara la latencia de red del proveedor. Colab no permite el montaje completo; usa el Perfil B.

**¿Puedo usar otro modelo?**
Sí, si cumples la regla de tamaño (no cabe en un nodo) y entregas su model card. Modelos permitidos: Qwen2.5-7B/3B, Mistral-7B-v0.3, Llama-3.1-8B (si tienes acceso). No uses modelos de 70B en el Perfil A.

**¿Qué pasa si mi hardware no tiene GPU?**
Usa el Perfil B (CPU) o el Perfil A con `--n-gpu-layers 0`. El análisis de red y costos sigue siendo válido; el rendimiento absoluto será menor y la bonificación se normaliza por roofline.

**¿Puedo usar vLLM o Exo en vez de llama.cpp?**
Sí, si documentas la equivalencia y puedes demostrar la partición y las métricas. llama.cpp RPC es el camino recomendado por su simplicidad y soporte de GGUF.

**¿Cómo demuestro que el modelo está particionado?**
Con `nvidia-smi` / `docker stats` por nodo, logs de `rpc-server` y la prueba de OOM al cargarlo completo en un solo worker. La suma de shards debe ser ≈ tamaño del modelo.

**¿Qué hago si `tc` no funciona en mi equipo?**
Usa una VM Linux o WSL2; si no, el proxy `netem_proxy.py`. Documenta la limitación y compara A/B con el proxy.

---

*Fin del examen.*

*Examen — Clúster distribuido de inferencia LLM · UTB · Arquitectura de Computadores · 2026*
