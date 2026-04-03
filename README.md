# Prometheus Persister

[![CI](https://github.com/mhuot/prometheus-persister/actions/workflows/ci.yml/badge.svg)](https://github.com/mhuot/prometheus-persister/actions/workflows/ci.yml)
[![Proto Check](https://github.com/mhuot/prometheus-persister/actions/workflows/proto-check.yml/badge.svg)](https://github.com/mhuot/prometheus-persister/actions/workflows/proto-check.yml)

A standalone Python service that bridges Delta-V performance metrics from Kafka to Prometheus-compatible stores via Remote-Write.

## Overview

Delta-V Minions collect performance metrics (SNMP, WMI, etc.) and publish them as protobuf-encoded `CollectionSet` messages to Kafka. Prometheus Persister consumes these messages, transforms Delta-V hierarchical resource structures into flat Prometheus labels following [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/), and pushes the metrics via [Prometheus Remote-Write](https://prometheus.io/docs/concepts/remote_write_spec/) to any compatible backend (Prometheus, Mimir, VictoriaMetrics, Thanos).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#4A7C59', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5a3f', 'lineColor': '#6B7280', 'secondaryColor': '#3B6EA5', 'tertiaryColor': '#8B6914', 'background': 'transparent', 'mainBkg': 'transparent', 'nodeBorder': '#4A7C59', 'clusterBkg': 'transparent', 'titleColor': '#1a1a1a', 'edgeLabelBackground': 'transparent'}}}%%
flowchart LR
    subgraph sources ["Data Sources"]
        M1["Minion 1"]
        M2["Minion 2"]
        Mn["Minion N"]
    end

    subgraph kafka ["Apache Kafka"]
        T1[/"CollectionSet Topic"/]
    end

    subgraph persister ["Prometheus Persister"]
        C["Consumer\n+ Chunk\nReassembly"]
        X["Transformer\nOTel Label\nMapping"]
        W["Remote-Write\nClient"]
    end

    subgraph targets ["Prometheus Backend"]
        P[("Prometheus\nMimir\nVictoriaMetrics")]
    end

    M1 --> T1
    M2 --> T1
    Mn --> T1
    T1 --> C
    C --> X
    X --> W
    W -->|"Remote-Write v1\nSnappy + Protobuf"| P

    style sources fill:transparent,stroke:#6B7280,stroke-width:1px
    style kafka fill:transparent,stroke:#6B7280,stroke-width:1px
    style persister fill:transparent,stroke:#6B7280,stroke-width:1px
    style targets fill:transparent,stroke:#6B7280,stroke-width:1px
    style M1 fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style M2 fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style Mn fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style T1 fill:#8B6914,stroke:#6d5210,color:#FFFFFF
    style C fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style X fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style W fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style P fill:#7B4B94,stroke:#5e3972,color:#FFFFFF
```

## Features

- **Kafka consumer** with SinkMessage protobuf envelope parsing and multi-chunk reassembly
- **OTel-conformant label mapping** from Delta-V hierarchical resources to flat Prometheus labels
- **Prometheus Remote-Write v1** with Snappy compression, batching, retry, and backpressure
- **OpenTelemetry instrumentation** for the service itself: metrics, distributed traces, and structured logging
- **Docker-ready** with YAML + environment variable configuration

## Label Mapping

Delta-V resource metadata is mapped to Prometheus labels following OpenTelemetry semantic conventions:

| Delta-V Field | Prometheus Label | OTel Convention |
|:---|:---|:---|
| `node_id` | `host_id` | `host.id` |
| `node_label` | `host_name` | `host.name` |
| `foreign_source` | `deltav_foreign_source` | custom |
| `foreign_id` | `deltav_foreign_id` | custom |
| `location` | `deltav_location` | `deltav.location` |
| `resource_id` | `deltav_resource_id` | `deltav.resource.id` |
| `if_index` | `deltav_if_index` | custom |
| `instance` | `deltav_instance` | custom |
| `resource_type_name` | `deltav_resource_type` | custom |

All four resource types are supported:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#3B6EA5', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5580', 'lineColor': '#6B7280', 'background': 'transparent', 'mainBkg': 'transparent', 'nodeBorder': '#3B6EA5', 'clusterBkg': 'transparent', 'edgeLabelBackground': 'transparent'}}}%%
flowchart TD
    CS["CollectionSet\n<i>timestamp</i>"]
    CSR["CollectionSetResource"]
    NLR["NodeLevelResource\nhost_id, host_name\ndeltav_location"]
    ILR["InterfaceLevelResource\n+ deltav_instance\n+ deltav_if_index"]
    GTR["GenericTypeResource\n+ deltav_resource_type\n+ deltav_instance"]
    RTR["ResponseTimeResource\ndeltav_instance\ndeltav_location"]
    NA["NumericAttribute\nmetric name + value"]

    CS --> CSR
    CSR -->|"oneof resource"| NLR
    CSR -->|"oneof resource"| ILR
    CSR -->|"oneof resource"| GTR
    CSR -->|"oneof resource"| RTR
    CSR --> NA

    ILR -.->|"inherits labels"| NLR
    GTR -.->|"inherits labels"| NLR

    style CS fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style CSR fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style NLR fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style ILR fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style GTR fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style RTR fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style NA fill:#8B6914,stroke:#6d5210,color:#FFFFFF
```

## Architecture

### Processing Pipeline

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#3B6EA5', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5580', 'lineColor': '#6B7280', 'background': 'transparent', 'mainBkg': 'transparent', 'edgeLabelBackground': 'transparent'}}}%%
sequenceDiagram
    participant K as Kafka
    participant C as Consumer
    participant B as Chunk Buffer
    participant T as Transformer
    participant R as Remote-Write Client
    participant P as Prometheus Backend

    K->>C: Poll messages
    C->>C: Parse SinkMessage envelope

    alt Single chunk (total_chunks == 1)
        C->>T: Forward content bytes
    else Multi-chunk
        C->>B: Buffer chunk by message_id
        B-->>B: Wait for remaining chunks
        B->>T: Emit concatenated payload
    end

    T->>T: Deserialize CollectionSet protobuf
    T->>T: Map resource labels (OTel conventions)
    T->>T: Sanitize metric names
    T->>R: Prometheus samples

    R->>R: Accumulate in batch buffer

    alt Batch size reached OR flush interval elapsed
        R->>R: Serialize WriteRequest protobuf
        R->>R: Compress with Snappy
        R->>P: HTTP POST (Remote-Write v1)
        P-->>R: 200 OK
        R->>C: Confirm flush (commit offsets)
    end
```

### Observability Stack

The service instruments itself with OpenTelemetry for full observability:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#3B6EA5', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5580', 'lineColor': '#6B7280', 'background': 'transparent', 'mainBkg': 'transparent', 'nodeBorder': '#3B6EA5', 'clusterBkg': 'transparent', 'edgeLabelBackground': 'transparent'}}}%%
flowchart TB
    subgraph app ["Prometheus Persister"]
        OBS["observability.py\nMeterProvider\nTracerProvider\nLoggerProvider"]
        CON["consumer.py"]
        TRA["transformer.py"]
        REM["remote_writer.py"]
    end

    subgraph signals ["OTel Signals"]
        MET["Metrics\ncounters, histograms,\nup/down counters"]
        TRC["Traces\nconsume > transform >\nwrite spans"]
        LOG["Logs\nJSON + trace_id\n+ span_id"]
    end

    subgraph exporters ["Exporters"]
        PROM["/metrics :8000\nPrometheus Exporter"]
        OTLP["OTLP Exporter\n(optional)"]
    end

    OBS --> CON
    OBS --> TRA
    OBS --> REM
    CON --> MET
    CON --> TRC
    TRA --> MET
    TRA --> TRC
    REM --> MET
    REM --> TRC
    CON --> LOG
    TRA --> LOG
    REM --> LOG
    MET --> PROM
    MET --> OTLP
    TRC --> OTLP
    LOG --> OTLP

    style app fill:transparent,stroke:#6B7280,stroke-width:1px
    style signals fill:transparent,stroke:#6B7280,stroke-width:1px
    style exporters fill:transparent,stroke:#6B7280,stroke-width:1px
    style OBS fill:#7B4B94,stroke:#5e3972,color:#FFFFFF
    style CON fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style TRA fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style REM fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style MET fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style TRC fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style LOG fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style PROM fill:#8B6914,stroke:#6d5210,color:#FFFFFF
    style OTLP fill:#8B6914,stroke:#6d5210,color:#FFFFFF
```

## Integration

The prometheus-persister connects a **source** (Delta-V Kafka) to a **target** (any Prometheus-compatible Remote-Write endpoint).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#3B6EA5', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5580', 'lineColor': '#6B7280', 'background': 'transparent', 'mainBkg': 'transparent', 'edgeLabelBackground': 'transparent'}}}%%
flowchart LR
    subgraph source ["Source: Delta-V"]
        KFK[/"Kafka\nCollectionSet Topic"/]
    end

    PP["Prometheus\nPersister"]

    subgraph target ["Target: Prometheus Store"]
        RW["Remote-Write\nEndpoint"]
    end

    KFK --> PP -->|"Remote-Write v1\nprotobuf + snappy"| RW

    style source fill:transparent,stroke:#6B7280,stroke-width:1px
    style target fill:transparent,stroke:#6B7280,stroke-width:1px
    style KFK fill:#8B6914,stroke:#6d5210,color:#FFFFFF
    style PP fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style RW fill:#7B4B94,stroke:#5e3972,color:#FFFFFF
```

### Supported Targets

Any Prometheus-compatible Remote-Write endpoint works. Here are the common ones:

| Target | Remote-Write URL | Auth |
|:---|:---|:---|
| **Prometheus** | `http://prometheus:9090/api/v1/write` | None (or reverse proxy) |
| **Grafana Mimir** | `http://mimir:9009/api/v1/push` | Bearer token or basic auth |
| **Grafana Cloud** | `https://prometheus-prod-XX-....grafana.net/api/prom/push` | Basic auth (instance ID + API key) |
| **VictoriaMetrics** | `http://victoriametrics:8428/api/v1/write` | None (or basic auth) |
| **Thanos Receive** | `http://thanos-receive:19291/api/v1/receive` | None (or bearer token) |
| **Cortex** | `http://cortex:9009/api/v1/push` | Bearer token or basic auth |

Configure via `config.yaml` or environment variables:

```bash
# Prometheus (no auth)
REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write

# Grafana Cloud (basic auth)
REMOTE_WRITE_URL=https://prometheus-prod-13-prod-us-east-0.grafana.net/api/prom/push
REMOTE_WRITE_USERNAME=123456
REMOTE_WRITE_PASSWORD=glc_eyJ...

# VictoriaMetrics (no auth)
REMOTE_WRITE_URL=http://victoriametrics:8428/api/v1/write

# Thanos Receive (bearer token)
REMOTE_WRITE_URL=http://thanos-receive:19291/api/v1/receive
REMOTE_WRITE_BEARER_TOKEN=my-token

# Cortex (bearer token)
REMOTE_WRITE_URL=http://cortex:9009/api/v1/push
REMOTE_WRITE_BEARER_TOKEN=my-token
```

### Connecting to Delta-V

The persister consumes from the `OpenNMS.Sink.CollectionSet` Kafka topic. To find your Delta-V Kafka brokers:

1. Check the Delta-V `docker-compose.yml` for the `kafka` service and its advertised listeners
2. Or check a Minion's configuration for `KAFKA_IPC_BOOTSTRAP_SERVERS`

Quick connectivity test:

```bash
# Verify the topic exists and has data
kcat -b your-kafka-broker:9092 -t OpenNMS.Sink.CollectionSet -C -c 1 -e -q | wc -c
```

If this returns a non-zero value, Kafka is reachable and Minions are publishing metrics.

### Guides

- [Grafana Cloud Integration Guide](docs/grafana-cloud-guide.md) — complete walkthrough from setup to dashboards
- [Replacing the Cortex TSS Plugin](docs/replacing-cortex-tss.md) — migrating from the embedded Cortex TSS to the standalone persister

## Configuration

Configuration is loaded from `config.yaml` with environment variable overrides:

```yaml
kafka:
  bootstrap_servers: "localhost:9092"     # or KAFKA_BOOTSTRAP_SERVERS
  consumer_group: "prometheus-persister"  # or KAFKA_CONSUMER_GROUP
  topic: "OpenNMS.Sink.CollectionSet"

remote_write:
  url: "http://localhost:9090/api/v1/write"  # or REMOTE_WRITE_URL
  # username: ""        # Basic auth (or REMOTE_WRITE_USERNAME)
  # password: ""        # Basic auth (or REMOTE_WRITE_PASSWORD)
  # bearer_token: ""    # Bearer auth (or REMOTE_WRITE_BEARER_TOKEN)
  timeout: 30            # seconds
  max_retries: 3

batching:
  max_size: 1000         # samples per batch
  flush_interval: 5      # seconds

chunk_reassembly:
  ttl: 60                # seconds before incomplete chunks are evicted

observability:
  metrics_port: 8000     # Prometheus /metrics endpoint port
  # OTEL_EXPORTER_OTLP_ENDPOINT: set via env var to enable OTLP export
```

## Quick Start

### Prerequisites

- Python 3.11+
- Access to a Kafka cluster with Delta-V topics
- A Prometheus-compatible Remote-Write endpoint

### Run Locally

```bash
# Clone and set up
git clone https://github.com/mhuot/prometheus-persister.git
cd prometheus-persister
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Generate protobuf bindings
make proto

# Configure
cp config.yaml.example config.yaml
# Edit config.yaml with your Kafka and Prometheus endpoints

# Run
python -m prometheus_persister
```

### Run with Docker

```bash
# Build locally
make image

# Or build directly
docker build -t prometheus-persister .

# Run
docker run -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
           -e REMOTE_WRITE_URL=http://mimir:9009/api/v1/push \
           -p 8000:8000 \
           prometheus-persister
```

### Run with Docker Compose

The included `docker-compose.yml` provides a Kafka broker and the persister for local development:

```bash
# Start everything (Kafka + persister)
docker compose up

# Or just the persister (if Kafka is already running)
docker compose up prometheus-persister
```

Set `REMOTE_WRITE_URL` to point at your Prometheus-compatible endpoint:

```bash
REMOTE_WRITE_URL=http://mimir:9009/api/v1/push docker compose up
```

### Adding to the Delta-V Stack

Copy the `prometheus-persister` service block from `docker-compose.yml` into the Delta-V `opennms-container/delta-v/docker-compose.yml`, adjusting `KAFKA_BOOTSTRAP_SERVERS` and `REMOTE_WRITE_URL` for the target environment.

### Pull Pre-built Images

```bash
docker pull ghcr.io/mhuot/prometheus-persister:latest
docker pull ghcr.io/mhuot/prometheus-persister:0.1.0  # specific version
```

## Project Structure

```
prometheus-persister/
├── config.yaml                 # Default configuration
├── pyproject.toml              # Python project metadata and dependencies
├── Dockerfile
├── proto/                      # Source .proto files (from delta-v)
│   ├── sink-message.proto
│   ├── collectionset.proto
│   └── remote_write.proto
├── prometheus_persister/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # YAML + env var config loading
│   ├── consumer.py             # Kafka consumer + chunk reassembly
│   ├── transformer.py          # CollectionSet → Prometheus samples
│   ├── remote_writer.py        # Remote-Write client with batching
│   ├── observability.py        # OTel SDK setup (metrics, traces, logs)
│   └── proto/                  # Generated protobuf bindings
└── tests/
```

## Operational Metrics

The service exposes its own health metrics at `:8000/metrics`:

| Metric | Type | Description |
|:---|:---|:---|
| `prometheus_persister.messages_consumed` | Counter | Kafka messages consumed |
| `prometheus_persister.samples_written` | Counter | Samples sent via Remote-Write |
| `prometheus_persister.write_errors` | Counter | Failed write attempts |
| `prometheus_persister.chunk_reassembly_timeouts` | Counter | Expired incomplete chunks |
| `prometheus_persister.write_latency` | Histogram | Remote-Write request duration (s) |
| `prometheus_persister.transform_duration` | Histogram | CollectionSet transform time (s) |
| `prometheus_persister.batch_size` | Histogram | Samples per flush |
| `prometheus_persister.inflight_chunks` | UpDownCounter | Incomplete chunks in buffer |

Enable OTLP export for traces and logs by setting `OTEL_EXPORTER_OTLP_ENDPOINT`.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
black prometheus_persister tests
pylint prometheus_persister
```

## Releasing

Releases are triggered by pushing a git tag:

```bash
git tag v0.1.0
git push --tags
```

The [release workflow](.github/workflows/release.yml) will:
1. Run the full test suite
2. Build multi-arch images (amd64 + arm64) via Docker BuildX
3. Push to GHCR (`ghcr.io/mhuot/prometheus-persister`)
4. Optionally push to Docker Hub (if secrets are configured)

Images are tagged with the version (e.g., `0.1.0`) and `latest`.

### Configuring Secrets

**GHCR (GitHub Container Registry)** works automatically — the built-in `GITHUB_TOKEN` has `packages:write` permission configured in the workflow.

**Docker Hub** (optional) requires two repository secrets:

1. Go to **Settings > Secrets and variables > Actions** in your GitHub repo
2. Add `DOCKERHUB_USERNAME` — your Docker Hub username
3. Add `DOCKERHUB_TOKEN` — a Docker Hub [access token](https://hub.docker.com/settings/security) (not your password)

If these secrets are not set, the release workflow skips Docker Hub and only pushes to GHCR.

## Proto Contract Check

A [weekly workflow](.github/workflows/proto-check.yml) (Monday 6am UTC) validates that the prometheus-persister test suite still passes against the latest Delta-V proto files. This detects breaking schema changes in `sink-message.proto` or `collectionset.proto` before they hit production.

If a break is detected, the workflow automatically opens a GitHub issue with the failing test output and remediation steps.

You can also run it manually from the **Actions** tab > **Proto Contract Check** > **Run workflow**.

### When a Proto Break is Detected

1. Review the opened GitHub issue for the failing test output
2. Fetch the updated protos: check the Delta-V repo for what changed
3. Update `proto/` files and regenerate bindings: `make proto`
4. Fix any broken transformer/consumer code
5. Run tests locally: `pytest`
6. Commit and close the issue

## License

Apache License 2.0
