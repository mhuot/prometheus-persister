## 1. Dockerfile Alignment

- [x] 1.1 Add OCI labels to Dockerfile via `ARG`/`LABEL` — `org.opencontainers.image.version`, `.created`, `.revision`, `.source`, `.title`, `.vendor`, `.licenses`
- [x] 1.2 Create non-root user `persister` (UID 10001, GID 10001) in the final stage and set `USER persister`
- [x] 1.3 Add `STOPSIGNAL SIGTERM` to the Dockerfile
- [x] 1.4 Add `HEALTHCHECK` instruction using `curl -sf http://localhost:8000/metrics || exit 1` with `interval=15s`, `timeout=5s`, `retries=3`, `start_period=30s`
- [x] 1.5 Create `entrypoint.sh` wrapper script — handles `CONFIG_PATH` env var override, exec's `python -m prometheus_persister`
- [x] 1.6 Update Dockerfile to `COPY entrypoint.sh` and use `ENTRYPOINT ["/app/entrypoint.sh"]`

## 2. Build Context

- [x] 2.1 Create `.dockerignore` excluding `.git/`, `.venv/`, `tests/`, `__pycache__/`, `*.md`, `.github/`, `.claude/`, `.gemini/`, `openspec/`, IDE configs
- [ ] 2.2 Update Makefile — add `image` target using `docker buildx build` with build args, add `push` target, update `clean` target

## 3. Docker Compose

- [ ] 3.1 Create `docker-compose.yml` with prometheus-persister service — depends_on kafka (service_healthy), environment variables for Kafka and Remote-Write, port 8000, health check with Delta-V timing parameters

## 4. CI Workflow

- [ ] 4.1 Create `.github/workflows/ci.yml` — trigger on push to main and PRs
- [ ] 4.2 Add steps: checkout, setup Python 3.11, pip install with caching, proto generation, black check, pylint, pytest
- [ ] 4.3 Add Docker build step (build only, no push) to validate the Dockerfile

## 5. Release Workflow

- [ ] 5.1 Create `.github/workflows/release.yml` — trigger on tags matching `v*`
- [ ] 5.2 Add test step: checkout, setup Python, install, proto gen, pytest (gates the release)
- [ ] 5.3 Add Docker BuildX setup with QEMU for multi-arch (amd64 + arm64)
- [ ] 5.4 Add GHCR login using `GITHUB_TOKEN` and optional Docker Hub login using secrets
- [ ] 5.5 Add build-and-push step with version tag (stripped `v` prefix) and `latest` tag, passing OCI label build args from git context

## 6. Proto Contract Check

- [ ] 6.1 Create `.github/workflows/proto-check.yml` — scheduled weekly (cron) and manual `workflow_dispatch`, fetches `sink-message.proto` and `collectionset.proto` from delta-v `main` branch, regenerates Python bindings, runs `pytest` against them
- [ ] 6.2 Add step to open a GitHub issue automatically if tests fail, with title "Proto contract break detected" and the failing test output in the body

## 7. Documentation

- [ ] 7.1 Update README.md — add CI badge, update Docker section with new build/run commands, document release process and image registries
- [ ] 7.2 Update README.md — document Docker Compose usage and Delta-V stack integration
- [ ] 7.3 Update README.md — add "Configuring Secrets" section with step-by-step instructions for setting up `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` in GitHub repo settings, and explain that GHCR uses the built-in `GITHUB_TOKEN` automatically
- [ ] 7.4 Update README.md — document the weekly proto contract check workflow and what to do when a break is detected
