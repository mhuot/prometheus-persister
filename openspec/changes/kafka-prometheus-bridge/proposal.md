## Why

Delta-V Delta-V publishes performance metrics collected by Minions to Kafka topics using the Sink IPC mechanism. There is no lightweight, standalone bridge to persist these metrics into a Prometheus-compatible store (Mimir, VictoriaMetrics, Prometheus). This project creates a Python-based Kafka-to-Prometheus bridge that consumes CollectionSet messages and pushes them via Remote-Write, enabling modern observability stacks to store and query Delta-V metrics in real-time.

## What Changes

- **New standalone Python service**: `prometheus-persister` — consumes Delta-V CollectionSet protobuf messages from Kafka and writes them to Prometheus via Remote-Write.
- **Protobuf parsing**: Deserializes `SinkMessage` envelopes and inner `CollectionSet` payloads using generated Python protobuf bindings.
- **OTel-conformant label mapping**: Transforms Delta-V hierarchical resources (Node, Interface, GenericType, ResponseTime) into flat Prometheus labels following OpenTelemetry semantic conventions.
- **Batched Remote-Write**: Accumulates metrics and pushes them in batches to a configurable Prometheus-compatible endpoint.
- **Configuration**: YAML-based configuration for Kafka brokers, consumer group, Remote-Write endpoint, authentication, and batching parameters.

## Capabilities

### New Capabilities
- `kafka-consumer`: Kafka consumer subscribing to `Delta-V.Sink.CollectionSet` topic, parsing SinkMessage envelopes and reassembling chunked messages.
- `metric-transformer`: Transforms Delta-V CollectionSet protobuf resources and numeric attributes into Prometheus time-series with OTel-conformant labels.
- `remote-writer`: Batches and pushes Prometheus samples to a Remote-Write endpoint with retry and backpressure handling.
- `observability`: OpenTelemetry-instrumented self-observability — metrics, traces, and structured logging for the persister's own operations.

### Modified Capabilities
_(none — greenfield project)_

## Impact

- **New dependencies**: `confluent-kafka`, `protobuf`, `python-snappy`, `requests`, `pyyaml`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-prometheus`, `opentelemetry-exporter-otlp`.
- **Infrastructure**: Requires access to the Kafka cluster used by Delta-V and a Prometheus-compatible Remote-Write endpoint.
- **Proto compilation**: Requires generating Python bindings from the Delta-V `.proto` files (`sink-message.proto`, `collectionset.proto`).
