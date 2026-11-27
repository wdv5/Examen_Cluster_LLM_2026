# syntax=docker/dockerfile:1
#
# Imagen base para el examen de clúster LLM.
# Compila llama.cpp con RPC y CUDA.
#
# Uso:
#   docker build -t llm-cluster:2026 \
#     --build-arg LLAMA_CPP_REF=<commit> \
#     --build-arg CUDA_ARCHS="61;86;89" .
#
# IMPORTANTE: anota el commit usado en el informe. "master" no es reproducible.

FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda

RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake build-essential libcurl4-openssl-dev \
    iproute2 iputils-ping iperf3 jq curl ca-certificates \
    python3 python3-pip procps psmisc \
    && rm -rf /var/lib/apt/lists/*

# Arquitecturas CUDA: 61 = GTX 1050 Ti, 86 = RTX 3060, 89 = RTX 4090.
# Ajusta según tu hardware. Si no sabes, usa "native" (solo funciona con GPU en build).
ARG CUDA_ARCHS="61;86;89"

# Fija un commit/tag de llama.cpp para reproducibilidad.
ARG LLAMA_CPP_REF=master

RUN git clone https://github.com/ggerganov/llama.cpp /opt/llama.cpp \
    && cd /opt/llama.cpp \
    && git checkout "${LLAMA_CPP_REF}" \
    && cmake -B build \
        -DGGML_CUDA=ON \
        -DGGML_RPC=ON \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHS}" \
    && cmake --build build -j"$(nproc)" \
    && git rev-parse HEAD > /opt/llama.cpp/COMMIT.txt

ENV PATH="/opt/llama.cpp/build/bin:${PATH}"
WORKDIR /workspace

# Binarios esperados:
#   /opt/llama.cpp/build/bin/llama-server
#   /opt/llama.cpp/build/bin/llama-cli
#   /opt/llama.cpp/build/bin/rpc-server

CMD ["/bin/bash"]
