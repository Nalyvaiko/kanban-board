# On-call engineer

`poll.py` watches the observability stack's alert API and, when a
Grafana alert fires (see `../observability/grafana/provisioning/
alerting/`), hands its full details to a headless coding agent -
Claude Code itself, in its non-interactive `claude -p` mode - to
investigate and, if it can, fix.

This is not deployed anywhere and is not part of either Compose stack.
It needs a real coding agent's own credentials and a real checkout of
this repo to do anything useful, so it runs wherever an operator (or a
dedicated, always-on ops host) puts it - a laptop, a small VM, a
container you build yourself - not baked into this repo's images.

## Running it

```sh
python3 on-call-engineer/poll.py
```

No dependencies to install - stdlib only. Runs forever, polling once a
minute by default (`Ctrl-C` to stop). Needs the `claude` CLI installed
and already logged in (or `ANTHROPIC_API_KEY` set) in whatever
environment runs this script, and network access to wherever Grafana
actually is (`http://localhost:3000` by default, for the local
`observability/docker-compose.yml` stack).

| Env var | Default | What it's for |
| --- | --- | --- |
| `GRAFANA_URL` | `http://localhost:3000` | Where to poll - the AWS deploy's `GrafanaUrl` output if watching that instance instead |
| `GRAFANA_USER` / `GRAFANA_PASSWORD` | `admin` / `admin` | Basic auth - match whatever `GrafanaAdminPassword` was actually set to for a real deploy |
| `POLL_INTERVAL_SECONDS` | `60` | How often to check for new firing alerts |
| `REPO_DIR` | this repo's own root | Working directory handed to the agent - where it actually looks for the code to investigate |
| `AGENT_COMMAND` | `claude -p` | The headless agent to dispatch to - the alert's full prompt is appended as its last argument |
| `STATE_FILE` / `LOG_FILE` | `on-call-engineer/state.json` / `dispatch.log` | Where this script tracks what it has already dispatched, and its own log |

## What actually happens

Every `POLL_INTERVAL_SECONDS`, it asks Grafana's Alertmanager-
compatible API (`/api/alertmanager/grafana/api/v2/alerts`) which alerts
are currently firing. For each one that is a *new* incident - its
(fingerprint, start time) pair hasn't been dispatched before, which
also covers the same rule firing again later after resolving in
between - it builds a prompt out of the alert's own labels and
annotations (service, environment, deployed version, owner, summary,
description, dashboard link - the same fields `rules.yaml` puts on
every alert, see `../observability/README.md`'s "Alerting" section)
and runs:

```sh
claude -p "<that prompt>"
```

in `REPO_DIR`, in the background - this script moves on to its next
poll tick immediately rather than waiting for the agent to finish,
since triage can take far longer than a minute. The agent's own output
goes to `on-call-engineer/agent-<fingerprint>-<timestamp>.log`.

An incident is dispatched once, not once per minute it stays firing -
`state.json` is what remembers that.

## Before pointing this at a real alert

**The agent can change and commit code with no human in the loop
between the alert firing and that happening.** That is the point - an
on-call engineer who can actually fix things while you're asleep - but
it is also the real risk here, and this script does nothing to limit
it: the default prompt explicitly invites a fix, `REPO_DIR` defaults to
a real checkout of this repo, and nothing here reviews, sandboxes, or
gates what the agent does before it does it.

Before running this against anything that matters, decide how much
autonomy you actually want and build that in - some options, from most
to least autonomous:

- As designed: the agent works directly in `REPO_DIR` and can commit/
  push on its own. Fastest, highest risk.
- Point `REPO_DIR` at a disposable git worktree instead of your main
  checkout, and require a human to review and merge whatever branch
  the agent pushes - keeps the investigation autonomous, gates the
  actual change.
- Change the prompt in `poll.py`'s `build_prompt` to ask for
  investigation and a written report only ("do not make any code
  changes"), and have a human act on that report.

Nothing in this directory assumes which of these you want - that's a
real decision about how much you trust an unattended agent with this
specific codebase, not something to default silently.
