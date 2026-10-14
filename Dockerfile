FROM node:26.11.1-bookworm-slim@sha256:86f07bc9c5dce4578cf37e5a418b7bfc7f817cda25cde66e2b66e95ed86c4567 AS frontend
WORKDIR /app/web
RUN npm install --global npm@12.2.0
COPY web/package.json web/package-lock.json web/.npmrc ./
RUN npm ci
COPY web/ ./
COPY contract/ /app/contract/
COPY docs/ /app/docs/
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.0@sha256:cdc6093146eb3ff6a40107b38f008b789e050e77ad87865e381d9917da55a168 AS uv

FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS backend
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TORCH_HOME=/app/models/torch \
    UV_CACHE_DIR=/app/.cache/uv \
    UV_PYTHON_DOWNLOADS=never
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg espeak-ng curl ca-certificates libgomp1 libsndfile1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock .python-version README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/ src/
COPY contract/ contract/
RUN uv sync --locked --no-dev
ARG MMS_MODEL_URL=https://dl.fbaipublicfiles.com/mms/torchaudio/ctc_alignment_mling_uroman/model.pt
ARG MMS_MODEL_SHA256=20ef12963ab4924bef49ac4fc7f58ad5da2ee43b2c11bc8c853c9b90ecdbc680
RUN mkdir -p "$TORCH_HOME/hub/checkpoints" \
    && curl --fail --location --retry 3 "$MMS_MODEL_URL" \
       --output "$TORCH_HOME/hub/checkpoints/model.pt.download" \
    && printf '%s  %s\n' "$MMS_MODEL_SHA256" "$TORCH_HOME/hub/checkpoints/model.pt.download" \
       | sha256sum --check \
    && mv "$TORCH_HOME/hub/checkpoints/model.pt.download" "$TORCH_HOME/hub/checkpoints/model.pt"
COPY data/dataset/manifest.json data/dataset/calibration.json data/dataset/README.md data/dataset/
COPY data/dataset/LICENSE data/dataset/LICENSE
ARG DATASET_URL=https://github.com/opx0/speech-delivery-flaw-detector/releases/download/dataset-v1/speech_delivery_dataset_v1.tar.gz
ARG DATASET_SHA256=ca5c16fa9f0503c9f13b60dfdb1f0f2f5322581ff7a51a2bb3e111d91a0cb6da
RUN curl --fail --location --retry 3 "$DATASET_URL" --output /tmp/dataset.tar.gz \
    && printf '%s  %s\n' "$DATASET_SHA256" /tmp/dataset.tar.gz | sha256sum --check \
    && tar -xzf /tmp/dataset.tar.gz -C data dataset/audio \
    && rm /tmp/dataset.tar.gz
COPY --from=frontend /app/web/dist/ web/dist/
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD .venv/bin/python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/library', timeout=3).close()"
CMD [".venv/bin/python", "-m", "speech_delivery.api", "--data", "data/dataset", "--calibration", "data/dataset/calibration.json", "--web", "web/dist", "--host", "0.0.0.0", "--port", "8000"]

FROM backend AS cuda
RUN uv pip install --python /app/.venv/bin/python --reinstall-package torch \
    --reinstall-package torchaudio --index-url https://download.pytorch.org/whl/cu124 \
    torch==2.6.0+cu124 torchaudio==2.6.0+cu124
ENV SPEECH_DEVICE=cuda \
    CUBLAS_WORKSPACE_CONFIG=:4096:8

FROM backend AS runtime
