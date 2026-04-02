"""Integration test — end-to-end with mock data and mock Remote-Write server."""

import http.server
import threading

import snappy

from prometheus_persister.config import (
    BatchingConfig,
    PersisterConfig,
    RemoteWriteConfig,
)
from prometheus_persister.proto.collectionset_pb2 import (
    CollectionSet,
    CollectionSetResource,
    NodeLevelResource,
    NumericAttribute,
)
from prometheus_persister.proto.remote_write_pb2 import WriteRequest
from prometheus_persister.proto.sink_message_pb2 import SinkMessage
from prometheus_persister.consumer import parse_sink_message
from prometheus_persister.remote_writer import RemoteWriteClient
from prometheus_persister.transformer import transform_collection_set


class MockRemoteWriteHandler(http.server.BaseHTTPRequestHandler):
    """Mock Prometheus Remote-Write endpoint that records requests."""

    received_requests = []

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        decompressed = snappy.decompress(body)
        write_request = WriteRequest()
        write_request.ParseFromString(decompressed)
        MockRemoteWriteHandler.received_requests.append(write_request)

        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP log output during tests


class TestEndToEnd:
    def setup_method(self):
        MockRemoteWriteHandler.received_requests.clear()

    def test_full_pipeline(self):
        """SinkMessage → parse → transform → Remote-Write → mock server."""
        # 1. Build a CollectionSet with a node resource and metric
        node = NodeLevelResource(
            node_id=42,
            node_label="switch1",
            foreign_source="network",
            foreign_id="sw1",
            location="NYC",
        )
        resource = CollectionSetResource(
            node=node,
            resource_id="node[42]",
            resource_type_name="node",
        )
        resource.numeric.append(
            NumericAttribute(
                group="mib2",
                name="ifInOctets",
                value=9876543.0,
                type=NumericAttribute.GAUGE,
            )
        )
        collection_set = CollectionSet(timestamp=1700000000000)
        collection_set.resource.append(resource)

        # 2. Wrap in SinkMessage
        sink_message = SinkMessage(
            message_id="test-msg-1",
            content=collection_set.SerializeToString(),
            current_chunk_number=0,
            total_chunks=1,
        )

        # 3. Parse SinkMessage (simulating consumer)
        parsed = parse_sink_message(sink_message.SerializeToString())
        assert parsed.message_id == "test-msg-1"

        # 4. Transform CollectionSet to Prometheus samples
        samples = transform_collection_set(parsed.content)
        assert len(samples) == 1
        assert samples[0].metric_name == "mib2_ifInOctets"
        assert samples[0].labels["host_id"] == "42"
        assert samples[0].labels["host_name"] == "switch1"
        assert samples[0].labels["deltav_location"] == "NYC"
        assert samples[0].value == 9876543.0

        # 5. Start mock Remote-Write server
        server = http.server.HTTPServer(("127.0.0.1", 0), MockRemoteWriteHandler)
        server_port = server.server_address[1]
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.start()

        try:
            # 6. Send via RemoteWriteClient
            config = PersisterConfig(
                remote_write=RemoteWriteConfig(
                    url=f"http://127.0.0.1:{server_port}/api/v1/write",
                    timeout=5,
                    max_retries=0,
                ),
                batching=BatchingConfig(max_size=100, flush_interval=60),
            )
            client = RemoteWriteClient(config=config)
            client.add_samples(samples)
            client.close()
        finally:
            server_thread.join(timeout=5)
            server.server_close()

        # 7. Verify the mock server received the data
        assert len(MockRemoteWriteHandler.received_requests) == 1
        write_request = MockRemoteWriteHandler.received_requests[0]
        assert len(write_request.timeseries) == 1

        time_series = write_request.timeseries[0]
        label_map = {
            label.name: label.value for label in time_series.labels
        }
        assert label_map["__name__"] == "mib2_ifInOctets"
        assert label_map["host_id"] == "42"
        assert label_map["deltav_location"] == "NYC"
        assert time_series.samples[0].value == 9876543.0
        assert time_series.samples[0].timestamp == 1700000000000
