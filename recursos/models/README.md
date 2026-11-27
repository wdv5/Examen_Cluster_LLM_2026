# Modelos

Coloca aquí el archivo GGUF. **No lo versiones** (pesa varios GB).

Perfil A:

```bash
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
  qwen2.5-7b-instruct-q8_0.gguf --local-dir .
```

Perfil B:

```bash
huggingface-cli download Qwen/Qwen2.5-3B-Instruct-GGUF \
  qwen2.5-3b-instruct-q8_0.gguf --local-dir .
```

Verifica:

```bash
ls -lh
sha256sum *.gguf
```

Anota el tamaño y el SHA-256 en el informe. Si el archivo viene dividido, únelo con:

```bash
llama-gguf-split --merge qwen2.5-7b-instruct-q8_0-00001-of-00002.gguf qwen2.5-7b-instruct-q8_0.gguf
```
