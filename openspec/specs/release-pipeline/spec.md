## ADDED Requirements

### Requirement: Tag-triggered release
The release workflow SHALL trigger on git tags matching the pattern `v*`.

#### Scenario: Version tag triggers release
- **WHEN** a tag like `v0.1.0` is pushed
- **THEN** the release workflow SHALL build and publish container images

#### Scenario: Non-version tag does not trigger
- **WHEN** a tag not matching `v*` is pushed
- **THEN** the release workflow SHALL NOT run

### Requirement: Multi-architecture image build
The release workflow SHALL build container images for both `linux/amd64` and `linux/arm64` architectures using Docker BuildX.

#### Scenario: Multi-arch manifest published
- **WHEN** the release workflow completes
- **THEN** the published image SHALL contain manifests for both amd64 and arm64 platforms

### Requirement: Image tagging strategy
The release workflow SHALL tag images with the version extracted from the git tag and with `latest`.

#### Scenario: Version tag applied
- **WHEN** the git tag is `v0.2.0`
- **THEN** the image SHALL be tagged as `<registry>/prometheus-persister:0.2.0` (without the `v` prefix) and `<registry>/prometheus-persister:latest`

### Requirement: GHCR image publishing
The release workflow SHALL push images to GitHub Container Registry (ghcr.io).

#### Scenario: GHCR push
- **WHEN** the release workflow runs
- **THEN** images SHALL be pushed to `ghcr.io/mhuot/prometheus-persister` with version and latest tags

### Requirement: Optional Docker Hub publishing
The release workflow SHALL push to Docker Hub when `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets are configured.

#### Scenario: Docker Hub secrets present
- **WHEN** Docker Hub secrets are configured in the repository
- **THEN** images SHALL additionally be pushed to `docker.io/mhuot/prometheus-persister`

#### Scenario: Docker Hub secrets absent
- **WHEN** Docker Hub secrets are not configured
- **THEN** the workflow SHALL skip Docker Hub push without failing

### Requirement: OCI labels populated at build time
The release workflow SHALL pass build arguments for OCI labels including version, build date, git revision, and source URL.

#### Scenario: Labels from CI context
- **WHEN** the release image is built
- **THEN** the build SHALL pass `VERSION` (from tag), `BUILD_DATE` (ISO 8601), `REVISION` (git SHA), and `SOURCE` (repository URL) as build args

### Requirement: Tests run before publish
The release workflow SHALL run the full test suite before building and pushing images.

#### Scenario: Tests gate release
- **WHEN** any test fails during the release workflow
- **THEN** the image SHALL NOT be built or pushed
