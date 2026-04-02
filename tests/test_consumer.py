"""Unit tests for consumer.py — SinkMessage parsing, chunk reassembly, TTL."""

import time

from prometheus_persister.consumer import ChunkReassembler, parse_sink_message
from prometheus_persister.proto.sink_message_pb2 import SinkMessage


class TestParseSinkMessage:
    def test_parses_valid_message(self):
        original = SinkMessage(
            message_id="msg-1",
            content=b"hello",
            current_chunk_number=0,
            total_chunks=1,
        )
        result = parse_sink_message(original.SerializeToString())
        assert result.message_id == "msg-1"
        assert result.content == b"hello"
        assert result.total_chunks == 1

    def test_parses_multi_chunk_fields(self):
        original = SinkMessage(
            message_id="msg-2",
            content=b"chunk1",
            current_chunk_number=0,
            total_chunks=3,
        )
        result = parse_sink_message(original.SerializeToString())
        assert result.current_chunk_number == 0
        assert result.total_chunks == 3


class TestChunkReassembler:
    def test_single_chunk_returns_immediately(self):
        reassembler = ChunkReassembler(ttl_seconds=60)
        result = reassembler.add_chunk("msg-1", 0, 1, b"full payload")
        assert result == b"full payload"
        assert reassembler.inflight_count == 0

    def test_multi_chunk_reassembly(self):
        reassembler = ChunkReassembler(ttl_seconds=60)
        result_1 = reassembler.add_chunk("msg-1", 0, 3, b"aaa")
        assert result_1 is None
        assert reassembler.inflight_count == 1

        result_2 = reassembler.add_chunk("msg-1", 1, 3, b"bbb")
        assert result_2 is None

        result_3 = reassembler.add_chunk("msg-1", 2, 3, b"ccc")
        assert result_3 == b"aaabbbccc"
        assert reassembler.inflight_count == 0

    def test_out_of_order_chunks(self):
        reassembler = ChunkReassembler(ttl_seconds=60)
        reassembler.add_chunk("msg-1", 2, 3, b"ccc")
        reassembler.add_chunk("msg-1", 0, 3, b"aaa")
        result = reassembler.add_chunk("msg-1", 1, 3, b"bbb")
        assert result == b"aaabbbccc"

    def test_concurrent_messages(self):
        reassembler = ChunkReassembler(ttl_seconds=60)
        reassembler.add_chunk("msg-1", 0, 2, b"aa")
        reassembler.add_chunk("msg-2", 0, 2, b"xx")

        result_1 = reassembler.add_chunk("msg-1", 1, 2, b"bb")
        assert result_1 == b"aabb"
        assert reassembler.inflight_count == 1

        result_2 = reassembler.add_chunk("msg-2", 1, 2, b"yy")
        assert result_2 == b"xxyy"
        assert reassembler.inflight_count == 0

    def test_ttl_eviction(self):
        timeout_count = 0

        def on_timeout():
            nonlocal timeout_count
            timeout_count += 1

        reassembler = ChunkReassembler(ttl_seconds=0, on_timeout=on_timeout)
        reassembler.add_chunk("msg-1", 0, 3, b"aaa")

        time.sleep(0.01)
        evicted = reassembler.evict_stale()

        assert evicted == 1
        assert reassembler.inflight_count == 0
        assert timeout_count == 1

    def test_no_eviction_within_ttl(self):
        reassembler = ChunkReassembler(ttl_seconds=300)
        reassembler.add_chunk("msg-1", 0, 3, b"aaa")

        evicted = reassembler.evict_stale()
        assert evicted == 0
        assert reassembler.inflight_count == 1
