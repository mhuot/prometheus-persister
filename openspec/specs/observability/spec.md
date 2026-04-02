## ADDED Requirements

### Requirement: OTel SDK initialization
The system SHALL initialize OpenTelemetry `MeterProvider`, `TracerProvider`, and `LoggerProvider` at startup with `service.name` set to `prometheus-persister`.

#### Scenario: Default startup with Prometheus exporter
- **WHEN** the service starts without `OTEL_EXPORTER_OTLP_ENDPOINT` set
- **THEN** the system SHALL initialize OTel with a Prometheus metric exporter serving `/metrics` on the configured port (default: 8000), and a no-op trace exporter

#### Scenario: Startup with OTLP endpoint configured
- **WHEN** the service starts with `OTEL_EXPORTER_OTLP_ENDPOINT` set
- **THEN** the system SHALL initialize OTel with both the Prometheus metric exporter AND OTLP exporters for metrics, traces, and logs

### Requirement: OTel operational counters
The system SHALL record OTel counters for key operational events.

#### Scenario: Message consumption counted
- **WHEN** a Kafka message is successfully consumed and parsed
- **THEN** the `prometheus_persister.messages_consumed` counter SHALL be incremented

#### Scenario: Samples written counted
- **WHEN** a Remote-Write batch is successfully sent
- **THEN** the `prometheus_persister.samples_written` counter SHALL be incremented by the number of samples in the batch

#### Scenario: Write errors counted
- **WHEN** a Remote-Write request fails after all retries
- **THEN** the `prometheus_persister.write_errors` counter SHALL be incremented

#### Scenario: Chunk reassembly timeouts counted
- **WHEN** an incomplete chunked message is evicted due to TTL expiry
- **THEN** the `prometheus_persister.chunk_reassembly_timeouts` counter SHALL be incremented

### Requirement: OTel operational histograms
The system SHALL record OTel histograms for latency and batch size distributions.

#### Scenario: Write latency recorded
- **WHEN** a Remote-Write HTTP request completes (success or failure)
- **THEN** the `prometheus_persister.write_latency` histogram SHALL record the request duration in seconds

#### Scenario: Transform duration recorded
- **WHEN** a CollectionSet is transformed into Prometheus samples
- **THEN** the `prometheus_persister.transform_duration` histogram SHALL record the transformation duration in seconds

#### Scenario: Batch size recorded
- **WHEN** a batch is flushed via Remote-Write
- **THEN** the `prometheus_persister.batch_size` histogram SHALL record the number of samples in the batch

### Requirement: OTel operational gauges
The system SHALL record OTel up/down counters for instantaneous state.

#### Scenario: Inflight chunks tracked
- **WHEN** a chunk is added to or removed from the reassembly buffer
- **THEN** the `prometheus_persister.inflight_chunks` up/down counter SHALL reflect the current number of incomplete chunked messages

### Requirement: Distributed trace spans
The system SHALL create OTel spans for the consume→transform→write pipeline.

#### Scenario: Consume span
- **WHEN** a Kafka message is polled
- **THEN** a span named `consume_message` SHALL be created with attributes `messaging.system`, `messaging.destination.name`, and `messaging.kafka.message.offset`

#### Scenario: Reassembly span
- **WHEN** a multi-chunk message completes reassembly
- **THEN** a span named `reassemble_chunks` SHALL be created with attributes `messaging.message_id` and `chunks.total`

#### Scenario: Transform span
- **WHEN** a CollectionSet is transformed
- **THEN** a child span named `transform_collectionset` SHALL be created with attributes `collectionset.resource_count` and `collectionset.sample_count`

#### Scenario: Write span
- **WHEN** a batch is flushed
- **THEN** a child span named `remote_write_batch` SHALL be created with attributes `batch.size` and `http.response.status_code`, and span status set to ERROR on failure

### Requirement: Log-trace correlation
The system SHALL correlate Python log records with active OTel trace context.

#### Scenario: Log within active span
- **WHEN** a log message is emitted while an OTel span is active
- **THEN** the log record SHALL include `trace_id` and `span_id` fields

#### Scenario: JSON structured logging
- **WHEN** the service emits log output
- **THEN** logs SHALL be formatted as JSON with fields: `timestamp`, `level`, `message`, `logger`, `trace_id`, `span_id`
