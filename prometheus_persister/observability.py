"""OpenTelemetry SDK setup for metrics, traces, and structured logging."""

import logging
import os
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import start_http_server
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger(__name__)

_SERVICE_NAME = "prometheus-persister"

# Module-level references set during init
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None


class Instruments:
    """Container for all OTel metric instruments."""

    def __init__(self, meter: metrics.Meter):
        self.messages_consumed = meter.create_counter(
            name="prometheus_persister.messages_consumed",
            description="Total Kafka messages consumed",
        )
        self.samples_written = meter.create_counter(
            name="prometheus_persister.samples_written",
            description="Total samples sent via Remote-Write",
        )
        self.write_errors = meter.create_counter(
            name="prometheus_persister.write_errors",
            description="Total failed write attempts",
        )
        self.chunk_reassembly_timeouts = meter.create_counter(
            name="prometheus_persister.chunk_reassembly_timeouts",
            description="Expired incomplete chunks",
        )
        self.write_latency = meter.create_histogram(
            name="prometheus_persister.write_latency",
            description="Remote-Write request duration in seconds",
            unit="s",
        )
        self.transform_duration = meter.create_histogram(
            name="prometheus_persister.transform_duration",
            description="CollectionSet transform duration in seconds",
            unit="s",
        )
        self.batch_size = meter.create_histogram(
            name="prometheus_persister.batch_size",
            description="Number of samples per flush",
        )
        self.inflight_chunks = meter.create_up_down_counter(
            name="prometheus_persister.inflight_chunks",
            description="Incomplete chunks in reassembly buffer",
        )


_instruments: Optional[Instruments] = None


def get_tracer() -> trace.Tracer:
    """Return the package-level OTel tracer."""
    if _tracer is None:
        return trace.get_tracer(_SERVICE_NAME)
    return _tracer


def get_instruments() -> Optional[Instruments]:
    """Return the OTel metric instruments, or None if not initialized."""
    return _instruments


def setup_logging() -> None:
    """Configure structured JSON logging with trace/span correlation."""
    json_formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(json_formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(handler)


def init_observability(metrics_port: int = 8000) -> Instruments:
    """Initialize OTel MeterProvider, TracerProvider, and logging."""
    global _tracer, _meter, _instruments  # noqa: PLW0603

    resource = Resource.create({"service.name": _SERVICE_NAME})
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Metrics: always serve Prometheus /metrics, optionally export via OTLP
    prometheus_reader = PrometheusMetricReader()
    metric_readers = [prometheus_reader]

    if otlp_endpoint:
        otlp_metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        )
        metric_readers.append(otlp_metric_reader)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers,
    )
    metrics.set_meter_provider(meter_provider)

    # Traces: OTLP export when configured, no-op otherwise
    tracer_provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    _tracer = trace.get_tracer(_SERVICE_NAME)
    _meter = metrics.get_meter(_SERVICE_NAME)
    _instruments = Instruments(_meter)

    # Start Prometheus metrics HTTP server
    start_http_server(metrics_port)
    logger.info("Prometheus /metrics endpoint started on port %d", metrics_port)

    if otlp_endpoint:
        logger.info("OTLP export enabled to %s", otlp_endpoint)

    return _instruments
