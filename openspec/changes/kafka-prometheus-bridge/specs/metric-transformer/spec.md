## ADDED Requirements

### Requirement: CollectionSet protobuf deserialization
The system SHALL parse the raw bytes payload as a `CollectionSet` protobuf message, iterating over each `CollectionSetResource` and its `NumericAttribute` entries.

#### Scenario: Valid CollectionSet payload
- **WHEN** the consumer provides a raw bytes payload from the `Delta-V.Sink.CollectionSet` topic
- **THEN** the system SHALL deserialize it as a `CollectionSet` protobuf and produce one Prometheus sample per `NumericAttribute`

#### Scenario: Invalid or corrupt payload
- **WHEN** the payload cannot be deserialized as a `CollectionSet`
- **THEN** the system SHALL log an error with the raw payload size and skip the message

### Requirement: Node-level resource label mapping
The system SHALL map `NodeLevelResource` fields to Prometheus labels following OTel conventions.

#### Scenario: NodeLevelResource with all fields populated
- **WHEN** a `CollectionSetResource` contains a `NodeLevelResource` with `node_id=42`, `node_label="router1"`, `foreign_source="requisition"`, `foreign_id="r1"`, `location="Default"`
- **THEN** the generated Prometheus sample SHALL include labels: `host_id="42"`, `host_name="router1"`, `deltav_foreign_source="requisition"`, `deltav_foreign_id="r1"`, `deltav_location="Default"`

### Requirement: Interface-level resource label mapping
The system SHALL map `InterfaceLevelResource` fields to Prometheus labels, including the parent node labels plus interface-specific labels.

#### Scenario: InterfaceLevelResource mapping
- **WHEN** a `CollectionSetResource` contains an `InterfaceLevelResource` with `instance="eth0"` and `if_index=2`
- **THEN** the generated sample SHALL include all parent node labels plus `deltav_instance="eth0"` and `deltav_if_index="2"`

### Requirement: GenericType resource label mapping
The system SHALL map `GenericTypeResource` fields to Prometheus labels, including the parent node labels plus type and instance.

#### Scenario: GenericTypeResource mapping
- **WHEN** a `CollectionSetResource` contains a `GenericTypeResource` with `type="diskIOTable"` and `instance="/dev/sda"`
- **THEN** the generated sample SHALL include all parent node labels plus `deltav_resource_type="diskIOTable"` and `deltav_instance="/dev/sda"`

### Requirement: ResponseTime resource label mapping
The system SHALL map `ResponseTimeResource` fields to Prometheus labels.

#### Scenario: ResponseTimeResource mapping
- **WHEN** a `CollectionSetResource` contains a `ResponseTimeResource` with `instance="192.168.1.1"` and `location="Default"`
- **THEN** the generated sample SHALL include labels `deltav_instance="192.168.1.1"` and `deltav_location="Default"`

### Requirement: Resource-level metadata labels
The system SHALL include `resource_id`, `resource_name`, and `resource_type_name` from `CollectionSetResource` as labels on every generated sample when present.

#### Scenario: Resource metadata included
- **WHEN** a `CollectionSetResource` has `resource_id="node[42].interfaceSnmp[eth0-00deadbeef00]"` and `resource_type_name="interfaceSnmp"`
- **THEN** the generated sample SHALL include `deltav_resource_id="node[42].interfaceSnmp[eth0-00deadbeef00]"` and `deltav_resource_type="interfaceSnmp"`

### Requirement: Metric name sanitization
The system SHALL sanitize `NumericAttribute` names to be valid Prometheus metric names (matching `[a-zA-Z_:][a-zA-Z0-9_:]*`), replacing invalid characters with underscores.

#### Scenario: Metric name with invalid characters
- **WHEN** a `NumericAttribute` has `name="if.octets.in"` and `group="mib2-interfaces"`
- **THEN** the Prometheus metric name SHALL be `mib2_interfaces_if_octets_in`

### Requirement: Metric type mapping
The system SHALL map `NumericAttribute.Type.GAUGE` to Prometheus gauge and `NumericAttribute.Type.COUNTER` to Prometheus counter, appending `_total` suffix for counters.

#### Scenario: Gauge metric
- **WHEN** a `NumericAttribute` has `type=GAUGE`
- **THEN** the Prometheus sample SHALL be emitted as a gauge (no suffix)

#### Scenario: Counter metric
- **WHEN** a `NumericAttribute` has `type=COUNTER`
- **THEN** the Prometheus metric name SHALL have `_total` appended

### Requirement: Timestamp handling
The system SHALL use the `CollectionSet.timestamp` field (epoch milliseconds) as the Prometheus sample timestamp, converting to milliseconds as required by Remote-Write.

#### Scenario: Timestamp conversion
- **WHEN** a `CollectionSet` has `timestamp=1700000000000`
- **THEN** all generated samples from that CollectionSet SHALL have timestamp `1700000000000`

### Requirement: Metric value handling
The system SHALL prefer the `metric_value` wrapper field over the `value` field in `NumericAttribute` when `metric_value` is present, to correctly handle zero values.

#### Scenario: Zero-value metric with metric_value set
- **WHEN** a `NumericAttribute` has `value=0` and `metric_value` wrapper set to `0.0`
- **THEN** the system SHALL emit the sample with value `0.0`

#### Scenario: Metric without metric_value wrapper
- **WHEN** a `NumericAttribute` has `value=42.5` and no `metric_value` wrapper
- **THEN** the system SHALL use `value=42.5`
