"""Unit tests for remote_writer.py — batching, serialization, retry."""

from unittest.mock import MagicMock, patch

import snappy

from prometheus_persister.config import (
    BatchingConfig,
    PersisterConfig,
    RemoteWriteConfig,
)
from prometheus_persister.proto.remote_write_pb2 import WriteRequest
from prometheus_persister.remote_writer import RemoteWriteClient, _build_write_request
from prometheus_persister.transformer import PrometheusSample


def _make_sample(name="test_metric", value=1.0, timestamp_ms=1700000000000):
    return PrometheusSample(
        metric_name=name,
        labels={"host_id": "42", "host_name": "router1"},
        value=value,
        timestamp_ms=timestamp_ms,
    )


def _make_config(**overrides):
    remote_write_kwargs = {
        "url": "http://localhost:9090/api/v1/write",
        "timeout": 5,
        "max_retries": 2,
    }
    remote_write_kwargs.update(overrides.get("remote_write", {}))
    batching_kwargs = {"max_size": 3, "flush_interval": 5}
    batching_kwargs.update(overrides.get("batching", {}))

    return PersisterConfig(
        remote_write=RemoteWriteConfig(**remote_write_kwargs),
        batching=BatchingConfig(**batching_kwargs),
    )


class TestBuildWriteRequest:
    def test_serializes_single_sample(self):
        sample = _make_sample()
        serialized = _build_write_request([sample])
        write_request = WriteRequest()
        write_request.ParseFromString(serialized)

        assert len(write_request.timeseries) == 1
        time_series = write_request.timeseries[0]

        label_names = [label.name for label in time_series.labels]
        assert "__name__" in label_names
        assert "host_id" in label_names

        assert len(time_series.samples) == 1
        assert time_series.samples[0].value == 1.0
        assert time_series.samples[0].timestamp == 1700000000000

    def test_groups_same_series(self):
        sample_1 = _make_sample(value=1.0, timestamp_ms=1000)
        sample_2 = _make_sample(value=2.0, timestamp_ms=2000)

        serialized = _build_write_request([sample_1, sample_2])
        write_request = WriteRequest()
        write_request.ParseFromString(serialized)

        assert len(write_request.timeseries) == 1
        assert len(write_request.timeseries[0].samples) == 2

    def test_separates_different_metrics(self):
        sample_1 = _make_sample(name="metric_a")
        sample_2 = _make_sample(name="metric_b")

        serialized = _build_write_request([sample_1, sample_2])
        write_request = WriteRequest()
        write_request.ParseFromString(serialized)

        assert len(write_request.timeseries) == 2


class TestBatchTriggering:
    @patch("prometheus_persister.remote_writer.get_tracer")
    @patch("prometheus_persister.remote_writer.get_instruments")
    def test_flushes_at_batch_size(self, mock_instruments, mock_tracer):
        mock_tracer.return_value = MagicMock()
        mock_instruments.return_value = None
        config = _make_config(batching={"max_size": 2})
        client = RemoteWriteClient(config=config)

        with patch.object(client, "_send_with_retry") as mock_send:
            mock_send.return_value = 200
            client.add_samples([_make_sample(), _make_sample()])
            assert mock_send.called

    @patch("prometheus_persister.remote_writer.get_tracer")
    @patch("prometheus_persister.remote_writer.get_instruments")
    def test_does_not_flush_below_batch_size(self, mock_instruments, mock_tracer):
        mock_tracer.return_value = MagicMock()
        mock_instruments.return_value = None
        config = _make_config(batching={"max_size": 10})
        client = RemoteWriteClient(config=config)

        with patch.object(client, "_send_with_retry") as mock_send:
            client.add_samples([_make_sample()])
            assert not mock_send.called


class TestRetryLogic:
    def test_no_retry_on_4xx(self):
        config = _make_config(remote_write={"max_retries": 3})
        client = RemoteWriteClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch.object(client._session, "post", return_value=mock_response):
            result = client._send_with_retry(b"data", 10)
            assert result == 400
            assert client._session.post.call_count == 1

    def test_retries_on_5xx(self):
        config = _make_config(remote_write={"max_retries": 2})
        client = RemoteWriteClient(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(client._session, "post", return_value=mock_response):
            with patch("prometheus_persister.remote_writer.time.sleep"):
                result = client._send_with_retry(b"data", 10)
                assert result == 500
                assert client._session.post.call_count == 3  # 1 + 2 retries


class TestAuthentication:
    def test_bearer_token_in_headers(self):
        config = _make_config(
            remote_write={"bearer_token": "my-token"}
        )
        client = RemoteWriteClient(config=config)
        assert client._session.headers["Authorization"] == "Bearer my-token"

    def test_basic_auth_configured(self):
        config = _make_config(
            remote_write={"username": "user", "password": "pass"}
        )
        client = RemoteWriteClient(config=config)
        assert client._session.auth == ("user", "pass")
