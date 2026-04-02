## ADDED Requirements

### Requirement: Prerequisites section
The guide SHALL document all prerequisites needed before starting setup.

#### Scenario: Prerequisites listed
- **WHEN** a user reads the prerequisites section
- **THEN** the guide SHALL list: existing Delta-V deployment with Minions publishing to Kafka, Grafana Cloud account with Mimir enabled, network access from the persister host to both Kafka and Grafana Cloud, Docker (or Python 3.11+) installed

### Requirement: Grafana Cloud setup instructions
The guide SHALL provide step-by-step instructions for obtaining the Mimir Remote-Write endpoint URL and API key from Grafana Cloud.

#### Scenario: Finding the Remote-Write endpoint
- **WHEN** a user follows the Grafana Cloud setup steps
- **THEN** the guide SHALL describe how to navigate to the Mimir data source configuration and locate the Remote-Write endpoint URL in the format `https://prometheus-prod-XX-prod-us-east-0.grafana.net/api/prom/push`

#### Scenario: Creating an API key
- **WHEN** a user needs authentication credentials
- **THEN** the guide SHALL describe how to create a Grafana Cloud API key with `MetricsPublisher` role and note the instance ID for basic auth

### Requirement: Persister configuration for Grafana Cloud
The guide SHALL show the exact configuration needed to connect the persister to Delta-V Kafka and Grafana Cloud Mimir.

#### Scenario: Config file example
- **WHEN** a user configures the persister
- **THEN** the guide SHALL provide a complete `config.yaml` example with Kafka bootstrap servers, Grafana Cloud Remote-Write URL, and basic auth (username=instance ID, password=API key)

#### Scenario: Environment variable example
- **WHEN** a user prefers environment variables
- **THEN** the guide SHALL provide the equivalent `KAFKA_BOOTSTRAP_SERVERS`, `REMOTE_WRITE_URL`, `REMOTE_WRITE_USERNAME`, and `REMOTE_WRITE_PASSWORD` environment variables

### Requirement: Docker deployment instructions
The guide SHALL provide instructions for deploying the persister via Docker alongside an existing Delta-V stack.

#### Scenario: Docker Compose deployment
- **WHEN** a user deploys with Docker Compose
- **THEN** the guide SHALL show how to add the persister service to the Delta-V docker-compose.yml with the Grafana Cloud environment variables

#### Scenario: Standalone Docker run
- **WHEN** a user runs Docker directly
- **THEN** the guide SHALL provide a `docker run` command with all required environment variables and network configuration

### Requirement: Standalone deployment instructions
The guide SHALL provide instructions for running the persister directly with Python.

#### Scenario: Python venv deployment
- **WHEN** a user deploys without Docker
- **THEN** the guide SHALL show: creating a venv, installing the package, generating protos, configuring config.yaml, and running the service

### Requirement: Verification steps
The guide SHALL include verification steps to confirm metrics are flowing end-to-end.

#### Scenario: Verify persister is running
- **WHEN** the persister is started
- **THEN** the guide SHALL show how to check the `/metrics` endpoint for `prometheus_persister_messages_consumed` counter

#### Scenario: Verify metrics in Grafana Cloud
- **WHEN** the persister is writing to Grafana Cloud
- **THEN** the guide SHALL provide a PromQL query to run in Grafana Explore to confirm Delta-V metrics are present (e.g., `{host_id!=""}`)

### Requirement: Example dashboard
The guide SHALL include an example Grafana dashboard configuration.

#### Scenario: Dashboard with Delta-V metrics
- **WHEN** a user wants to visualize Delta-V metrics
- **THEN** the guide SHALL provide example PromQL queries for common panels: interface traffic by host, CPU/memory by node, top-N hosts by metric value

### Requirement: OTel integration for persister observability
The guide SHALL describe how to send the persister's own OTel telemetry to Grafana Cloud.

#### Scenario: OTLP configuration
- **WHEN** a user wants full-stack observability
- **THEN** the guide SHALL show how to set `OTEL_EXPORTER_OTLP_ENDPOINT` to the Grafana Cloud OTLP endpoint with authentication headers

### Requirement: Troubleshooting section
The guide SHALL include a troubleshooting section covering common failure modes.

#### Scenario: Common issues documented
- **WHEN** a user encounters problems
- **THEN** the guide SHALL cover: Kafka connection refused, Remote-Write 401/403 auth errors, no metrics appearing in Grafana, high consumer lag, and chunk reassembly timeouts
