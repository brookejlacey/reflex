"""
GCP Cloud Monitoring integration for Reflex incident diagnostics.

Connects to Google Cloud Monitoring API to query time-series metrics,
detect anomalies in error rates and latency, and correlate metric spikes
with the incident timeline.
Falls back to realistic mock data when GCP credentials are unavailable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single data point in a time series."""

    timestamp: str
    value: float
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp, "value": self.value, "unit": self.unit}


@dataclass
class MetricSeries:
    """A named time series with metadata and data points."""

    metric_type: str
    display_name: str
    service: str
    points: list[MetricPoint] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def mean(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    @property
    def peak(self) -> float:
        if not self.points:
            return 0.0
        return max(p.value for p in self.points)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "display_name": self.display_name,
            "service": self.service,
            "points": [p.to_dict() for p in self.points],
            "labels": self.labels,
            "mean": round(self.mean, 4),
            "peak": round(self.peak, 4),
        }


@dataclass
class Anomaly:
    """A detected anomaly in a metric time series."""

    metric_type: str
    service: str
    detected_at: str
    value: float
    baseline: float
    deviation_factor: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_type": self.metric_type,
            "service": self.service,
            "detected_at": self.detected_at,
            "value": round(self.value, 4),
            "baseline": round(self.baseline, 4),
            "deviation_factor": round(self.deviation_factor, 2),
            "description": self.description,
        }


@dataclass
class MonitoringData:
    """Structured output from a Cloud Monitoring query."""

    series: list[MetricSeries]
    anomalies: list[Anomaly]
    time_range_start: str
    time_range_end: str
    services_queried: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "series": [s.to_dict() for s in self.series],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "services_queried": self.services_queried,
        }


class CloudMonitoringClient:
    """
    Client for querying Google Cloud Monitoring metrics and detecting anomalies.

    Automatically falls back to mock data when GCP credentials are not
    configured, enabling local development and demo usage.
    """

    # Standard metric types we query for incident diagnostics.
    DEFAULT_METRIC_TYPES = [
        "custom.googleapis.com/http/error_rate",
        "custom.googleapis.com/http/latency_p99",
        "compute.googleapis.com/instance/cpu/utilization",
        "custom.googleapis.com/db/connection_pool_usage",
    ]

    # If a metric value exceeds baseline * this factor, flag it as anomalous.
    ANOMALY_DEVIATION_THRESHOLD = 2.5

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ) -> None:
        self.project_id = project_id or os.environ.get("GCP_PROJECT_ID", "reflex-demo")
        self._client: Any = None
        self._demo_mode = False

        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self._init_client()

    def _init_client(self) -> None:
        """Initialize the Cloud Monitoring client, falling back to demo mode."""
        try:
            from google.cloud import monitoring_v3  # type: ignore[import-untyped]

            self._client = monitoring_v3.MetricServiceClient()
            logger.info("Connected to GCP Cloud Monitoring (project: %s)", self.project_id)
        except Exception as exc:
            logger.warning(
                "GCP Cloud Monitoring unavailable (%s). Running in demo mode.",
                exc,
            )
            self._demo_mode = True

    def query_incident_metrics(
        self,
        incident_id: str,
        service_names: Optional[list[str]] = None,
        metric_types: Optional[list[str]] = None,
        lookback_minutes: int = 60,
    ) -> MonitoringData:
        """
        Query Cloud Monitoring for metrics related to an incident.

        Args:
            incident_id: Identifier for the incident being investigated.
            service_names: Services to query metrics for. Defaults to ["payment-api"].
            metric_types: Specific metric types to query. Uses defaults if not provided.
            lookback_minutes: How far back from now to search, in minutes.

        Returns:
            MonitoringData with time-series data and detected anomalies.
        """
        services = service_names or ["payment-api"]
        metrics = metric_types or self.DEFAULT_METRIC_TYPES
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=lookback_minutes)

        if self._demo_mode:
            return self._mock_query(incident_id, services, start, now)

        return self._live_query(services, metrics, start, now)

    def _live_query(
        self,
        services: list[str],
        metric_types: list[str],
        start: datetime,
        end: datetime,
    ) -> MonitoringData:
        """Execute a live query against GCP Cloud Monitoring."""
        from google.cloud import monitoring_v3  # type: ignore[import-untyped]
        from google.protobuf.timestamp_pb2 import Timestamp  # type: ignore[import-untyped]

        all_series: list[MetricSeries] = []

        project_name = f"projects/{self.project_id}"

        start_pb = Timestamp()
        start_pb.FromDatetime(start)
        end_pb = Timestamp()
        end_pb.FromDatetime(end)

        interval = monitoring_v3.TimeInterval(
            start_time=start_pb,
            end_time=end_pb,
        )

        for metric_type in metric_types:
            for service in services:
                try:
                    filter_str = (
                        f'metric.type = "{metric_type}" AND '
                        f'resource.labels.service_name = "{service}"'
                    )
                    results = self._client.list_time_series(
                        request={
                            "name": project_name,
                            "filter": filter_str,
                            "interval": interval,
                            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                        }
                    )

                    for ts in results:
                        points = [
                            MetricPoint(
                                timestamp=p.interval.end_time.isoformat(),
                                value=p.value.double_value or p.value.int64_value,
                            )
                            for p in ts.points
                        ]
                        series = MetricSeries(
                            metric_type=metric_type,
                            display_name=metric_type.split("/")[-1],
                            service=service,
                            points=points,
                            labels=dict(ts.metric.labels),
                        )
                        all_series.append(series)

                except Exception as exc:
                    logger.error(
                        "Error querying metric %s for %s: %s",
                        metric_type, service, exc,
                    )

        anomalies = self._detect_anomalies(all_series)

        return MonitoringData(
            series=all_series,
            anomalies=anomalies,
            time_range_start=start.isoformat(),
            time_range_end=end.isoformat(),
            services_queried=services,
        )

    def _detect_anomalies(self, series_list: list[MetricSeries]) -> list[Anomaly]:
        """
        Simple anomaly detection: flag points that deviate significantly from
        the series mean. Uses a configurable deviation factor threshold.
        """
        anomalies: list[Anomaly] = []

        for series in series_list:
            if len(series.points) < 3:
                continue

            baseline = series.mean
            if baseline == 0:
                continue

            for point in series.points:
                factor = point.value / baseline
                if factor >= self.ANOMALY_DEVIATION_THRESHOLD:
                    anomalies.append(
                        Anomaly(
                            metric_type=series.metric_type,
                            service=series.service,
                            detected_at=point.timestamp,
                            value=point.value,
                            baseline=baseline,
                            deviation_factor=factor,
                            description=(
                                f"{series.display_name} spiked to {point.value:.2f} "
                                f"({factor:.1f}x baseline of {baseline:.2f}) "
                                f"on {series.service}"
                            ),
                        )
                    )

        return anomalies

    def _mock_query(
        self,
        incident_id: str,
        services: list[str],
        start: datetime,
        end: datetime,
    ) -> MonitoringData:
        """Return realistic mock monitoring data for demo mode."""
        primary_svc = services[0] if services else "payment-api"
        incident_time = end - timedelta(minutes=20)

        # Generate error rate time series with a clear spike.
        error_rate_points: list[MetricPoint] = []
        for i in range(12):
            t = start + timedelta(minutes=i * 5)
            # Normal: ~0.5%, spike at incident time to ~45%
            if abs((t - incident_time).total_seconds()) < 600:
                value = 0.45 + (0.1 * (i % 2))
            else:
                value = 0.005 + (0.002 * (i % 3))
            error_rate_points.append(
                MetricPoint(timestamp=t.isoformat(), value=round(value, 4), unit="%")
            )

        error_rate_series = MetricSeries(
            metric_type="custom.googleapis.com/http/error_rate",
            display_name="error_rate",
            service=primary_svc,
            points=error_rate_points,
            labels={"env": "production", "incident_id": incident_id},
        )

        # Generate p99 latency time series with a spike.
        latency_points: list[MetricPoint] = []
        for i in range(12):
            t = start + timedelta(minutes=i * 5)
            if abs((t - incident_time).total_seconds()) < 600:
                value = 12500.0 + (2000.0 * (i % 3))
            else:
                value = 180.0 + (40.0 * (i % 4))
            latency_points.append(
                MetricPoint(timestamp=t.isoformat(), value=round(value, 1), unit="ms")
            )

        latency_series = MetricSeries(
            metric_type="custom.googleapis.com/http/latency_p99",
            display_name="latency_p99",
            service=primary_svc,
            points=latency_points,
            labels={"env": "production", "incident_id": incident_id},
        )

        # DB connection pool usage.
        pool_points: list[MetricPoint] = []
        for i in range(12):
            t = start + timedelta(minutes=i * 5)
            if abs((t - incident_time).total_seconds()) < 600:
                value = 1.0  # 100% pool exhaustion
            else:
                value = 0.35 + (0.05 * (i % 3))
            pool_points.append(
                MetricPoint(timestamp=t.isoformat(), value=round(value, 3), unit="ratio")
            )

        pool_series = MetricSeries(
            metric_type="custom.googleapis.com/db/connection_pool_usage",
            display_name="connection_pool_usage",
            service=primary_svc,
            points=pool_points,
            labels={"env": "production", "incident_id": incident_id},
        )

        all_series = [error_rate_series, latency_series, pool_series]
        anomalies = self._detect_anomalies(all_series)

        return MonitoringData(
            series=all_series,
            anomalies=anomalies,
            time_range_start=start.isoformat(),
            time_range_end=end.isoformat(),
            services_queried=services,
        )

    def correlate_with_timeline(
        self,
        monitoring_data: MonitoringData,
        incident_start: datetime,
        incident_end: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Correlate monitoring anomalies with the incident timeline.

        Returns a summary of which anomalies occurred before, during, and after
        the incident window, helping establish causation vs. correlation.
        """
        end = incident_end or datetime.now(timezone.utc)
        before: list[dict[str, Any]] = []
        during: list[dict[str, Any]] = []
        after: list[dict[str, Any]] = []

        for anomaly in monitoring_data.anomalies:
            try:
                anomaly_time = datetime.fromisoformat(anomaly.detected_at)
            except ValueError:
                continue

            entry = anomaly.to_dict()
            if anomaly_time < incident_start:
                before.append(entry)
            elif anomaly_time > end:
                after.append(entry)
            else:
                during.append(entry)

        # The earliest anomaly before the incident is likely a leading indicator.
        leading_indicator = before[0] if before else None

        return {
            "incident_start": incident_start.isoformat(),
            "incident_end": end.isoformat(),
            "anomalies_before_incident": before,
            "anomalies_during_incident": during,
            "anomalies_after_incident": after,
            "leading_indicator": leading_indicator,
            "total_anomalies": len(before) + len(during) + len(after),
        }
