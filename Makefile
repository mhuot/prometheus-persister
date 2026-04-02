.PHONY: proto clean test lint format

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

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
