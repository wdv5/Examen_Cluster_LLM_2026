#!/usr/bin/env python3
"""netem_proxy.py — Proxy TCP con latencia, pérdida y ancho de banda.

Alternativa a `tc netem` para Google Colab o entornos sin NET_ADMIN.
No emula paquetes: emula flujos (aplica el retardo por bloque leído).

Uso típico (un proxy por worker):
    python3 netem_proxy.py --listen-port 6001 --target-host 127.0.0.1 \
        --target-port 50052 --delay-ms 2 --loss 0.001 --rate-mbps 100

Luego, en el master:
    llama-server ... --rpc 127.0.0.1:6001,127.0.0.1:6002,127.0.0.1:6003

Escenario A: --delay-ms 0.5 --loss 0 --rate-mbps 1000
Escenario B: --delay-ms 2   --loss 0.001 --rate-mbps 100
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys


class TokenBucket:
    def __init__(self, rate_bps: float):
        self.rate = max(rate_bps, 1.0)
        self.capacity = max(self.rate * 0.05, 65536.0)
        self.tokens = self.capacity
        self.last = asyncio.get_running_loop().time()

    async def consume(self, n: int) -> None:
        while True:
            now = asyncio.get_running_loop().time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= n:
                self.tokens -= n
                return
            await asyncio.sleep((n - self.tokens) / self.rate)


async def pump(reader, writer, bucket, delay_s, loss, label):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            if loss > 0 and random.random() < loss:
                continue
            await bucket.consume(len(data))
            if delay_s > 0:
                await asyncio.sleep(delay_s)
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(client_reader, client_writer, args, up_bucket, down_bucket):
    try:
        target_reader, target_writer = await asyncio.open_connection(
            args.target_host, args.target_port
        )
    except OSError as e:
        print(f"No se pudo conectar a {args.target_host}:{args.target_port}: {e}", file=sys.stderr)
        client_writer.close()
        return

    delay_s = args.delay_ms / 1000.0
    t1 = asyncio.create_task(
        pump(client_reader, target_writer, up_bucket, delay_s, args.loss, "up")
    )
    t2 = asyncio.create_task(
        pump(target_reader, client_writer, down_bucket, delay_s, args.loss, "down")
    )
    await asyncio.gather(t1, t2, return_exceptions=True)


async def main_async(args):
    rate_bps = args.rate_mbps * 1_000_000 / 8.0
    up_bucket = TokenBucket(rate_bps)
    down_bucket = TokenBucket(rate_bps)

    server = await asyncio.start_server(
        lambda r, w: handle(r, w, args, up_bucket, down_bucket),
        host=args.listen_host,
        port=args.listen_port,
    )
    addr = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(
        f"Proxy {addr} -> {args.target_host}:{args.target_port} "
        f"| delay={args.delay_ms} ms | loss={args.loss} | rate={args.rate_mbps} Mbps"
    )
    async with server:
        await server.serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen-host", default="0.0.0.0")
    ap.add_argument("--listen-port", type=int, required=True)
    ap.add_argument("--target-host", default="127.0.0.1")
    ap.add_argument("--target-port", type=int, required=True)
    ap.add_argument("--delay-ms", type=float, default=0.0)
    ap.add_argument("--loss", type=float, default=0.0, help="fracción, ej. 0.001 = 0.1%")
    ap.add_argument("--rate-mbps", type=float, default=100.0)
    args = ap.parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("Detenido")


if __name__ == "__main__":
    main()
