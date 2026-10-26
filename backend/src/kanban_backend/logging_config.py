"""Structured (JSON) application logging, correlated to the active
OpenTelemetry trace.

Every log record this app emits - via `logging.getLogger("kanban_backend")`
or a child of it - goes to stdout as one JSON object per line, always
including `trace_id`/`span_id` from whatever span is active when the log
call happens (null if none is, e.g. at startup before a request exists).
That correlation works independently of whether OTLP export is configured
at all - it's a property of the stdout JSON, not of shipping logs
anywhere - so `docker logs`/`grep` already lets you pull every log line
for one request by its trace ID, even with no collector running.

When OTEL_EXPORTER_OTLP_ENDPOINT *is* set (see telemetry.py's own
comment on why that's the gate), the same records are additionally
exported via OTLP to the collector, which forwards them to Loki (see
observability/otel-collector-config.yaml) - the OTel SDK's LoggingHandler
does its own, separate trace-context correlation for that path, using
the real OTel LogRecord fields Loki/Grafana understand for trace-to-logs
linking, not the plain JSON fields below.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

# Attributes every stdlib LogRecord already has - anything else present
# on the record came from a caller's `extra={...}` and belongs in the
# JSON payload as a structured field.
_STANDARD_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class _TraceContextFilter(logging.Filter):
    """Attaches the active span's trace_id/span_id to every record, so
    the JSON formatter below can include them - independent of whether
    OTel's own LoggingHandler is also attached."""

    def filter(self, record: logging.LogRecord) -> bool:
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(resource: Resource) -> None:
    """Call once, from setup_telemetry. `resource` is the same one
    traces/metrics use, so logs carry the same service.name/
    deployment.environment/service.version."""
    logger = logging.getLogger("kanban_backend")
    logger.setLevel(logging.INFO)
    # This app's own logger, not the root one - never doubles up with
    # uvicorn's own access-log handler, which stays exactly as it was.
    logger.propagate = False

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(_JsonFormatter())
    stream_handler.addFilter(_TraceContextFilter())
    logger.addHandler(stream_handler)

    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        logger.addHandler(LoggingHandler(logger_provider=logger_provider))
