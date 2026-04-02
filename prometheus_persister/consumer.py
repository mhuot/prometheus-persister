"""Kafka consumer with SinkMessage envelope parsing and chunk reassembly."""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from confluent_kafka import Consumer, KafkaError, KafkaException

from opentelemetry import trace

from prometheus_persister.config import PersisterConfig
from prometheus_persister.observability import get_instruments, get_tracer
from prometheus_persister.proto.sink_message_pb2 import SinkMessage

logger = logging.getLogger(__name__)


@dataclass
class ChunkBuffer:
    """Buffer for reassembling chunked SinkMessage payloads."""

    total_chunks: int
    chunks: dict[int, bytes] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)

    @property
    def is_complete(self) -> bool:
        return len(self.chunks) == self.total_chunks


class ChunkReassembler:
    """Manages in-flight chunk buffers with TTL-based eviction."""

    def __init__(self, ttl_seconds: int, on_timeout: Optional[Callable] = None):
        self._ttl_seconds = ttl_seconds
        self._buffers: dict[str, ChunkBuffer] = {}
        self._on_timeout = on_timeout

    @property
    def inflight_count(self) -> int:
        return len(self._buffers)

    def add_chunk(
        self, message_id: str, chunk_number: int, total_chunks: int, content: bytes
    ) -> Optional[bytes]:
        """Add a chunk and return the complete payload if all chunks arrived."""
        if message_id not in self._buffers:
            self._buffers[message_id] = ChunkBuffer(total_chunks=total_chunks)

        buffer = self._buffers[message_id]
        buffer.chunks[chunk_number] = content

        if buffer.is_complete:
            complete_payload = b"".join(buffer.chunks[i] for i in range(total_chunks))
            del self._buffers[message_id]
            return complete_payload

        return None

    def evict_stale(self) -> int:
        """Remove buffers that have exceeded the TTL. Returns count evicted."""
        now = time.monotonic()
        stale_ids = [
            message_id
            for message_id, buffer in self._buffers.items()
            if (now - buffer.created_at) > self._ttl_seconds
        ]
        for message_id in stale_ids:
            logger.warning(
                "Evicting incomplete chunk buffer for message_id=%s", message_id
            )
            del self._buffers[message_id]
            if self._on_timeout:
                self._on_timeout()
        return len(stale_ids)


def parse_sink_message(raw_value: bytes) -> SinkMessage:
    """Deserialize raw Kafka message value as a SinkMessage protobuf."""
    sink_message = SinkMessage()
    sink_message.ParseFromString(raw_value)
    return sink_message


class CollectionSetConsumer:
    """Kafka consumer that parses SinkMessage envelopes and yields payloads."""

    def __init__(
        self,
        config: PersisterConfig,
        message_handler: Callable[[bytes], None],
    ):
        self._config = config
        self._message_handler = message_handler
        self._running = False

        self._reassembler = ChunkReassembler(
            ttl_seconds=config.chunk_reassembly.ttl,
        )

        self._consumer = Consumer(
            {
                "bootstrap.servers": config.kafka.bootstrap_servers,
                "group.id": config.kafka.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )

    @property
    def reassembler(self) -> ChunkReassembler:
        return self._reassembler

    def start(self) -> None:
        """Subscribe and start the polling loop."""
        self._consumer.subscribe([self._config.kafka.topic])
        self._running = True
        logger.info(
            "Subscribed to topic=%s group=%s",
            self._config.kafka.topic,
            self._config.kafka.consumer_group,
        )

        while self._running:
            self._reassembler.evict_stale()
            message = self._consumer.poll(timeout=1.0)
            if message is None:
                continue

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error: %s", message.error())
                raise KafkaException(message.error())

            self._process_message(message)

    def _process_message(self, message) -> None:
        """Parse SinkMessage envelope, reassemble chunks, and dispatch."""
        tracer = get_tracer()
        instruments = get_instruments()

        with tracer.start_as_current_span(
            "consume_message",
            attributes={
                "messaging.system": "kafka",
                "messaging.destination.name": self._config.kafka.topic,
                "messaging.kafka.message.offset": message.offset(),
            },
        ):
            if instruments:
                instruments.messages_consumed.add(1)

            try:
                sink_message = parse_sink_message(message.value())
            except Exception:
                logger.exception("Failed to parse SinkMessage envelope")
                self._consumer.commit(message=message, asynchronous=False)
                return

            if sink_message.total_chunks <= 1:
                payload = sink_message.content
            else:
                with tracer.start_as_current_span(
                    "reassemble_chunks",
                    attributes={
                        "messaging.message_id": sink_message.message_id,
                        "chunks.total": sink_message.total_chunks,
                    },
                ):
                    payload = self._reassembler.add_chunk(
                        message_id=sink_message.message_id,
                        chunk_number=sink_message.current_chunk_number,
                        total_chunks=sink_message.total_chunks,
                        content=sink_message.content,
                    )

            if payload is not None:
                try:
                    self._message_handler(payload)
                except Exception:
                    logger.exception("Failed to handle CollectionSet payload")

            self._consumer.commit(message=message, asynchronous=False)

    def stop(self) -> None:
        """Stop the consumer loop gracefully."""
        logger.info("Stopping consumer...")
        self._running = False

    def close(self) -> None:
        """Close the Kafka consumer connection."""
        try:
            self._consumer.close()
        except Exception:
            logger.exception("Error closing Kafka consumer")
