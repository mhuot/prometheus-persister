"""CollectionSet protobuf to Prometheus sample transformation."""

import logging
import re
import time
from dataclasses import dataclass

from prometheus_persister.observability import get_instruments, get_tracer
from prometheus_persister.proto.collectionset_pb2 import (
    CollectionSet,
    CollectionSetResource,
    GenericTypeResource,
    InterfaceLevelResource,
    NodeLevelResource,
    NumericAttribute,
    ResponseTimeResource,
)

logger = logging.getLogger(__name__)

_INVALID_METRIC_CHARS = re.compile(r"[^a-zA-Z0-9_:]")
_LEADING_INVALID = re.compile(r"^[^a-zA-Z_:]")


@dataclass
class PrometheusSample:
    """A single Prometheus time-series sample."""

    metric_name: str
    labels: dict[str, str]
    value: float
    timestamp_ms: int


def sanitize_metric_name(name: str) -> str:
    """Replace invalid Prometheus metric name characters with underscores."""
    sanitized = _INVALID_METRIC_CHARS.sub("_", name)
    if _LEADING_INVALID.match(sanitized):
        sanitized = "_" + sanitized
    return sanitized


def _build_node_labels(node: NodeLevelResource) -> dict[str, str]:
    """Map NodeLevelResource fields to OTel-conformant Prometheus labels."""
    labels = {}
    if node.node_id:
        labels["host_id"] = str(node.node_id)
    if node.node_label:
        labels["host_name"] = node.node_label
    if node.foreign_source:
        labels["deltav_foreign_source"] = node.foreign_source
    if node.foreign_id:
        labels["deltav_foreign_id"] = node.foreign_id
    if node.location:
        labels["deltav_location"] = node.location
    return labels


def _build_interface_labels(interface: InterfaceLevelResource) -> dict[str, str]:
    """Map InterfaceLevelResource to labels including parent node labels."""
    labels = _build_node_labels(interface.node)
    if interface.instance:
        labels["deltav_instance"] = interface.instance
    if interface.if_index:
        labels["deltav_if_index"] = str(interface.if_index)
    return labels


def _build_generic_labels(generic: GenericTypeResource) -> dict[str, str]:
    """Map GenericTypeResource to labels including parent node labels."""
    labels = _build_node_labels(generic.node)
    if generic.type:
        labels["deltav_resource_type"] = generic.type
    if generic.instance:
        labels["deltav_instance"] = generic.instance
    return labels


def _build_response_time_labels(response: ResponseTimeResource) -> dict[str, str]:
    """Map ResponseTimeResource to labels."""
    labels = {}
    if response.instance:
        labels["deltav_instance"] = response.instance
    if response.location:
        labels["deltav_location"] = response.location
    return labels


def _build_resource_labels(resource: CollectionSetResource) -> dict[str, str]:
    """Build labels from a CollectionSetResource based on its resource type."""
    resource_type = resource.WhichOneof("resource")

    if resource_type == "node":
        labels = _build_node_labels(resource.node)
    elif resource_type == "interface":
        labels = _build_interface_labels(resource.interface)
    elif resource_type == "generic":
        labels = _build_generic_labels(resource.generic)
    elif resource_type == "response":
        labels = _build_response_time_labels(resource.response)
    else:
        labels = {}

    if resource.resource_id:
        labels["deltav_resource_id"] = resource.resource_id
    if resource.resource_type_name:
        labels["deltav_resource_type"] = resource.resource_type_name

    return labels


def _get_metric_value(attribute: NumericAttribute) -> float:
    """Extract metric value, preferring metric_value wrapper over value field."""
    if attribute.HasField("metric_value"):
        return attribute.metric_value.value
    return attribute.value


def _build_metric_name(attribute: NumericAttribute) -> str:
    """Build a sanitized Prometheus metric name from group and attribute name."""
    parts = []
    if attribute.group:
        parts.append(attribute.group)
    parts.append(attribute.name)
    metric_name = sanitize_metric_name("_".join(parts))

    if attribute.type == NumericAttribute.COUNTER:
        metric_name = metric_name + "_total"

    return metric_name


def transform_collection_set(raw_payload: bytes) -> list[PrometheusSample]:
    """Parse a CollectionSet protobuf and transform to Prometheus samples."""
    tracer = get_tracer()
    instruments = get_instruments()
    start_time = time.monotonic()

    with tracer.start_as_current_span("transform_collectionset") as span:
        collection_set = CollectionSet()
        try:
            collection_set.ParseFromString(raw_payload)
        except Exception:
            logger.exception(
                "Failed to deserialize CollectionSet payload (size=%d)",
                len(raw_payload),
            )
            return []

        timestamp_ms = collection_set.timestamp
        samples = []

        for resource in collection_set.resource:
            labels = _build_resource_labels(resource)

            for attribute in resource.numeric:
                metric_name = _build_metric_name(attribute)
                metric_value = _get_metric_value(attribute)

                samples.append(
                    PrometheusSample(
                        metric_name=metric_name,
                        labels=labels.copy(),
                        value=metric_value,
                        timestamp_ms=timestamp_ms,
                    )
                )

        resource_count = len(collection_set.resource)
        sample_count = len(samples)
        span.set_attribute("collectionset.resource_count", resource_count)
        span.set_attribute("collectionset.sample_count", sample_count)

        if instruments:
            duration = time.monotonic() - start_time
            instruments.transform_duration.record(duration)

        return samples
