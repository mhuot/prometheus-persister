## 1. Guide Document

- [x] 1.1 Create `docs/grafana-cloud-guide.md` with title, overview, and prerequisites section (Delta-V with Kafka, Grafana Cloud account, Docker or Python 3.11+)
- [x] 1.2 Write "Grafana Cloud Setup" section — step-by-step for locating the Mimir Remote-Write endpoint URL, creating an API key with MetricsPublisher role, and noting the instance ID for basic auth
- [x] 1.3 Write "Configure the Persister" section — complete `config.yaml` example with Grafana Cloud auth, plus equivalent environment variable table
- [x] 1.4 Write "Deploy with Docker" section — docker-compose service block for adding to Delta-V stack, standalone `docker run` command, and pre-built image pull instructions
- [x] 1.5 Write "Deploy Standalone" section — venv setup, pip install, proto generation, config, and run commands
- [x] 1.6 Write "Verify Metrics Flow" section — check /metrics endpoint for counters, PromQL query in Grafana Explore to confirm Delta-V metrics, expected label examples
- [ ] 1.7 Write "Example Dashboard" section — PromQL queries for interface traffic, node metrics, top-N panels; include ready-to-use dashboard JSON snippet
- [ ] 1.8 Write "Monitor the Persister with OTel" section — configure OTEL_EXPORTER_OTLP_ENDPOINT for Grafana Cloud OTLP, verify traces and persister metrics in Grafana Cloud
- [ ] 1.9 Write "Troubleshooting" section — Kafka connection refused, 401/403 auth errors, no metrics in Grafana, high consumer lag, chunk reassembly timeouts, each with cause and fix

## 2. README Integration Section

- [ ] 2.1 Add "Integration" section to README.md — generalized overview explaining the source (Delta-V Kafka) and target (any Prometheus-compatible Remote-Write endpoint) architecture with a Mermaid diagram
- [ ] 2.2 Add "Supported Targets" subsection — configuration examples for Prometheus, Grafana Mimir, VictoriaMetrics, and Thanos, each showing the Remote-Write URL format and auth pattern
- [ ] 2.3 Add "Connecting to Delta-V" subsection — how to find/verify the Kafka bootstrap servers and CollectionSet topic in an existing Delta-V deployment, including a quick connectivity test command
- [ ] 2.4 Add "Guides" subsection — link to `docs/grafana-cloud-guide.md` and note that target-specific guides live in `docs/`

## 3. Documentation

- [ ] 3.1 Commit and push all changes
