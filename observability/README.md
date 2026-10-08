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

A real deploy (`deploy-app.sh`) sets this the same way, just pointed at
a real, always-on collector instead of localhost - see "Deploying to
AWS" below for how dev and production both get wired up to it.

## What's actually flowing right now

**Traces and metrics.** The app's instrumentation (FastAPI + SQLAlchemy
auto-instrumentation, plus four app-specific metrics - see the backend
README's "Telemetry" section) emits both. **Not logs** - the app still
just writes to stdout, not through OTel, so the Loki pipeline is real
and wired up correctly (verified: it accepts OTLP pushes), but has
nothing to carry yet. Routing the app's logs through OTel instead of
plain stdout would start filling that in without any change on this
side.

## The dashboard

Grafana comes with a "Kanban App Metrics" dashboard already provisioned
(`grafana/provisioning/dashboards/kanban-app-metrics.json`) - open it
straight from Grafana's home page, no setup needed. It shows the four
metrics above (current totals as stat panels, trends as time series),
with **Environment** and **Deployed version** dropdowns at the top that
filter every panel by `deployment_environment`/`service_version` - both
populated from whatever values have actually been seen, via
`label_values(...)` queries against the metrics themselves.

This relies on `otel-collector-config.yaml`'s `prometheus` exporter
having `resource_to_telemetry_conversion` enabled, which copies every
OTel resource attribute (including both of those) onto every metric as
a label - without it, they'd only exist on the separate `target_info`
metric, and the dashboard's filters wouldn't have anything to filter
*on* the metrics directly. Verified end to end: ran the app twice under
two different `APP_VERSION`s, confirmed both show up as separate
`service_version` label values in Prometheus, and confirmed the
dashboard's filtered queries correctly isolate one version's data from
the other (and union them back together when filtering by both/"All").

## Alerting

One Grafana-managed alert rule is provisioned (`grafana/provisioning/
alerting/`): **Repeated task creation failures**, which fires when
`task_creation_failures_total` shows more than 5 failures within a
trailing 5-minute window, sustained for 2 minutes. Both numbers are
chosen, not arbitrary - see rules.yaml's own comment, which also
documents a real bug this caught: an earlier version used a 5-minute
sustain duration (equal to the measurement window), and actually
testing it - firing a real burst of failures and watching the rule's
state - showed it going Pending and then resetting back to Normal
before the 5 minutes was up, because the burst scrolled back out of
its own 5-minute measurement window at essentially the same rate the
sustain timer was counting down. A single occasional failure (one
blank-title submission, one permission error) is routine and does not
fire this; a sustained burst does.

Each firing alert carries, as real labels/annotations rather than
boilerplate text - verified by actually triggering it and reading the
live alert back from Grafana's API:

| What | Where it comes from |
| --- | --- |
| Service | `service_name` label - from the query's own `by (service_name, ...)` grouping, i.e. the real OTel resource attribute, not a hardcoded string |
| Environment | `deployment_environment` label, same way |
| Deployed version | `service_version` label, same way |
| Owner | `owner` label/annotation - static (`backend`); there's no telemetry attribute this could come from, since this project has no real on-call rotation |
| Dashboard URL | `dashboard_url` annotation (a path Grafana's own UI resolves against itself) plus `__dashboardUid__`/`__panelId__`, which link it to "Kanban App Metrics"' Task Creation Failures panel and make that link absolute in a contact point's own notification (via `GF_SERVER_ROOT_URL`) |

It's routed (`policies.yaml`) to a provisioned webhook contact point
(`contactpoints.yaml`) named `kanban-board-oncall` - currently pointed
at a placeholder URL, since a real Slack/PagerDuty/Opsgenie integration
needs credentials this project doesn't have. The rule firing and
routing to that contact point is real and verified (Grafana's own logs
show it dispatching); only the very last hop - an actual webhook
somewhere actually receiving it - needs a real URL dropped in to
`contactpoints.yaml` (or edited directly in Grafana's Alerting UI).

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

## Deploying to AWS

One instance, shared by both environments - not duplicated per
environment the way the app stack is (`cloudformation/template.yaml`,
deployed once as `kanban-board` for dev and again as `kanban-board-prod`
for production). There's only ever one Grafana to look at either
environment's data in, filtered by the dashboard's Environment dropdown
- see "The dashboard" above.

1. **Deploy it** (once, ever - same account as the app stacks, any VPC/
   subnet, doesn't need to be the same one they use):

   ```sh
   aws cloudformation deploy \
     --template-file cloudformation/observability.yaml \
     --stack-name kanban-board-observability \
     --parameter-overrides \
         VpcId=<your-vpc-id> \
         SubnetId=<your-subnet-id> \
         GrafanaAdminPassword=<pick-a-real-password> \
     --capabilities CAPABILITY_NAMED_IAM
   ```

   Then, after a few minutes:

   ```sh
   aws cloudformation describe-stacks --stack-name kanban-board-observability \
     --query 'Stacks[0].Outputs' --output table
   ```

   `GrafanaUrl` is the dashboard (login `admin` / whatever password you
   set); `CollectorOtlpEndpoint` is what the next step needs.

2. **Point dev and production at it**: add `OTEL_COLLECTOR_ENDPOINT` as
   a variable - set to the `CollectorOtlpEndpoint` value from step 1 -
   in **both** GitHub Environments (repo → Settings → Environments →
   `dev`, then again under `production`; see `cloudformation/README.md`'s
   "Two environments" section for how those were set up in the first
   place). The next deploy to either one picks it up automatically -
   `deploy-app.sh` writes it into the running app container's
   environment, and `backend/src/kanban_backend/telemetry.py` starts
   exporting to it. No app code change, no redeploy of this stack
   itself needed.

   Leaving `OTEL_COLLECTOR_ENDPOINT` unset in an environment is fine -
   that environment's app just doesn't send telemetry, same as any
   local run with `OTEL_EXPORTER_OTLP_ENDPOINT` unset.

3. **Updating this stack later** (a `docker-compose.yaml`/collector-
   config change, say) - there's no CI job for this one, since it's
   infrequent and config-only:

   ```sh
   aws ssm start-session --target <InstanceId-from-the-outputs-table>
   cd /opt/observability-src && git pull
   cd observability && docker compose up -d
   ```

   Or delete the stack and deploy again for a fresh instance - same
   tradeoff as the app stack's own "Updating after a code change"
   section.

**What's different from local here**: only Grafana (3000) and the
collector's OTLP ports (4317/4318) are open to the internet -
Prometheus/Loki/Tempo's own ports are not, unlike local `docker compose
up`'s defaults (see the Notes below on why, and `cloudformation/
observability.yaml`'s security group for the exact reasoning). Grafana
also gets a real admin password instead of the default `admin`/`admin`,
since this instance - unlike a laptop - is reachable by anyone who
finds its IP.

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
  for a stack that only runs on localhost; the AWS deploy above acts on
  this by simply not opening those three ports in its security group,
  rather than putting anything in front of them.
