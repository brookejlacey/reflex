"""
GCP Cloud Logging integration for Reflex incident diagnostics.

Connects to Google Cloud Logging API to query error logs, extract stack traces,
and return structured diagnostic data for the incident analysis pipeline.
Falls back to realistic mock data when GCP credentials are unavailable (demo mode).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """A single structured log entry extracted from Cloud Logging."""

    timestamp: str
    severity: str
    service: str
    message: str
    stack_trace: Optional[str] = None
    labels: dict[str, str] = field(default_factory=dict)
    resource: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "severity": self.severity,
            "service": self.service,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "labels": self.labels,
            "resource": self.resource,
        }


@dataclass
class DiagnosticData:
    """Structured diagnostic output from a Cloud Logging query."""

    entries: list[LogEntry]
    query_filter: str
    time_range_start: str
    time_range_end: str
    total_entries_scanned: int
    error_count: int
    unique_errors: list[str]
    services_affected: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "query_filter": self.query_filter,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "total_entries_scanned": self.total_entries_scanned,
            "error_count": self.error_count,
            "unique_errors": self.unique_errors,
            "services_affected": self.services_affected,
        }


class CloudLoggingClient:
    """
    Client for querying Google Cloud Logging for incident-related log data.

    Automatically falls back to mock data when GCP credentials are not
    configured, enabling local development and demo usage.
    """

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
        """Initialize the Cloud Logging client, falling back to demo mode."""
        try:
            from google.cloud import logging as cloud_logging  # type: ignore[import-untyped]

            self._client = cloud_logging.Client(project=self.project_id)
            logger.info("Connected to GCP Cloud Logging (project: %s)", self.project_id)
        except Exception as exc:
            logger.warning(
                "GCP Cloud Logging unavailable (%s). Running in demo mode with mock data.",
                exc,
            )
            self._demo_mode = True

    def query_incident_logs(
        self,
        incident_id: str,
        service_name: Optional[str] = None,
        severity_min: str = "ERROR",
        lookback_minutes: int = 60,
        max_entries: int = 200,
    ) -> DiagnosticData:
        """
        Query Cloud Logging for log entries related to an incident.

        Args:
            incident_id: Identifier for the incident being investigated.
            service_name: Optional GCP service or application name to filter on.
            severity_min: Minimum severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            lookback_minutes: How far back from now to search, in minutes.
            max_entries: Maximum number of log entries to return.

        Returns:
            DiagnosticData with matching log entries and summary statistics.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(minutes=lookback_minutes)

        if self._demo_mode:
            return self._mock_query(incident_id, service_name, severity_min, start, now)

        return self._live_query(
            incident_id, service_name, severity_min, start, now, max_entries
        )

    def _live_query(
        self,
        incident_id: str,
        service_name: Optional[str],
        severity_min: str,
        start: datetime,
        end: datetime,
        max_entries: int,
    ) -> DiagnosticData:
        """Execute a live query against GCP Cloud Logging."""
        severity_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        min_index = severity_levels.index(severity_min) if severity_min in severity_levels else 3

        filter_parts = [
            f'timestamp >= "{start.isoformat()}"',
            f'timestamp <= "{end.isoformat()}"',
            f"severity >= {severity_levels[min_index]}",
        ]
        if service_name:
            filter_parts.append(f'resource.labels.service_name = "{service_name}"')

        query_filter = " AND ".join(filter_parts)
        logger.info("Querying Cloud Logging: %s", query_filter)

        entries: list[LogEntry] = []
        total_scanned = 0

        try:
            iterator = self._client.list_entries(
                filter_=query_filter,
                order_by="timestamp desc",
                page_size=max_entries,
            )
            for entry in iterator:
                total_scanned += 1
                if total_scanned > max_entries:
                    break

                payload = entry.payload if isinstance(entry.payload, dict) else {}
                message = (
                    payload.get("message", str(entry.payload))
                    if isinstance(entry.payload, dict)
                    else str(entry.payload)
                )
                stack_trace = payload.get("stack_trace") or payload.get("stackTrace")

                log_entry = LogEntry(
                    timestamp=entry.timestamp.isoformat() if entry.timestamp else "",
                    severity=entry.severity or "UNKNOWN",
                    service=getattr(entry.resource, "labels", {}).get("service_name", "unknown"),
                    message=message,
                    stack_trace=stack_trace,
                    labels=dict(entry.labels) if entry.labels else {},
                    resource=dict(getattr(entry.resource, "labels", {})),
                )
                entries.append(log_entry)

        except Exception as exc:
            logger.error("Error querying Cloud Logging: %s", exc)
            raise

        unique_errors = list({e.message.split("\n")[0][:120] for e in entries})
        services_affected = list({e.service for e in entries if e.service != "unknown"})

        return DiagnosticData(
            entries=entries,
            query_filter=query_filter,
            time_range_start=start.isoformat(),
            time_range_end=end.isoformat(),
            total_entries_scanned=total_scanned,
            error_count=len(entries),
            unique_errors=unique_errors,
            services_affected=services_affected,
        )

    def _mock_query(
        self,
        incident_id: str,
        service_name: Optional[str],
        severity_min: str,
        start: datetime,
        end: datetime,
    ) -> DiagnosticData:
        """Return realistic mock data for demo mode."""
        svc = service_name or "payment-api"
        base_time = end - timedelta(minutes=15)

        mock_entries = [
            LogEntry(
                timestamp=(base_time + timedelta(seconds=0)).isoformat(),
                severity="ERROR",
                service=svc,
                message="Connection pool exhausted: max_connections=50 reached",
                stack_trace=(
                    "Traceback (most recent call last):\n"
                    '  File "/app/db/pool.py", line 142, in acquire\n'
                    "    raise PoolExhaustedError(f'max_connections={self.max_size} reached')\n"
                    "db.exceptions.PoolExhaustedError: max_connections=50 reached"
                ),
                labels={"env": "production", "incident_id": incident_id},
                resource={"service_name": svc, "region": "us-central1"},
            ),
            LogEntry(
                timestamp=(base_time + timedelta(seconds=12)).isoformat(),
                severity="CRITICAL",
                service=svc,
                message="Database query timeout after 30000ms on payments.transactions",
                stack_trace=(
                    "Traceback (most recent call last):\n"
                    '  File "/app/services/payment.py", line 87, in process_payment\n'
                    "    result = await db.execute(query, timeout=30.0)\n"
                    '  File "/app/db/session.py", line 203, in execute\n'
                    "    raise QueryTimeoutError(f'timeout after {timeout_ms}ms')\n"
                    "db.exceptions.QueryTimeoutError: timeout after 30000ms"
                ),
                labels={"env": "production", "incident_id": incident_id},
                resource={"service_name": svc, "region": "us-central1"},
            ),
            LogEntry(
                timestamp=(base_time + timedelta(seconds=30)).isoformat(),
                severity="ERROR",
                service="auth-service",
                message="Upstream dependency timeout: payment-api health check failed",
                labels={"env": "production", "incident_id": incident_id},
                resource={"service_name": "auth-service", "region": "us-central1"},
            ),
            LogEntry(
                timestamp=(base_time + timedelta(seconds=45)).isoformat(),
                severity="ERROR",
                service=svc,
                message="Connection pool exhausted: max_connections=50 reached",
                stack_trace=(
                    "Traceback (most recent call last):\n"
                    '  File "/app/db/pool.py", line 142, in acquire\n'
                    "    raise PoolExhaustedError(f'max_connections={self.max_size} reached')\n"
                    "db.exceptions.PoolExhaustedError: max_connections=50 reached"
                ),
                labels={"env": "production", "incident_id": incident_id},
                resource={"service_name": svc, "region": "us-central1"},
            ),
            LogEntry(
                timestamp=(base_time + timedelta(seconds=90)).isoformat(),
                severity="WARNING",
                service=svc,
                message="Request queue depth exceeding threshold: 847/100",
                labels={"env": "production", "incident_id": incident_id},
                resource={"service_name": svc, "region": "us-central1"},
            ),
        ]

        # Filter by severity
        severity_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        min_level = severity_order.get(severity_min, 3)
        filtered = [e for e in mock_entries if severity_order.get(e.severity, 0) >= min_level]

        unique_errors = list({e.message.split("\n")[0][:120] for e in filtered})
        services_affected = list({e.service for e in filtered})

        return DiagnosticData(
            entries=filtered,
            query_filter=f"severity >= {severity_min} (demo mode, incident: {incident_id})",
            time_range_start=start.isoformat(),
            time_range_end=end.isoformat(),
            total_entries_scanned=len(filtered),
            error_count=len(filtered),
            unique_errors=unique_errors,
            services_affected=services_affected,
        )

    def extract_stack_traces(self, diagnostic: DiagnosticData) -> list[dict[str, str]]:
        """
        Extract and deduplicate stack traces from diagnostic data.

        Returns a list of dicts with keys: service, error_summary, stack_trace.
        """
        seen: set[str] = set()
        traces: list[dict[str, str]] = []

        for entry in diagnostic.entries:
            if not entry.stack_trace:
                continue
            key = entry.stack_trace.strip()
            if key in seen:
                continue
            seen.add(key)
            traces.append({
                "service": entry.service,
                "error_summary": entry.message.split("\n")[0][:200],
                "stack_trace": entry.stack_trace,
            })

        return traces
