## 1. Project Setup

- [ ] 1.1 Initialize Python project with `pyproject.toml`, define dependencies (`confluent-kafka`, `protobuf`, `python-snappy`, `requests`, `pyyaml`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-prometheus`, `opentelemetry-exporter-otlp`, `python-json-logger`), and create virtual environment
- [ ] 1.2 Copy `.proto` files from delta-v (`sink-message.proto`, `collectionset.proto`) into `proto/` directory and add Remote-Write `types.proto` for WriteRequest
- [ ] 1.3 Generate Python protobuf bindings from `.proto` files into `prometheus_persister/proto/`
- [ ] 1.4 Create package structure: `prometheus_persister/` with `__init__.py`, `main.py`, `config.py`, `consumer.py`, `transformer.py`, `remote_writer.py`, `observability.py`
- [ ] 1.5 Create default `config.yaml` with documented configuration options for Kafka, Remote-Write, and batching
- [ ] 1.6 Create `Dockerfile` for containerized deployment

## 2. Configuration

- [ ] 2.1 Implement `config.py` — load YAML config with environment variable overrides for Kafka bootstrap servers, consumer group, Remote-Write URL, auth, batch size, and flush interval
- [ ] 2.2 Add config validation: require Kafka bootstrap servers and Remote-Write URL, validate types and ranges

## 3. Kafka Consumer

- [ ] 3.1 Implement Kafka consumer in `consumer.py` — connect to Kafka, subscribe to `OpenNMS.Sink.CollectionSet` topic, poll messages in a loop
- [ ] 3.2 Implement `SinkMessage` envelope parsing — deserialize protobuf, extract content bytes for single-chunk messages
- [ ] 3.3 Implement chunk reassembly buffer — in-memory dict keyed by `message_id`, concatenate content when all chunks arrive, TTL-based eviction for stale entries
- [ ] 3.4 Implement offset management — commit offsets after metrics are accepted into the batch buffer
- [ ] 3.5 Implement graceful shutdown — handle SIGTERM/SIGINT, stop polling, flush batches, commit offsets

## 4. Metric Transformer

- [ ] 4.1 Implement `CollectionSet` deserialization in `transformer.py` — parse raw bytes into `CollectionSet` protobuf
- [ ] 4.2 Implement `NodeLevelResource` label mapping — `node_id` → `host_id`, `node_label` → `host_name`, `location` → `deltav_location`, `foreign_source`/`foreign_id` labels
- [ ] 4.3 Implement `InterfaceLevelResource` label mapping — parent node labels plus `deltav_instance`, `deltav_if_index`
- [ ] 4.4 Implement `GenericTypeResource` label mapping — parent node labels plus `deltav_resource_type`, `deltav_instance`
- [ ] 4.5 Implement `ResponseTimeResource` label mapping — `deltav_instance`, `deltav_location`
- [ ] 4.6 Implement resource-level metadata labels — `deltav_resource_id`, `deltav_resource_type` from `CollectionSetResource` fields
- [ ] 4.7 Implement metric name sanitization — replace invalid Prometheus characters with underscores, prepend group name, append `_total` for counters
- [ ] 4.8 Implement metric value handling — prefer `metric_value` wrapper over `value` field, use `CollectionSet.timestamp` for sample timestamps

## 5. Remote-Write Client

- [ ] 5.1 Implement batch buffer in `remote_writer.py` — accumulate samples, flush on batch size or time interval
- [ ] 5.2 Implement Remote-Write serialization — build `WriteRequest` protobuf, compress with Snappy, POST with correct headers
- [ ] 5.3 Implement retry logic — exponential backoff for 5xx and timeouts, respect `Retry-After` for 429, no retry for 4xx
- [ ] 5.4 Implement authentication — Basic auth and Bearer token support from config

## 6. Observability (OpenTelemetry)

- [ ] 6.1 Implement `observability.py` — initialize OTel `MeterProvider` with Prometheus exporter (serves `/metrics` on configurable port) and optional OTLP exporter when `OTEL_EXPORTER_OTLP_ENDPOINT` is set
- [ ] 6.2 Implement OTel `TracerProvider` setup — configure with OTLP span exporter (when endpoint set) and `service.name` resource attribute; create a module-level tracer for the package
- [ ] 6.3 Implement structured logging with OTel log bridge — configure Python `logging` with JSON formatter (`python-json-logger`), attach OTel `LoggerProvider` so logs include `trace_id` and `span_id`
- [ ] 6.4 Create OTel metrics instruments — counters (`messages_consumed`, `samples_written`, `write_errors`, `chunk_reassembly_timeouts`), histograms (`write_latency`, `transform_duration`, `batch_size`), up/down counters (`inflight_chunks`)
- [ ] 6.5 Instrument `consumer.py` with OTel — add `consume_message` and `reassemble_chunks` spans with Kafka attributes, increment `messages_consumed` counter
- [ ] 6.6 Instrument `transformer.py` with OTel — add `transform_collectionset` span with `resource_count`/`sample_count` attributes, record `transform_duration` histogram
- [ ] 6.7 Instrument `remote_writer.py` with OTel — add `remote_write_batch` span with `batch.size` and `http.response.status_code` attributes, record `write_latency` histogram and `samples_written`/`write_errors` counters

## 7. Entry Point and Integration

- [ ] 7.1 Implement `main.py` — load config, initialize OTel providers via `observability.py`, wire consumer → transformer → remote-writer pipeline, start consumer loop
- [ ] 7.2 Add signal handling in main — register SIGTERM/SIGINT handlers for graceful shutdown

## 8. Testing

- [ ] 8.1 Unit tests for `transformer.py` — test all four resource types, metric name sanitization, value handling, timestamp conversion
- [ ] 8.2 Unit tests for `consumer.py` — test SinkMessage parsing, chunk reassembly, TTL eviction
- [ ] 8.3 Unit tests for `remote_writer.py` — test batch triggering, serialization, retry logic
- [ ] 8.4 Integration test — end-to-end with mock Kafka producer and mock Remote-Write HTTP server
