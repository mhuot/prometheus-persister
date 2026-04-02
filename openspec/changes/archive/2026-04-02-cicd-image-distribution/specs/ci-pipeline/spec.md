## ADDED Requirements

### Requirement: CI workflow triggers
The CI workflow SHALL run on pushes to `main` and on pull requests.

#### Scenario: Push to main triggers CI
- **WHEN** a commit is pushed to the `main` branch
- **THEN** the CI workflow SHALL execute all steps (lint, test, build)

#### Scenario: Pull request triggers CI
- **WHEN** a pull request is opened or updated
- **THEN** the CI workflow SHALL execute all steps

### Requirement: Python linting
The CI workflow SHALL run black and pylint to validate code quality.

#### Scenario: Formatting check
- **WHEN** the CI lint step runs
- **THEN** `black --check` SHALL be executed against all Python source and test files, failing the workflow if formatting violations are found

#### Scenario: Lint check
- **WHEN** the CI lint step runs
- **THEN** `pylint` SHALL be executed against the `prometheus_persister` package, failing the workflow if the score is below the configured threshold

### Requirement: Test execution
The CI workflow SHALL run the full pytest suite.

#### Scenario: Tests pass
- **WHEN** the CI test step runs
- **THEN** `pytest` SHALL execute all tests in the `tests/` directory and the workflow SHALL fail if any test fails

### Requirement: Docker image build validation
The CI workflow SHALL build the Docker image without pushing, to validate the Dockerfile.

#### Scenario: Docker build succeeds
- **WHEN** the CI build step runs
- **THEN** `docker build` SHALL complete successfully, confirming the Dockerfile is valid

### Requirement: Protobuf generation in CI
The CI workflow SHALL generate protobuf bindings before running tests.

#### Scenario: Proto generation before test
- **WHEN** the CI workflow runs
- **THEN** protobuf Python bindings SHALL be generated from `proto/` files before the test step executes
