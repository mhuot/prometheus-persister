FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc librdkafka-dev libsnappy-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY proto/ proto/
RUN pip install --no-cache-dir grpcio-tools && \
    python -m grpc_tools.protoc \
        -I proto \
        --python_out=prometheus_persister/proto \
        proto/sink-message.proto \
        proto/collectionset.proto \
        proto/remote_write.proto

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends librdkafka1 libsnappy1v5 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY prometheus_persister/ prometheus_persister/
COPY --from=builder /app/prometheus_persister/proto/ prometheus_persister/proto/
COPY config.yaml .

EXPOSE 8000

ENTRYPOINT ["python", "-m", "prometheus_persister"]
