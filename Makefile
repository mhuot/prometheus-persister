VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
REVISION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
BUILD_DATE ?= $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
IMAGE_NAME ?= ghcr.io/mhuot/prometheus-persister
DOCKER_ARCH ?= linux/amd64

.PHONY: proto clean test lint format image push

proto:
	python -m grpc_tools.protoc \
		-I proto \
		--python_out=prometheus_persister/proto \
		proto/sink-message.proto \
		proto/collectionset.proto \
		proto/remote_write.proto

test:
	pytest

lint:
	pylint prometheus_persister
	black --check prometheus_persister tests

format:
	black prometheus_persister tests

image:
	docker buildx build \
		--platform $(DOCKER_ARCH) \
		--build-arg VERSION=$(VERSION) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg REVISION=$(REVISION) \
		--build-arg BUILD_BRANCH=$(BUILD_BRANCH) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--load \
		.

push:
	docker buildx build \
		--platform $(DOCKER_ARCH) \
		--build-arg VERSION=$(VERSION) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg REVISION=$(REVISION) \
		--build-arg BUILD_BRANCH=$(BUILD_BRANCH) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--push \
		.

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
