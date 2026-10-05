"""OpenTelemetry setup.

Every span this process emits carries three resource attributes that
identify *which* deployment it came from:

  - service.name           OTEL_SERVICE_NAME, defaults to "kanban-backend"
  - deployment.environment ENVIRONMENT, e.g. "dev" or "production" (see
                            .github/scripts/deploy-app.sh, which is what
                            actually sets this outside local dev)
  - service.version        APP_VERSION, the deployed image's tag (see the
                            same script) - "unknown" if unset, which is
                            the normal case in local dev/tests.

Instrumentation (FastAPI request spans, SQLAlchemy query spans) is always
wired up, so tracing code paths are exercised the same way in every
environment. Actually *exporting* those spans only happens if
OTEL_EXPORTER_OTLP_ENDPOINT is set - otherwise there's nothing listening,
and we'd rather skip the exporter than have it burn time retrying a
connection that was never going to work (local dev, CI, tests).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

from .db import engine


def setup_telemetry(app: FastAPI) -> None:
    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "kanban-backend"),
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.environ.get("ENVIRONMENT", "development"),
            ResourceAttributes.SERVICE_VERSION: os.environ.get("APP_VERSION", "unknown"),
        }
    )
    provider = TracerProvider(resource=resource)

    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
