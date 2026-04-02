ARG VERSION=dev
ARG BUILD_DATE=unknown
ARG REVISION=unknown
ARG SOURCE=https://github.com/mhuot/prometheus-persister
ARG BUILD_BRANCH=unknown

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
    apt-get install -y --no-install-recommends librdkafka1 libsnappy1v5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -g 10001 persister && \
    useradd -u 10001 -g persister -s /sbin/nologin -M persister

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY entrypoint.sh .
COPY prometheus_persister/ prometheus_persister/
COPY --from=builder /app/prometheus_persister/proto/ prometheus_persister/proto/
COPY config.yaml .

ARG VERSION
ARG BUILD_DATE
ARG REVISION
ARG SOURCE
ARG BUILD_BRANCH

LABEL org.opencontainers.image.title="prometheus-persister" \
      org.opencontainers.image.description="Delta-V Kafka to Prometheus bridge via Remote-Write" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.source="${SOURCE}" \
      org.opencontainers.image.vendor="Delta-V" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opennms.cicd.branch="${BUILD_BRANCH}"

USER persister

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=30s \
    CMD curl -sf http://localhost:8000/metrics || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
