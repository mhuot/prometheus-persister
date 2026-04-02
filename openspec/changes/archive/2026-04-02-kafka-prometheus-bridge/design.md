## Context

Delta-V Delta-V Minions collect performance metrics (SNMP, WMI, etc.) and publish them as protobuf-encoded `CollectionSet` messages to Kafka via the Sink IPC mechanism. The messages are wrapped in a `SinkMessage` envelope that supports chunking for large payloads. Currently there is no Python-based consumer to bridge these metrics into Prometheus-compatible stores.

This project creates a standalone Python service (`prometheus-persister`) that consumes from Kafka, deserializes the protobuf payloads, maps Delta-V resource hierarchies to flat OTel-conformant Prometheus labels, and pushes metrics via Remote-Write.

## Goals / Non-Goals

**Goals:**
- Standalone Python service deployable via Docker, independent of the Delta-V Java stack.
- Consume `CollectionSet` messages from `Delta-V.Sink.CollectionSet` topic.
- Handle `SinkMessage` chunked envelope reassembly.
- Transform all four resource types (Node, Interface, GenericType, ResponseTime) to Prometheus labels following OTel semantic conventions.
- Push metrics via Prometheus Remote-Write (protobuf + snappy) with batching and retry.
- YAML-based configuration for Kafka, Remote-Write, and label mapping.
- Operational observability via OpenTelemetry SDK: metrics (Prometheus exporter + optional OTLP), distributed traces for the consume→transform→write pipeline, and structured logging.

**Non-Goals:**
- Telemetryd / `Delta-V.Sink.Telemetry` topic consumption (out of scope).
- Local metric storage within the service.
- A Prometheus scrape endpoint for the *collected* Delta-V metrics.
- Custom relabeling or filtering rules (future enhancement).
- HA leader election — horizontal scaling is handled by Kafka consumer groups.

## Decisions

### 1. Python with confluent-kafka
- **Decision**: Use `confluent-kafka` (librdkafka wrapper) for Kafka consumption.
- **Rationale**: Production-grade, widely deployed, supports consumer groups natively. Better performance than `kafka-python` for high-throughput scenarios.
- **Alternatives**: `kafka-python` (pure Python, simpler but slower), `aiokafka` (async, adds complexity without clear benefit for this batch-oriented workload).

### 2. Protobuf code generation with grpcio-tools
- **Decision**: Generate Python bindings from the Delta-V `.proto` files using `grpc_tools.protoc`.
- **Rationale**: Ensures type-safe parsing of `SinkMessage`, `CollectionSet`, and related messages. Proto files are copied from Delta-V and versioned in this repo.
- **Alternatives**: Manual binary parsing (fragile, error-prone).

### 3. SinkMessage chunk reassembly
- **Decision**: Implement a simple in-memory chunk buffer keyed by `message_id`, emitting the complete payload when `current_chunk_number == total_chunks`.
- **Rationale**: The SinkMessage envelope supports splitting large payloads across multiple Kafka messages. Most CollectionSet messages fit in a single chunk, but the reassembly logic is required for correctness.
- **Trade-off**: Memory usage scales with number of in-flight chunked messages. A TTL-based eviction prevents unbounded growth.

### 4. OTel-conformant label mapping
- **Decision**: Map Delta-V resource metadata to Prometheus labels using OpenTelemetry semantic conventions.
- **Mapping**:
  | Delta-V Field | Prometheus Label | OTel Convention |
  |---|---|---|
  | `node_id` | `host_id` | `host.id` |
  | `node_label` | `host_name` | `host.name` |
  | `foreign_source` | `deltav_foreign_source` | custom |
  | `foreign_id` | `deltav_foreign_id` | custom |
  | `location` | `deltav_location` | `deltav.location` |
  | `resource_id` | `deltav_resource_id` | `deltav.resource.id` |
  | `if_index` | `deltav_if_index` | custom |
  | `instance` | `deltav_instance` | custom |
  | `resource_type_name` | `deltav_resource_type` | custom |
- **Note**: Prometheus label names use underscores (dots are invalid). OTel conventions use dots — we store the underscore form as the label name with the OTel convention documented.
- **Rationale**: Interoperability with modern observability tools. Consistent with OTel resource attributes.

### 5. Remote-Write implementation
- **Decision**: Implement Remote-Write v1 using raw protobuf serialization + snappy compression, posting to the configured endpoint.
- **Rationale**: The Remote-Write protocol is a simple HTTP POST of snappy-compressed protobuf. Using the raw protocol avoids heavyweight dependencies and gives full control over batching.
- **Libraries**: `protobuf` for serialization, `python-snappy` for compression, `requests` for HTTP.
- **Alternatives**: `prometheus-client` (focused on exposition, not remote-write), `prometheus-remote-write` (limited maintenance).

### 6. Batching strategy
- **Decision**: Accumulate metrics in memory and flush when either a batch size limit or a time interval is reached, whichever comes first.
- **Rationale**: Balances latency (time-based flush) with throughput (size-based flush). Configurable via YAML.
- **Defaults**: 1000 samples or 5 seconds.

### 7. Configuration via YAML + environment overrides
- **Decision**: Primary config via `config.yaml`, with environment variable overrides for deployment flexibility (e.g., `KAFKA_BOOTSTRAP_SERVERS`).
- **Rationale**: YAML is human-readable for local development; env vars are standard for containerized deployments.

### 8. OpenTelemetry for self-observability
- **Decision**: Use the OpenTelemetry Python SDK (`opentelemetry-api`, `opentelemetry-sdk`) for the service's own operational telemetry — metrics, traces, and structured logs.
- **Rationale**: OTel is the industry standard for application observability. Using it for the persister's own instrumentation (not to be confused with the OTel label conventions used for the *forwarded* metrics) provides a consistent, vendor-neutral observability stack. The OTel Prometheus exporter serves a `/metrics` scrape endpoint, while the optional OTLP exporter can send telemetry to any OTel-compatible backend (Grafana Alloy, Jaeger, etc.).
- **Metrics**: Use OTel `Meter` to record counters (`messages_consumed`, `samples_written`, `write_errors`, `chunk_reassembly_timeouts`), histograms (`write_latency`, `transform_duration`, `batch_size`), and up/down counters (`kafka_lag`, `inflight_chunks`).
- **Traces**: Create spans for key operations — `consume_message`, `reassemble_chunks`, `transform_collectionset`, `remote_write_batch`. Propagate a single trace per message through the pipeline to enable latency debugging.
- **Logs**: Use Python `logging` with the OTel log bridge (`opentelemetry-sdk` log provider) so logs are correlated with trace/span IDs automatically.
- **Exporters**: Prometheus exporter (default, serves `/metrics` on port 8000) for metrics scraping. Optional OTLP exporter for metrics, traces, and logs when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- **Alternatives**: Raw `prometheus-client` (metrics only, no traces/logs correlation), custom logging (no trace correlation).

### 9. Project structure
- **Decision**: Single Python package `prometheus_persister` with modules for each concern.
- **Structure**:
  ```
  prometheus-persister/
  ├── config.yaml
  ├── pyproject.toml
  ├── proto/                    # Copied .proto files
  ├── prometheus_persister/
  │   ├── __init__.py
  │   ├── main.py              # Entry point
  │   ├── config.py            # Config loading
  │   ├── consumer.py          # Kafka consumer + chunk reassembly
  │   ├── transformer.py       # CollectionSet → Prometheus samples
  │   ├── remote_writer.py     # Remote-Write client
  │   ├── observability.py     # OTel SDK setup (meter, tracer, log provider)
  │   └── proto/               # Generated protobuf bindings
  ├── tests/
  └── Dockerfile
  ```

## Risks / Trade-offs

- **[Risk] High cardinality from resource IDs** → Delta-V `resource_id` values can be long and unique. Mitigation: Document label cardinality considerations; future enhancement for optional label filtering.
- **[Risk] Chunk reassembly memory** → Large or stalled chunked messages consume memory. Mitigation: TTL-based eviction (default 60s) for incomplete chunk buffers.
- **[Risk] Remote-Write backpressure** → If the Prometheus endpoint is slow, the Kafka consumer will lag. Mitigation: Configurable batch size, timeout, and retry with exponential backoff. Kafka consumer group rebalancing handles prolonged failures.
- **[Risk] Proto schema drift** → Delta-V proto files may change across versions. Mitigation: Pin proto files in this repo with version tracking; regenerate bindings as needed.
- **[Risk] Metric type mapping** → Delta-V `COUNTER` type maps to Prometheus counter, but Remote-Write sends raw values without `_total` suffix conventions. Mitigation: Append `_total` suffix for counter-type metrics and document the convention.
