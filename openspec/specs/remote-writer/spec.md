## ADDED Requirements

### Requirement: Batch accumulation
The system SHALL accumulate Prometheus samples in an internal buffer and flush when either the configured batch size or time interval is reached, whichever comes first.

#### Scenario: Batch size trigger
- **WHEN** the buffer reaches the configured maximum batch size (default: 1000 samples)
- **THEN** the system SHALL immediately flush the buffer via Remote-Write

#### Scenario: Time interval trigger
- **WHEN** the configured flush interval (default: 5 seconds) elapses since the last flush
- **THEN** the system SHALL flush the current buffer contents via Remote-Write, even if the batch size has not been reached

#### Scenario: Empty buffer at interval
- **WHEN** the flush interval elapses and the buffer is empty
- **THEN** the system SHALL NOT send an empty Remote-Write request

### Requirement: Remote-Write protocol
The system SHALL send metrics using the Prometheus Remote-Write v1 protocol: protobuf-serialized `WriteRequest` compressed with Snappy, sent as an HTTP POST with `Content-Type: application/x-protobuf` and `Content-Encoding: snappy`.

#### Scenario: Successful write
- **WHEN** a batch is flushed to the Remote-Write endpoint
- **THEN** the system SHALL serialize the samples as a `WriteRequest` protobuf, compress with Snappy, and POST to the configured URL

#### Scenario: Response validation
- **WHEN** the Remote-Write endpoint returns HTTP 200 or 204
- **THEN** the system SHALL consider the write successful and clear the batch

### Requirement: Retry on transient failure
The system SHALL retry failed Remote-Write requests with exponential backoff for transient errors.

#### Scenario: Server error (5xx)
- **WHEN** the Remote-Write endpoint returns a 5xx status code
- **THEN** the system SHALL retry the request up to 3 times (configurable) with exponential backoff starting at 1 second

#### Scenario: Network timeout
- **WHEN** the Remote-Write request times out (default: 30 seconds)
- **THEN** the system SHALL retry with the same exponential backoff policy

#### Scenario: Client error (4xx)
- **WHEN** the Remote-Write endpoint returns a 4xx status code (except 429)
- **THEN** the system SHALL NOT retry, log the error with response body, and discard the batch

#### Scenario: Rate limiting (429)
- **WHEN** the Remote-Write endpoint returns HTTP 429
- **THEN** the system SHALL respect the `Retry-After` header if present, or use exponential backoff

### Requirement: Authentication
The system SHALL support optional basic authentication and bearer token authentication for the Remote-Write endpoint.

#### Scenario: Basic auth configured
- **WHEN** the configuration includes `remote_write.username` and `remote_write.password`
- **THEN** the system SHALL include an HTTP Basic `Authorization` header on all Remote-Write requests

#### Scenario: Bearer token configured
- **WHEN** the configuration includes `remote_write.bearer_token`
- **THEN** the system SHALL include an HTTP Bearer `Authorization` header on all Remote-Write requests

#### Scenario: No auth configured
- **WHEN** no authentication is configured
- **THEN** the system SHALL send Remote-Write requests without an `Authorization` header

### Requirement: OpenTelemetry metrics instrumentation
The system SHALL use the OpenTelemetry Python SDK to record operational metrics for the persister's own health and performance.

#### Scenario: Prometheus metrics endpoint available
- **WHEN** the service is running
- **THEN** the OTel Prometheus exporter SHALL serve a `/metrics` HTTP endpoint on a configurable port (default: 8000) exposing counters, histograms, and gauges for the persister's operations

#### Scenario: Core counters recorded
- **WHEN** the service processes messages
- **THEN** the following OTel counters SHALL be recorded: `prometheus_persister.messages_consumed` (total Kafka messages consumed), `prometheus_persister.samples_written` (total samples sent via Remote-Write), `prometheus_persister.write_errors` (total failed write attempts), `prometheus_persister.chunk_reassembly_timeouts` (expired incomplete chunks)

#### Scenario: Histograms recorded
- **WHEN** the service performs write and transform operations
- **THEN** the following OTel histograms SHALL be recorded: `prometheus_persister.write_latency` (seconds per Remote-Write request), `prometheus_persister.transform_duration` (seconds per CollectionSet transformation), `prometheus_persister.batch_size` (number of samples per flush)

#### Scenario: Gauges recorded
- **WHEN** the service is consuming from Kafka
- **THEN** the following OTel up/down counters SHALL be recorded: `prometheus_persister.inflight_chunks` (number of incomplete chunked messages in the reassembly buffer)

#### Scenario: OTLP export enabled
- **WHEN** the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable is set
- **THEN** the system SHALL additionally export metrics via OTLP to the configured endpoint

### Requirement: OpenTelemetry distributed tracing
The system SHALL create OTel trace spans for the consume-transform-write pipeline to enable latency debugging and request flow visualization.

#### Scenario: Consume span created
- **WHEN** a Kafka message is polled and parsed
- **THEN** the system SHALL create a span named `consume_message` with attributes `messaging.system="kafka"`, `messaging.destination.name="Delta-V.Sink.CollectionSet"`, and `messaging.kafka.message.offset`

#### Scenario: Transform span created
- **WHEN** a CollectionSet payload is transformed to Prometheus samples
- **THEN** the system SHALL create a child span named `transform_collectionset` with attributes `collectionset.resource_count` and `collectionset.sample_count`

#### Scenario: Write span created
- **WHEN** a batch is flushed via Remote-Write
- **THEN** the system SHALL create a child span named `remote_write_batch` with attributes `batch.size`, `http.response.status_code`, and span status reflecting success or failure

#### Scenario: Chunk reassembly span
- **WHEN** a multi-chunk message is being reassembled
- **THEN** the system SHALL create a span named `reassemble_chunks` with attributes `messaging.message_id` and `chunks.total`

#### Scenario: OTLP trace export
- **WHEN** `OTEL_EXPORTER_OTLP_ENDPOINT` is configured
- **THEN** the system SHALL export traces via OTLP to the configured endpoint

### Requirement: Structured logging with trace correlation
The system SHALL use Python's `logging` module with the OTel log bridge so that log records include trace and span IDs for correlation.

#### Scenario: Logs include trace context
- **WHEN** a log message is emitted within an active trace span
- **THEN** the log record SHALL include `trace_id` and `span_id` fields

#### Scenario: Structured log format
- **WHEN** the service logs operational events
- **THEN** log output SHALL be in JSON format with fields: `timestamp`, `level`, `message`, `logger`, `trace_id`, `span_id`
