"""Unit tests for transformer.py — resource types, sanitization, values."""

from google.protobuf.wrappers_pb2 import DoubleValue

from prometheus_persister.proto.collectionset_pb2 import (
    CollectionSet,
    CollectionSetResource,
    GenericTypeResource,
    InterfaceLevelResource,
    NodeLevelResource,
    NumericAttribute,
    ResponseTimeResource,
)
from prometheus_persister.transformer import (
    PrometheusSample,
    sanitize_metric_name,
    transform_collection_set,
)


def _make_collection_set(resources, timestamp_ms=1700000000000):
    collection_set = CollectionSet(timestamp=timestamp_ms)
    collection_set.resource.extend(resources)
    return collection_set.SerializeToString()


def _make_node_resource(
    node_id=42,
    node_label="router1",
    foreign_source="requisition",
    foreign_id="r1",
    location="Default",
):
    return NodeLevelResource(
        node_id=node_id,
        node_label=node_label,
        foreign_source=foreign_source,
        foreign_id=foreign_id,
        location=location,
    )


class TestSanitizeMetricName:
    def test_replaces_dots_with_underscores(self):
        assert sanitize_metric_name("if.octets.in") == "if_octets_in"

    def test_replaces_hyphens_with_underscores(self):
        assert sanitize_metric_name("mib2-interfaces") == "mib2_interfaces"

    def test_prepends_underscore_for_leading_digit(self):
        assert sanitize_metric_name("3com_errors") == "_3com_errors"

    def test_valid_name_unchanged(self):
        assert sanitize_metric_name("cpu_idle") == "cpu_idle"


class TestNodeLevelResource:
    def test_maps_all_fields(self):
        node = _make_node_resource()
        resource = CollectionSetResource(
            node=node,
            resource_id="node[42]",
            resource_type_name="node",
        )
        resource.numeric.append(
            NumericAttribute(
                group="mib2-interfaces",
                name="ifInOctets",
                value=1234.0,
                type=NumericAttribute.GAUGE,
            )
        )

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        sample = samples[0]
        assert sample.labels["host_id"] == "42"
        assert sample.labels["host_name"] == "router1"
        assert sample.labels["deltav_foreign_source"] == "requisition"
        assert sample.labels["deltav_foreign_id"] == "r1"
        assert sample.labels["deltav_location"] == "Default"
        assert sample.labels["deltav_resource_id"] == "node[42]"
        assert sample.metric_name == "mib2_interfaces_ifInOctets"
        assert sample.value == 1234.0
        assert sample.timestamp_ms == 1700000000000


class TestInterfaceLevelResource:
    def test_includes_parent_node_labels(self):
        interface = InterfaceLevelResource(
            node=_make_node_resource(),
            instance="eth0",
            if_index=2,
        )
        resource = CollectionSetResource(interface=interface)
        resource.numeric.append(
            NumericAttribute(
                group="mib2",
                name="ifSpeed",
                value=1000000000.0,
                type=NumericAttribute.GAUGE,
            )
        )

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        sample = samples[0]
        assert sample.labels["host_id"] == "42"
        assert sample.labels["host_name"] == "router1"
        assert sample.labels["deltav_instance"] == "eth0"
        assert sample.labels["deltav_if_index"] == "2"


class TestGenericTypeResource:
    def test_includes_type_and_instance(self):
        generic = GenericTypeResource(
            node=_make_node_resource(),
            type="diskIOTable",
            instance="/dev/sda",
        )
        resource = CollectionSetResource(generic=generic)
        resource.numeric.append(
            NumericAttribute(
                group="disk",
                name="reads",
                value=500.0,
                type=NumericAttribute.COUNTER,
            )
        )

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        sample = samples[0]
        assert sample.labels["deltav_resource_type"] == "diskIOTable"
        assert sample.labels["deltav_instance"] == "/dev/sda"
        assert sample.metric_name == "disk_reads_total"


class TestResponseTimeResource:
    def test_maps_instance_and_location(self):
        response = ResponseTimeResource(
            instance="192.168.1.1",
            location="Default",
        )
        resource = CollectionSetResource(response=response)
        resource.numeric.append(
            NumericAttribute(
                group="icmp",
                name="response_time",
                value=0.5,
                type=NumericAttribute.GAUGE,
            )
        )

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        sample = samples[0]
        assert sample.labels["deltav_instance"] == "192.168.1.1"
        assert sample.labels["deltav_location"] == "Default"
        assert "host_id" not in sample.labels


class TestMetricValueHandling:
    def test_prefers_metric_value_wrapper(self):
        node = _make_node_resource()
        resource = CollectionSetResource(node=node)
        attribute = NumericAttribute(
            group="test",
            name="metric",
            value=0.0,
            type=NumericAttribute.GAUGE,
        )
        attribute.metric_value.CopyFrom(DoubleValue(value=0.0))
        resource.numeric.append(attribute)

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        assert samples[0].value == 0.0

    def test_falls_back_to_value_field(self):
        node = _make_node_resource()
        resource = CollectionSetResource(node=node)
        resource.numeric.append(
            NumericAttribute(
                group="test",
                name="metric",
                value=42.5,
                type=NumericAttribute.GAUGE,
            )
        )

        payload = _make_collection_set([resource])
        samples = transform_collection_set(payload)

        assert len(samples) == 1
        assert samples[0].value == 42.5


class TestTimestampHandling:
    def test_uses_collection_set_timestamp(self):
        node = _make_node_resource()
        resource = CollectionSetResource(node=node)
        resource.numeric.append(
            NumericAttribute(
                group="test", name="m", value=1.0, type=NumericAttribute.GAUGE
            )
        )

        payload = _make_collection_set([resource], timestamp_ms=1700000000000)
        samples = transform_collection_set(payload)

        assert samples[0].timestamp_ms == 1700000000000


class TestInvalidPayload:
    def test_returns_empty_on_corrupt_payload(self):
        samples = transform_collection_set(b"not a valid protobuf!@#$")
        assert samples == []
