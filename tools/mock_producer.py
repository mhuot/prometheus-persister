"""Publish mock CollectionSet messages to Kafka for testing."""

import sys
import time
import uuid
import random

from confluent_kafka import Producer

# Add parent to path for proto imports
sys.path.insert(0, ".")

from prometheus_persister.proto.collectionset_pb2 import (
    CollectionSet,
    CollectionSetResource,
    InterfaceLevelResource,
    NodeLevelResource,
    NumericAttribute,
)
from prometheus_persister.proto.sink_message_pb2 import SinkMessage


NODES = [
    {"node_id": 1, "label": "router-core", "location": "Default", "fs": "home-network", "fid": "1"},
    {"node_id": 2, "label": "switch-floor1", "location": "Default", "fs": "home-network", "fid": "2"},
    {"node_id": 3, "label": "ap-office", "location": "Default", "fs": "home-network", "fid": "3"},
    {"node_id": 4, "label": "nas-storage", "location": "Default", "fs": "home-network", "fid": "4"},
    {"node_id": 5, "label": "firewall-edge", "location": "Default", "fs": "home-network", "fid": "5"},
]

INTERFACES = ["eth0", "eth1", "ge-0/0/0", "ge-0/0/1"]


def build_collection_set(node_info):
    """Build a realistic CollectionSet for a single node."""
    node = NodeLevelResource(
        node_id=node_info["node_id"],
        node_label=node_info["label"],
        foreign_source=node_info["fs"],
        foreign_id=node_info["fid"],
        location=node_info["location"],
    )

    collection_set = CollectionSet(timestamp=int(time.time() * 1000))

    for iface in random.sample(INTERFACES, k=random.randint(2, len(INTERFACES))):
        interface = InterfaceLevelResource(
            node=node,
            instance=iface,
            if_index=INTERFACES.index(iface) + 1,
        )
        resource = CollectionSetResource(
            interface=interface,
            resource_id=f"node[{node_info['node_id']}].interfaceSnmp[{iface}]",
            resource_type_name="interfaceSnmp",
        )

        base_in = random.randint(1_000_000, 100_000_000)
        base_out = random.randint(500_000, 50_000_000)

        resource.numeric.append(
            NumericAttribute(
                group="mib2-interfaces",
                name="ifInOctets",
                value=float(base_in),
                type=NumericAttribute.COUNTER,
            )
        )
        resource.numeric.append(
            NumericAttribute(
                group="mib2-interfaces",
                name="ifOutOctets",
                value=float(base_out),
                type=NumericAttribute.COUNTER,
            )
        )
        resource.numeric.append(
            NumericAttribute(
                group="mib2-interfaces",
                name="ifSpeed",
                value=1_000_000_000.0,
                type=NumericAttribute.GAUGE,
            )
        )
        resource.numeric.append(
            NumericAttribute(
                group="mib2-interfaces",
                name="ifInErrors",
                value=float(random.randint(0, 5)),
                type=NumericAttribute.COUNTER,
            )
        )

        collection_set.resource.append(resource)

    return collection_set


def wrap_in_sink_message(collection_set_bytes):
    """Wrap a serialized CollectionSet in a SinkMessage envelope."""
    return SinkMessage(
        message_id=str(uuid.uuid4()),
        content=collection_set_bytes,
        current_chunk_number=0,
        total_chunks=1,
    ).SerializeToString()


def main():
    bootstrap_servers = sys.argv[1] if len(sys.argv) > 1 else "localhost:19092"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    producer = Producer({"bootstrap.servers": bootstrap_servers})
    topic = "OpenNMS.Sink.CollectionSet"

    print(f"Publishing mock CollectionSets to {bootstrap_servers} topic={topic} every {interval}s")
    print(f"Nodes: {[n['label'] for n in NODES]}")

    cycle = 0
    while True:
        cycle += 1
        for node_info in NODES:
            collection_set = build_collection_set(node_info)
            message = wrap_in_sink_message(collection_set.SerializeToString())
            producer.produce(topic, value=message)

        producer.flush()
        sample_count = sum(
            len(INTERFACES) * 4 for _ in NODES  # approximate
        )
        print(f"[cycle {cycle}] Published {len(NODES)} CollectionSets (~{sample_count} metrics)")

        time.sleep(interval)


if __name__ == "__main__":
    main()
