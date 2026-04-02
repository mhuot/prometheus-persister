# Prometheus Persister Roadmap

This document outlines the high-level vision and "S-tier" enhancements planned for the Prometheus Persister. These items are categorized by their impact on the service's reliability, scalability, and feature set.

## 1. Data Integrity & Durability
*   **Write-Ahead Log (WAL):** Implement a lightweight disk-backed queue (using SQLite or `diskcache`) to prevent data loss of in-memory batches during service restarts or crashes.
*   **Dead Letter Queue (DLQ):** Route malformed or consistently failing `CollectionSet` messages to a dedicated Kafka DLQ topic for offline inspection and debugging.

## 2. Advanced Metric Processing
*   **Relabeling & Filtering:** Implement a subset of [Prometheus Relabeling](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#relabel_config) to allow dropping high-cardinality metrics or adding global static labels (e.g., `environment`, `cluster`).
*   **Metric Metadata:** Support sending `HELP` and `TYPE` metadata via Remote-Write to improve the discovery experience in Grafana and other backends.

## 3. Future-Proofing Protocols
*   **Remote-Write v2:** Implement support for the OTLP-based Prometheus Remote-Write v2 protocol for improved efficiency and alignment with the OpenTelemetry ecosystem.
*   **Native OTLP Sink:** Add an optional OTLP metric exporter to push metrics directly to OTel Collectors or other OTLP-native backends.

## 4. Performance & Scalability
*   **AsyncIO Architecture:** Migrate the core pipeline from `threading` and `requests` to `aiokafka` and `httpx` to increase throughput and reduce the resource footprint.
*   **Sharded Batching:** Implement per-partition or sharded buffers to allow the transformation and write logic to scale across multiple CPU cores without lock contention.

## 5. Operations & Deployment
*   **Helm Chart:** Provide a production-grade Helm chart with built-in Horizontal Pod Autoscaler (HPA) and Prometheus `ServiceMonitor` support.
*   **Health Dashboard:** Include a pre-configured Grafana JSON dashboard that visualizes the persister's internal OTel telemetry (lag, throughput, error rates).
*   **Kafka Lag Metrics:** Add a dedicated gauge for consumer lag to the `/metrics` endpoint for easier alerting on pipeline delays.

## 6. Developer Experience
*   **Mock Minion CLI:** Create a utility to generate and publish realistic Delta-V `SinkMessage` payloads to Kafka for local development and testing without a full Delta-V stack.
