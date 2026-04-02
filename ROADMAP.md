# Prometheus Persister Roadmap

This document outlines the high-level vision and planned enhancements for the Prometheus Persister. Items are categorized by their impact on reliability, scalability, and feature set.

## 1. Data Integrity & Durability
*   **Write-Ahead Log (WAL):** Implement a lightweight disk-backed queue (using SQLite or `diskcache`) to prevent data loss of in-memory batches during service restarts or crashes.
*   **Dead Letter Queue (DLQ):** Route malformed or consistently failing `CollectionSet` messages to a dedicated Kafka DLQ topic for offline inspection and debugging.

## 2. Advanced Metric Processing
*   **Relabeling & Filtering:** Implement a subset of [Prometheus Relabeling](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config) to allow dropping high-cardinality metrics or adding global static labels (e.g., `environment`, `cluster`).
*   **Metric Metadata:** Support sending `HELP` and `TYPE` metadata via Remote-Write to improve the discovery experience in Grafana and other backends.

## 3. Future-Proofing Protocols
*   **Remote-Write v2:** Implement support for the Prometheus Remote-Write v2 protocol for improved efficiency via symbol tables and reduced payload size.
*   **Native OTLP Sink:** Add an optional OTLP metric exporter to push metrics directly to OTel Collectors or other OTLP-native backends.
*   **Telemetryd Support:** Add consumption of the `OpenNMS.Sink.Telemetry` topic for Netflow/IPFIX/sFlow data, transforming telemetry payloads into Prometheus metrics alongside CollectionSet data.

## 4. Performance & Scalability
*   **AsyncIO Architecture:** Migrate the core pipeline from `threading` and `requests` to `aiokafka` and `httpx` to increase throughput and reduce the resource footprint.
*   **Sharded Batching:** Implement per-partition or sharded buffers to allow the transformation and write logic to scale across multiple CPU cores without lock contention.

## 5. Multi-Tenancy & Multi-Cluster
*   **Multi-Cluster Sources:** Support consuming from multiple Delta-V Kafka clusters simultaneously, with per-cluster consumer groups and configuration.
*   **Routing by Location/Tenant:** Route metrics to different Remote-Write endpoints based on `deltav_location` or other label values, enabling per-tenant or per-region metric isolation.

## 6. Operations & Deployment
*   **Helm Chart:** Provide a production-grade Helm chart with built-in Horizontal Pod Autoscaler (HPA) and Prometheus `ServiceMonitor` support.
*   **Health Dashboard:** Provide a pre-built Grafana JSON dashboard export for the persister's internal OTel telemetry (lag, throughput, error rates). See [Grafana Cloud guide](docs/grafana-cloud-guide.md) for example PromQL queries.
*   **Kafka Consumer Lag Gauge:** Add a per-partition consumer lag gauge to the `/metrics` endpoint by querying Kafka consumer group offsets, complementing the existing `inflight_chunks` counter for more precise alerting on pipeline delays.

## 7. Developer Experience
*   **Mock Minion CLI:** Create a utility to generate and publish realistic Delta-V `SinkMessage` payloads to Kafka for local development and testing without a full Delta-V stack.
