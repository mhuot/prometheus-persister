## ADDED Requirements

### Requirement: Kafka topic subscription
The system SHALL connect to a Kafka cluster and subscribe to the `Delta-V.Sink.CollectionSet` topic using a configurable consumer group.

#### Scenario: Successful connection and subscription
- **WHEN** the service starts with valid Kafka bootstrap servers configured
- **THEN** the system joins the configured consumer group and begins polling the `Delta-V.Sink.CollectionSet` topic

#### Scenario: Kafka unavailable at startup
- **WHEN** the service starts and the Kafka cluster is unreachable
- **THEN** the system SHALL retry connection with exponential backoff and log errors until the cluster becomes available

### Requirement: SinkMessage envelope parsing
The system SHALL deserialize each Kafka message value as a `SinkMessage` protobuf envelope, extracting `message_id`, `content`, `current_chunk_number`, and `total_chunks`.

#### Scenario: Single-chunk message
- **WHEN** a `SinkMessage` is received with `total_chunks == 1`
- **THEN** the system SHALL immediately pass the `content` bytes to the metric transformer

#### Scenario: Multi-chunk message reassembly
- **WHEN** multiple `SinkMessage` records share the same `message_id` and `total_chunks > 1`
- **THEN** the system SHALL buffer chunks in memory and emit the concatenated `content` bytes once all chunks (`current_chunk_number` 0 through `total_chunks - 1`) have arrived

#### Scenario: Incomplete chunked message timeout
- **WHEN** a chunked message has not received all chunks within 60 seconds (configurable)
- **THEN** the system SHALL discard the incomplete buffer, log a warning with the `message_id`, and increment an error counter metric

### Requirement: Kafka offset management
The system SHALL commit Kafka offsets only after the corresponding metrics have been successfully dispatched to the Remote-Write batching layer.

#### Scenario: Successful processing commits offset
- **WHEN** a message is consumed and its metrics are accepted into the batch buffer
- **THEN** the system SHALL commit the offset for that partition

#### Scenario: Processing failure delays commit
- **WHEN** a message fails to parse or transform
- **THEN** the system SHALL log the error, increment an error counter, and still commit the offset to avoid blocking the consumer

### Requirement: Graceful shutdown
The system SHALL handle SIGTERM and SIGINT signals by finishing in-flight message processing, flushing pending batches, and committing final offsets before exiting.

#### Scenario: SIGTERM received during processing
- **WHEN** the service receives SIGTERM
- **THEN** the system SHALL stop polling for new messages, flush the current metric batch via Remote-Write, commit offsets, and exit cleanly within 30 seconds
