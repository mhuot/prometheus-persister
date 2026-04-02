## ADDED Requirements

### Requirement: Scheduled proto contract validation
The system SHALL include a GitHub Actions workflow that validates the prometheus-persister test suite against the latest Delta-V proto files on a weekly schedule.

#### Scenario: Weekly scheduled run
- **WHEN** the weekly cron schedule triggers
- **THEN** the workflow SHALL fetch the latest `sink-message.proto` and `collectionset.proto` from the delta-v `main` branch, regenerate Python bindings, and run the full test suite

#### Scenario: Manual trigger
- **WHEN** a developer triggers the workflow via `workflow_dispatch`
- **THEN** the workflow SHALL perform the same fetch, regenerate, and test steps

### Requirement: Proto fetch from delta-v
The workflow SHALL fetch proto files directly from the delta-v repository without requiring a full clone.

#### Scenario: Fetch specific proto files
- **WHEN** the proto check workflow runs
- **THEN** it SHALL download `core/ipc/sink/common/src/main/proto/sink-message.proto` and `features/kafka/producer/src/main/proto/collectionset.proto` from the delta-v `main` branch

### Requirement: Automatic issue creation on failure
The workflow SHALL open a GitHub issue when the test suite fails against updated proto files, indicating a breaking change.

#### Scenario: Tests fail with new protos
- **WHEN** the test suite fails after regenerating bindings from the latest delta-v protos
- **THEN** the workflow SHALL open a GitHub issue with the title "Proto contract break detected in delta-v" and include the failing test output in the body

#### Scenario: Tests pass with new protos
- **WHEN** the test suite passes with the latest delta-v protos
- **THEN** the workflow SHALL NOT open an issue

#### Scenario: No duplicate issues
- **WHEN** an open issue with the same title already exists
- **THEN** the workflow SHALL NOT create a duplicate issue
