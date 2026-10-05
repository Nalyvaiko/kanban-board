# Observability stack

An OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana - a
separate Compose project from the app (`../docker-compose.yml`), so
either can be started, stopped, or redeployed independently. Nothing
here is specific to this app; it's a generic place to send OTLP
telemetry and look at it.

## Running it

```sh
docker compose up -d
```

| Service | Port | What's there |
| --- | --- | --- |
| Grafana | `http://localhost:3000` | The UI - login `admin` / `admin` (forces a password change on first login) |
| Prometheus | `http://localhost:9090` | Metrics, and its own UI if you want to query directly |
| Loki | `http://localhost:3100` | Logs - no real UI of its own, query it through Grafana |
| Tempo | `http://localhost:3200` | Traces - same, query through Grafana |
| OTel Collector | `http://localhost:4317` (gRPC) / `:4318` (HTTP) | Where OTLP senders point `OTEL_EXPORTER_OTLP_ENDPOINT` |

Grafana already has Prometheus, Loki, and Tempo provisioned as
datasources on first boot (`grafana/provisioning/datasources/`) - open
Grafana → Explore and pick one, no setup needed.

## Connecting the app

The collector's OTLP ports are published to the host (not just this
project's own internal network), so the app - a fully separate Compose
project, with no shared network or other coupling to this one - can
reach it over `host.docker.internal` without either stack needing to
know the other is running. To actually send telemetry, set this when
starting the app stack (`../docker-compose.yml`):

```sh
OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 ENVIRONMENT=dev docker compose up -d
```

Leave `OTEL_EXPORTER_OTLP_ENDPOINT` unset and the app runs exactly as
before - see `backend/src/kanban_backend/telemetry.py`'s own comment.
This stack can be started, stopped, or not running at all without
affecting whether the app stack itself comes up.

A real deploy (`deploy-app.sh`) doesn't set this at all right now - this
stack is local/dev-oriented only; nothing here is deployed to AWS.
Pointing a real deployment at a collector would mean either running
this stack on the same instance (same pattern as above) or at a
separate, always-on endpoint - not set up here.

## What's actually flowing right now

Only **traces**. The app's current instrumentation (FastAPI + SQLAlchemy
auto-instrumentation, see the backend README's "Telemetry" section)
only creates spans - it doesn't emit metrics or logs through OTel. The
Prometheus and Loki pipelines below are real and wired up correctly
(verified: `docker compose pull`'s prometheus exporter scrape succeeds,
Loki's OTLP endpoint accepts pushes), they just have nothing to carry
yet. Adding metrics (e.g. request counts/latencies) or routing the
app's logs through OTel instead of plain stdout would start filling
those in without any change on this side.

## How telemetry actually gets from the app to here

```
app ──OTLP──▶ otel-collector ──OTLP──▶ tempo        (traces)
                            ──scraped by──▶ prometheus  (metrics, pull-based)
                            ──OTLP──▶ loki           (logs)
                                                          ▲
                                              grafana ────┘ (queries all three)
```

The collector is the only thing the app talks to directly
(`otel-collector-config.yaml` defines where each signal goes from
there) - swapping Tempo/Loki/Prometheus for something else later is a
collector-config change, not an app change.

## Notes

- **Tempo is pinned to `2.6.1`**, not `latest` like the others - Tempo
  3.x restructured its config around a different deployment model
  (scheduler/worker-based) that `tempo.yaml`'s simple single-binary
  config doesn't match. Re-check this if you ever bump it.
- **Nothing here persists usefully long-term** - all storage is local
  Docker volumes with no backup, same tradeoff as the app's own
  database (see `../cloudformation/README.md`). Fine for local
  dev/demo; not a real observability backend.
- **No auth in front of Prometheus/Loki/Tempo's own ports** - acceptable
  for a stack that only runs on localhost; don't publish these ports on
  a real server without putting something in front of them.
