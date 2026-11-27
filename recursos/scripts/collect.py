#!/usr/bin/env python3
"""collect.py — Recolecta métricas de una corrida de llama-server.

Hace un POST streaming a /completion, mide TTFT, tokens/s y guarda una
línea JSON en logs/metricas.jsonl con un hash encadenado.

Uso:
    python3 collect.py --label C1-A-r1 --n-predict 300 \
        --prompt-file prompt.txt --out logs/metricas.jsonl

Requiere solo la biblioteca estándar (urllib, json, hashlib).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_prev_hash(path: str) -> str:
    if not os.path.exists(path):
        return "0" * 64
    last = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    return sha256_text(last) if last else "0" * 64


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080/completion")
    ap.add_argument("--prompt-file", default="prompt.txt")
    ap.add_argument("--label", default="run")
    ap.add_argument("--n-predict", type=int, default=300)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--out", default="logs/metricas.jsonl")
    ap.add_argument("--extra", default="{}", help="JSON con config/escenario")
    args = ap.parse_args()

    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    payload = {
        "prompt": prompt,
        "n_predict": args.n_predict,
        "temperature": args.temperature,
        "seed": args.seed,
        "stream": True,
        "stop": ["</s>"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        args.url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    t_first = None
    t_last = None
    n_chunks = 0
    text_parts: list[str] = []
    timings = {}
    raw_last = None

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line in ("[DONE]", "data: [DONE]"):
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                raw_last = obj
                if "timings" in obj:
                    timings = obj["timings"]

                content = obj.get("content", "")
                if content:
                    now = time.perf_counter()
                    if t_first is None:
                        t_first = now
                    t_last = now
                    n_chunks += 1
                    text_parts.append(content)

                if obj.get("stop"):
                    break
    except urllib.error.URLError as e:
        print(f"ERROR de red: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrumpido", file=sys.stderr)
        return 130

    t_end = time.perf_counter()
    if t_first is None:
        print("No se recibió ningún token", file=sys.stderr)
        return 3

    n_tokens = int(timings.get("predicted_n") or n_chunks)
    predicted_ms = float(timings.get("predicted_ms") or 0.0)
    prompt_ms = float(timings.get("prompt_ms") or 0.0)
    prompt_tps = float(timings.get("prompt_per_second") or 0.0)
    gen_tps = float(timings.get("predicted_per_second") or 0.0)
    if not gen_tps and predicted_ms > 0:
        gen_tps = 1000.0 * n_tokens / predicted_ms

    ttft_ms = (t_first - t0) * 1000.0
    total_ms = (t_end - t0) * 1000.0
    tpot_ms = ((t_last - t_first) * 1000.0 / max(1, n_tokens - 1)) if n_tokens > 1 else 0.0

    extra = json.loads(args.extra)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": args.label,
        "scenario": extra.get("scenario"),
        "config": extra.get("config", {}),
        "host": extra.get("host", {}),
        "prompt_chars": len(prompt),
        "n_predict": args.n_predict,
        "n_tokens": n_tokens,
        "ttft_ms": round(ttft_ms, 2),
        "total_ms": round(total_ms, 2),
        "tpot_ms": round(tpot_ms, 2),
        "prompt_ms": round(prompt_ms, 2),
        "prompt_tps": round(prompt_tps, 2),
        "gen_tps": round(gen_tps, 2),
        "timings": timings,
        "text_sample": "".join(text_parts)[:200],
        "prev_hash": read_prev_hash(args.out),
    }
    record["hash"] = sha256_text(json.dumps(record, sort_keys=True, ensure_ascii=False))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(
        f"{args.label}: TTFT={record['ttft_ms']} ms | "
        f"gen={record['gen_tps']} tok/s | "
        f"TPOT={record['tpot_ms']} ms | "
        f"tokens={n_tokens} | total={record['total_ms']} ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
