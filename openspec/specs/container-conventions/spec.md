## ADDED Requirements

### Requirement: OCI image labels
The Dockerfile SHALL include OCI-standard labels populated via build arguments, matching Delta-V label conventions.

#### Scenario: Labels present on built image
- **WHEN** the image is built with `--build-arg VERSION=0.1.0 --build-arg BUILD_DATE=2026-04-02T00:00:00Z --build-arg REVISION=abc123 --build-arg SOURCE=https://github.com/mhuot/prometheus-persister`
- **THEN** the image SHALL contain labels `org.opencontainers.image.version=0.1.0`, `org.opencontainers.image.created`, `org.opencontainers.image.revision`, `org.opencontainers.image.source`, `org.opencontainers.image.title=prometheus-persister`, `org.opencontainers.image.vendor`, and `org.opencontainers.image.licenses`

### Requirement: Non-root execution
The container SHALL run as a non-root user with UID 10001, matching Delta-V conventions.

#### Scenario: Process runs as non-root
- **WHEN** the container starts
- **THEN** the application process SHALL execute as user `persister` with UID 10001 and GID 10001

### Requirement: STOPSIGNAL
The Dockerfile SHALL declare `STOPSIGNAL SIGTERM` for graceful shutdown compatibility with orchestrators.

#### Scenario: Graceful shutdown via SIGTERM
- **WHEN** Docker sends the stop signal to the container
- **THEN** the container SHALL receive SIGTERM and initiate graceful shutdown (flush batches, commit offsets)

### Requirement: Health check
The Dockerfile SHALL include a `HEALTHCHECK` instruction that validates the service is operational.

#### Scenario: Healthy service
- **WHEN** the service is running and the OTel Prometheus exporter is serving `/metrics`
- **THEN** the health check SHALL pass by successfully curling `http://localhost:8000/metrics`

#### Scenario: Unhealthy service
- **WHEN** the service has crashed or `/metrics` is not responding
- **THEN** the health check SHALL fail after the configured retries

### Requirement: Entrypoint wrapper script
The container SHALL use an `entrypoint.sh` wrapper script that handles environment setup before exec'ing the Python process.

#### Scenario: Default startup
- **WHEN** the container starts with no command override
- **THEN** `entrypoint.sh` SHALL exec `python -m prometheus_persister` with the default config path

#### Scenario: Config path override
- **WHEN** the `CONFIG_PATH` environment variable is set
- **THEN** `entrypoint.sh` SHALL pass the config path as an argument to the Python process

### Requirement: .dockerignore
The project SHALL include a `.dockerignore` file that excludes development artifacts, git metadata, and test files from the build context.

#### Scenario: Build context is minimal
- **WHEN** a Docker build is initiated
- **THEN** the build context SHALL exclude `.git/`, `.venv/`, `tests/`, `__pycache__/`, `*.md`, `.github/`, and IDE config directories

### Requirement: Docker Compose service definition
The project SHALL include a `docker-compose.yml` with a prometheus-persister service following Delta-V compose conventions.

#### Scenario: Service starts with Kafka dependency
- **WHEN** `docker compose up prometheus-persister` is run
- **THEN** the service SHALL wait for Kafka to be healthy before starting, expose port 8000, and use environment variables for Kafka and Remote-Write configuration

#### Scenario: Health check in compose
- **WHEN** the service is defined in docker-compose.yml
- **THEN** the service SHALL include a health check with `interval`, `timeout`, `retries`, and `start_period` matching Delta-V patterns
