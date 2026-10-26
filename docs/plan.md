# Plan

Source of truth for product scope and decisions: [`../PROJECT-SPEC.md`](../PROJECT-SPEC.md)
(MVP goals, data model, auth, the full feature list) and [`../openapi.yaml`](../openapi.yaml)
(the exact API contract the backend implements against).

Read `PROJECT-SPEC.md` before planning product work. Do not expand scope past it
without filing that expansion as its own groomed task (see `task-template.md`'s
"Out of scope" section) - this mirrors the MVP's own explicit "Explicitly Out of
Scope" list, which exists precisely so scope creep has to be a deliberate decision,
not a drift.

## What `PROJECT-SPEC.md` does not cover

`PROJECT-SPEC.md` is the *product* spec, written before any of the infrastructure
below existed. None of it is optional or deferred - all of it is built, tested, and
(for the AWS/observability pieces) actually deployed - it just isn't product scope,
so it lives in its own docs instead of being folded into the spec:

| Area | Where the decisions and tradeoffs actually live |
| --- | --- |
| Local dev, Docker, Postgres | [`../README.md`](../README.md), [`../backend/README.md`](../backend/README.md) |
| CI/CD (tests, build, deploy) | [`../.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) |
| AWS deployment (dev + prod) | [`../cloudformation/README.md`](../cloudformation/README.md) |
| Observability (metrics/traces/logs, dashboard, alerting) | [`../observability/README.md`](../observability/README.md) |
| Automated on-call response | [`../on-call-engineer/README.md`](../on-call-engineer/README.md) |

Treat each of those as the plan for its own area, the same way `PROJECT-SPEC.md`
is the plan for product scope: read it before planning work in that area, and
don't expand past its stated tradeoffs without a deliberate, documented decision.
