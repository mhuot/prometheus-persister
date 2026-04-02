"""Prometheus Remote-Write client with batching and retry."""

import logging
import threading
import time
from typing import Callable, Optional

import requests
import snappy
from opentelemetry import trace

from prometheus_persister.config import PersisterConfig
from prometheus_persister.observability import get_instruments, get_tracer
from prometheus_persister.proto.remote_write_pb2 import (
    Label,
    Sample,
    TimeSeries,
    WriteRequest,
)
from prometheus_persister.transformer import PrometheusSample

logger = logging.getLogger(__name__)


def _build_write_request(samples: list[PrometheusSample]) -> bytes:
    """Build a serialized WriteRequest protobuf from Prometheus samples."""
    series_map: dict[tuple, TimeSeries] = {}

    for sample in samples:
        label_key = tuple(sorted(sample.labels.items()))
        metric_key = (sample.metric_name, label_key)

        if metric_key not in series_map:
            time_series = TimeSeries()
            time_series.labels.append(
                Label(name="__name__", value=sample.metric_name)
            )
            for label_name, label_value in sorted(sample.labels.items()):
                time_series.labels.append(
                    Label(name=label_name, value=label_value)
                )
            series_map[metric_key] = time_series

        series_map[metric_key].samples.append(
            Sample(value=sample.value, timestamp=sample.timestamp_ms)
        )

    write_request = WriteRequest()
    write_request.timeseries.extend(series_map.values())
    return write_request.SerializeToString()


class RemoteWriteClient:
    """Batches and pushes Prometheus samples via Remote-Write v1."""

    def __init__(
        self,
        config: PersisterConfig,
        on_flush_success: Optional[Callable[[int], None]] = None,
        on_flush_error: Optional[Callable[[], None]] = None,
    ):
        self._config = config
        self._on_flush_success = on_flush_success
        self._on_flush_error = on_flush_error

        self._buffer: list[PrometheusSample] = []
        self._lock = threading.Lock()
        self._last_flush_time = time.monotonic()

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/x-protobuf",
                "Content-Encoding": "snappy",
                "X-Prometheus-Remote-Write-Version": "0.1.0",
            }
        )

        remote_write_config = config.remote_write
        if remote_write_config.bearer_token:
            self._session.headers["Authorization"] = (
                f"Bearer {remote_write_config.bearer_token}"
            )
        elif remote_write_config.username:
            self._session.auth = (
                remote_write_config.username,
                remote_write_config.password,
            )

    def add_samples(self, samples: list[PrometheusSample]) -> None:
        """Add samples to the batch buffer, flushing if batch size is reached."""
        with self._lock:
            self._buffer.extend(samples)
            if len(self._buffer) >= self._config.batching.max_size:
                self._flush()

    def check_flush_interval(self) -> None:
        """Flush if the flush interval has elapsed since the last flush."""
        elapsed = time.monotonic() - self._last_flush_time
        if elapsed >= self._config.batching.flush_interval:
            with self._lock:
                if self._buffer:
                    self._flush()
                self._last_flush_time = time.monotonic()

    def flush(self) -> None:
        """Force flush the current buffer."""
        with self._lock:
            if self._buffer:
                self._flush()

    def _flush(self) -> None:
        """Serialize, compress, and send the current buffer. Must hold _lock."""
        tracer = get_tracer()
        instruments = get_instruments()

        samples_to_send = self._buffer[:]
        self._buffer.clear()
        self._last_flush_time = time.monotonic()

        sample_count = len(samples_to_send)
        serialized_data = _build_write_request(samples_to_send)
        compressed_data = snappy.compress(serialized_data)

        if instruments:
            instruments.batch_size.record(sample_count)

        with tracer.start_as_current_span(
            "remote_write_batch",
            attributes={"batch.size": sample_count},
        ) as span:
            start_time = time.monotonic()
            status_code = self._send_with_retry(compressed_data, sample_count)
            duration = time.monotonic() - start_time

            if status_code is not None:
                span.set_attribute("http.response.status_code", status_code)

            if instruments:
                instruments.write_latency.record(duration)

                if status_code and status_code in (200, 204):
                    instruments.samples_written.add(sample_count)
                else:
                    instruments.write_errors.add(1)
                    span.set_status(
                        trace.StatusCode.ERROR,
                        f"Remote-Write failed with status {status_code}",
                    )

    def _send_with_retry(
        self, compressed_data: bytes, sample_count: int
    ) -> Optional[int]:
        """Send compressed data with exponential backoff retry. Returns status code."""
        max_retries = self._config.remote_write.max_retries
        timeout = self._config.remote_write.timeout
        remote_write_url = self._config.remote_write.url
        last_status_code = None

        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(
                    remote_write_url,
                    data=compressed_data,
                    timeout=timeout,
                )
                last_status_code = response.status_code

                if response.status_code in (200, 204):
                    logger.debug(
                        "Remote-Write success: %d samples", sample_count
                    )
                    return last_status_code

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        delay = float(retry_after)
                    else:
                        delay = 2**attempt
                    logger.warning(
                        "Rate limited (429), retrying in %.1fs", delay
                    )
                    time.sleep(delay)
                    continue

                if 400 <= response.status_code < 500:
                    logger.error(
                        "Remote-Write client error %d: %s",
                        response.status_code,
                        response.text[:500],
                    )
                    return last_status_code

                if response.status_code >= 500:
                    delay = 2**attempt
                    logger.warning(
                        "Remote-Write server error %d, retry %d/%d in %.1fs",
                        response.status_code,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    if attempt < max_retries:
                        time.sleep(delay)
                    continue

            except requests.exceptions.Timeout:
                delay = 2**attempt
                logger.warning(
                    "Remote-Write timeout, retry %d/%d in %.1fs",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                if attempt < max_retries:
                    time.sleep(delay)
                continue

            except requests.exceptions.RequestException:
                logger.exception("Remote-Write request failed")
                return None

        logger.error(
            "Remote-Write failed after %d retries, discarding %d samples",
            max_retries,
            sample_count,
        )
        return last_status_code

    def close(self) -> None:
        """Flush remaining samples and close the HTTP session."""
        self.flush()
        self._session.close()
