## Why

Users deploying the prometheus-persister alongside an existing Delta-V installation need a clear, end-to-end guide for connecting it to Grafana Cloud. This involves configuring the Grafana Cloud Mimir Remote-Write endpoint, connecting to Delta-V's Kafka, verifying metric flow, and building dashboards. Without a guide, users must piece together docs from three different systems (Delta-V, prometheus-persister, Grafana Cloud).

## What Changes

- **New guide document**: `docs/grafana-cloud-guide.md` — a thorough step-by-step walkthrough covering prerequisites, Grafana Cloud setup, prometheus-persister configuration, deployment options (Docker, standalone), verification, dashboards, OTel observability integration, and troubleshooting.
- **README integration section**: Add a generalized "Integration" section to the README explaining how to connect any Delta-V source (Kafka) to any Prometheus-compatible target (Prometheus, Mimir, VictoriaMetrics, Thanos) with configuration examples for each.

## High-Level Flow

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#3B6EA5', 'primaryTextColor': '#1a1a1a', 'primaryBorderColor': '#2d5580', 'lineColor': '#6B7280', 'background': 'transparent', 'mainBkg': 'transparent', 'edgeLabelBackground': 'transparent'}}}%%
flowchart TB
    subgraph deltav ["Existing Delta-V"]
        MIN["Minions"]
        KFK[/"Kafka\nCollectionSet Topic"/]
    end

    subgraph bridge ["Prometheus Persister"]
        PP["Consumer\nTransformer\nRemote-Writer"]
    end

    subgraph grafana ["Grafana Cloud"]
        MIM["Mimir\nRemote-Write Endpoint"]
        GD["Grafana\nDashboards"]
    end

    MIN --> KFK
    KFK --> PP
    PP -->|"Remote-Write\nBasic Auth"| MIM
    MIM --> GD

    style deltav fill:transparent,stroke:#6B7280,stroke-width:1px
    style bridge fill:transparent,stroke:#6B7280,stroke-width:1px
    style grafana fill:transparent,stroke:#6B7280,stroke-width:1px
    style MIN fill:#4A7C59,stroke:#2d5a3f,color:#FFFFFF
    style KFK fill:#8B6914,stroke:#6d5210,color:#FFFFFF
    style PP fill:#3B6EA5,stroke:#2d5580,color:#FFFFFF
    style MIM fill:#7B4B94,stroke:#5e3972,color:#FFFFFF
    style GD fill:#7B4B94,stroke:#5e3972,color:#FFFFFF
```

## Capabilities

### New Capabilities
- `grafana-cloud-guide`: Step-by-step deployment guide covering Grafana Cloud setup, prometheus-persister configuration, verification, dashboards, and troubleshooting.

### Modified Capabilities
_(none)_

## Impact

- **New files**: `docs/grafana-cloud-guide.md`
- **Modified files**: `README.md` (integration section + link to guide)
- **No code changes** — documentation only.
