"""OpenTelemetry setup.

Every span and metric this process emits carries three resource
attributes that identify *which* deployment it came from:

  - service.name           OTEL_SERVICE_NAME, defaults to "kanban-backend"
  - deployment.environment ENVIRONMENT, e.g. "dev" or "production" (see
                            .github/scripts/deploy-app.sh, which is what
                            actually sets this outside local dev)
  - service.version        APP_VERSION, the deployed image's tag (see the
                            same script) - "unknown" if unset, which is
                            the normal case in local dev/tests.

Instrumentation (FastAPI request spans, SQLAlchemy query spans, and the
app metrics below) is always wired up, so those code paths are exercised
the same way in every environment. Actually *exporting* only happens if
OTEL_EXPORTER_OTLP_ENDPOINT is set - otherwise there's nothing listening,
and we'd rather skip the exporters than have them burn time retrying a
connection that was never going to work (local dev, CI, tests).

The four app metrics (`boards_created`, `active_sessions`,
`tasks_created`, `task_creation_failures`) are created here, at module
level, and imported by the routers that actually record them
(boards.py, auth.py, tasks.py) - see each one's own comment for why that
particular metric lives on that particular instrument.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

from .db import engine

_meter = metrics.get_meter("kanban_backend")

# "Board" is this app's closest equivalent to a shared collaborative
# space - counts one per board actually created (see boards.py).
boards_created = _meter.create_counter(
    "boards_created", description="Boards created", unit="{board}"
)

# Tracks currently-outstanding bearer tokens (one per logged-in
# session) as a running total, not a counter - it goes up on
# login/register and back down on logout, so it reads as "how many
# sessions are active right now" (see auth.py).
active_sessions = _meter.create_up_down_counter(
    "active_sessions", description="Currently active (logged-in) sessions", unit="{session}"
)

# "Task" is this app's closest equivalent to a unit of content users
# create within a board (see tasks.py).
tasks_created = _meter.create_counter(
    "tasks_created", description="Tasks created", unit="{task}"
)
task_creation_failures = _meter.create_counter(
    "task_creation_failures", description="Failed attempts to create a task", unit="{failure}"
)


def setup_telemetry(app: FastAPI) -> None:
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "kanban-backend"),
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.environ.get("ENVIRONMENT", "development"),
            ResourceAttributes.SERVICE_VERSION: os.environ.get("APP_VERSION", "unknown"),
        }
    )

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")

    tracer_provider = TracerProvider(resource=resource)
    if endpoint:
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    meter_provider_kwargs = {"resource": resource}
    if endpoint:
        meter_provider_kwargs["metric_readers"] = [
            PeriodicExportingMetricReader(OTLPMetricExporter())
        ]
    metrics.set_meter_provider(MeterProvider(**meter_provider_kwargs))

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
