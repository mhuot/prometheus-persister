"""Entry point for the Prometheus Persister service."""

import logging
import signal
import sys

from prometheus_persister.config import load_config
from prometheus_persister.consumer import CollectionSetConsumer
from prometheus_persister.observability import init_observability, setup_logging
from prometheus_persister.remote_writer import RemoteWriteClient
from prometheus_persister.transformer import transform_collection_set

logger = logging.getLogger(__name__)


def main() -> None:
    """Load config, initialize OTel, wire pipeline, and start consuming."""
    setup_logging()

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    try:
        config = load_config(config_path)
    except (ValueError, FileNotFoundError) as error:
        logger.error("Configuration error: %s", error)
        sys.exit(1)

    init_observability(config.observability.metrics_port)

    remote_writer = RemoteWriteClient(config=config)

    def handle_payload(raw_payload: bytes) -> None:
        samples = transform_collection_set(raw_payload)
        if samples:
            remote_writer.add_samples(samples)

    consumer = CollectionSetConsumer(
        config=config,
        message_handler=handle_payload,
    )

    def shutdown_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down...", signal_name)
        consumer.stop()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    logger.info("Prometheus Persister starting...")
    try:
        consumer.start()
    finally:
        logger.info("Flushing remaining samples...")
        remote_writer.close()
        consumer.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
