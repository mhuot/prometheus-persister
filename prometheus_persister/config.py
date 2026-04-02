"""Configuration loading from YAML with environment variable overrides."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class KafkaConfig:
    bootstrap_servers: str = "localhost:9092"
    consumer_group: str = "prometheus-persister"
    topic: str = "OpenNMS.Sink.CollectionSet"


@dataclass
class RemoteWriteConfig:
    url: str = "http://localhost:9090/api/v1/write"
    username: str = ""
    password: str = ""
    bearer_token: str = ""
    timeout: int = 30
    max_retries: int = 3


@dataclass
class BatchingConfig:
    max_size: int = 1000
    flush_interval: int = 5


@dataclass
class ChunkReassemblyConfig:
    ttl: int = 60


@dataclass
class ObservabilityConfig:
    metrics_port: int = 8000


@dataclass
class PersisterConfig:
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    remote_write: RemoteWriteConfig = field(default_factory=RemoteWriteConfig)
    batching: BatchingConfig = field(default_factory=BatchingConfig)
    chunk_reassembly: ChunkReassemblyConfig = field(
        default_factory=ChunkReassemblyConfig
    )
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


_ENV_OVERRIDES = {
    "KAFKA_BOOTSTRAP_SERVERS": ("kafka", "bootstrap_servers"),
    "KAFKA_CONSUMER_GROUP": ("kafka", "consumer_group"),
    "REMOTE_WRITE_URL": ("remote_write", "url"),
    "REMOTE_WRITE_USERNAME": ("remote_write", "username"),
    "REMOTE_WRITE_PASSWORD": ("remote_write", "password"),
    "REMOTE_WRITE_BEARER_TOKEN": ("remote_write", "bearer_token"),
}


def _apply_env_overrides(raw_config: dict) -> dict:
    for env_var, (section, key) in _ENV_OVERRIDES.items():
        value = os.environ.get(env_var)
        if value is not None:
            raw_config.setdefault(section, {})[key] = value
    return raw_config


def _build_config(raw_config: dict) -> PersisterConfig:
    kafka_data = raw_config.get("kafka", {})
    remote_write_data = raw_config.get("remote_write", {})
    batching_data = raw_config.get("batching", {})
    chunk_data = raw_config.get("chunk_reassembly", {})
    observability_data = raw_config.get("observability", {})

    return PersisterConfig(
        kafka=KafkaConfig(**{k: v for k, v in kafka_data.items() if v is not None}),
        remote_write=RemoteWriteConfig(
            **{k: v for k, v in remote_write_data.items() if v is not None}
        ),
        batching=BatchingConfig(
            **{k: v for k, v in batching_data.items() if v is not None}
        ),
        chunk_reassembly=ChunkReassemblyConfig(
            **{k: v for k, v in chunk_data.items() if v is not None}
        ),
        observability=ObservabilityConfig(
            **{k: v for k, v in observability_data.items() if v is not None}
        ),
    )


def validate_config(config: PersisterConfig) -> None:
    """Validate required fields and value ranges."""
    if not config.kafka.bootstrap_servers:
        raise ValueError("kafka.bootstrap_servers is required")

    if not config.remote_write.url:
        raise ValueError("remote_write.url is required")

    if config.batching.max_size < 1:
        raise ValueError("batching.max_size must be >= 1")

    if config.batching.flush_interval < 1:
        raise ValueError("batching.flush_interval must be >= 1")

    if config.chunk_reassembly.ttl < 1:
        raise ValueError("chunk_reassembly.ttl must be >= 1")

    if config.remote_write.timeout < 1:
        raise ValueError("remote_write.timeout must be >= 1")

    if config.remote_write.max_retries < 0:
        raise ValueError("remote_write.max_retries must be >= 0")

    if not 1 <= config.observability.metrics_port <= 65535:
        raise ValueError("observability.metrics_port must be between 1 and 65535")

    if config.remote_write.username and not config.remote_write.password:
        raise ValueError(
            "remote_write.password is required when username is provided"
        )


def load_config(config_path: str = "config.yaml") -> PersisterConfig:
    """Load configuration from YAML file with environment variable overrides."""
    raw_config = {}
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, encoding="utf-8") as file_handle:
            raw_config = yaml.safe_load(file_handle) or {}

    raw_config = _apply_env_overrides(raw_config)
    config = _build_config(raw_config)
    validate_config(config)
    return config
