#!/usr/bin/env python3
"""Polls the observability stack's alert API and, when an alert fires,
hands its details to a headless coding agent for triage.

Run this somewhere that has the agent's own CLI installed and
authenticated, and this repo checked out - see README.md. It is
deliberately not part of the app or observability Docker Compose
stacks, and nothing deploys it: it needs a real coding agent's own
credentials and a real checkout to investigate/fix anything, neither
of which belongs baked into this repo's own images.

Stdlib only, no dependencies to install - this is meant to just run
with `python3 on-call-engineer/poll.py`.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000").rstrip("/")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))
REPO_DIR = Path(os.environ.get("REPO_DIR", Path(__file__).resolve().parent.parent))
STATE_FILE = Path(os.environ.get("STATE_FILE", Path(__file__).resolve().parent / "state.json"))
LOG_FILE = Path(os.environ.get("LOG_FILE", Path(__file__).resolve().parent / "dispatch.log"))

# The headless coding agent to hand firing alerts to. `claude -p` is
# Claude Code's own non-interactive mode: give it a prompt as an
# argument, it runs to completion - investigating, and fixing if it
# can - with no human in the loop, then exits. Override to point at a
# different agent/CLI; whatever it is, it must accept the full prompt
# as its last argument and run to completion on its own.
AGENT_COMMAND = os.environ.get("AGENT_COMMAND", "claude -p").split()

ALERTS_URL = f"{GRAFANA_URL}/api/alertmanager/grafana/api/v2/alerts"


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message}"
    print(line, flush=True)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def load_state() -> dict[str, str]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_firing_alerts() -> list[dict]:
    """Returns only alerts Alertmanager currently considers active
    (firing) - not resolved, and not suppressed by a silence/inhibit."""
    request = urllib.request.Request(ALERTS_URL)
    credentials = f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()
    request.add_header("Authorization", "Basic " + base64.b64encode(credentials).decode())
    with urllib.request.urlopen(request, timeout=10) as response:
        alerts = json.loads(response.read())
    return [a for a in alerts if a.get("status", {}).get("state") == "active"]


def build_prompt(alert: dict) -> str:
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    dashboard_path = annotations.get("dashboard_url", "")
    dashboard_url = f"{GRAFANA_URL}{dashboard_path}" if dashboard_path.startswith("/") else dashboard_path
    return f"""An alert fired in the kanban-board observability stack. Investigate
the likely root cause in this repository and, if you can confidently
identify and fix it, make the fix; otherwise report what you found and
why you did not change anything.

Alert: {labels.get("alertname", "(unknown)")}
Summary: {annotations.get("summary", "(none)")}
Description: {annotations.get("description", "(none)")}
Severity: {labels.get("severity", "(none)")}
Service: {labels.get("service_name", "(none)")}
Environment: {labels.get("deployment_environment", "(none)")}
Deployed version: {labels.get("service_version", "(none)")}
Owner: {labels.get("owner", "(none)")}
Dashboard: {dashboard_url or "(none)"}
Fired at: {alert.get("startsAt", "(unknown)")}
Alert fingerprint: {alert.get("fingerprint", "(unknown)")}
""".strip()


def dispatch(alert: dict) -> None:
    fingerprint = alert.get("fingerprint", "unknown")
    alertname = alert.get("labels", {}).get("alertname", "unknown")
    prompt = build_prompt(alert)
    log(f"dispatching alert '{alertname}' (fingerprint {fingerprint}) to: {' '.join(AGENT_COMMAND)}")

    agent_log_path = LOG_FILE.parent / f"agent-{fingerprint}-{int(time.time())}.log"
    with agent_log_path.open("w") as agent_log:
        # Not awaited - a triage/fix attempt can run far longer than
        # this loop's poll interval, and dispatching is this script's
        # whole job, not babysitting the agent to completion.
        subprocess.Popen([*AGENT_COMMAND, prompt], cwd=REPO_DIR, stdout=agent_log, stderr=subprocess.STDOUT)
    log(f"agent output will be written to {agent_log_path}")


def poll_once(state: dict[str, str]) -> None:
    firing = fetch_firing_alerts()
    firing_fingerprints = set()

    for alert in firing:
        fingerprint = alert.get("fingerprint")
        starts_at = alert.get("startsAt")
        firing_fingerprints.add(fingerprint)

        # Dispatch once per incident, not once per poll tick - an
        # incident is the same (fingerprint, startsAt) pair for as
        # long as it keeps firing without resolving in between.
        if state.get(fingerprint) == starts_at:
            continue
        try:
            dispatch(alert)
        except Exception as error:
            log(f"error dispatching alert (fingerprint {fingerprint}): {error}")
            continue
        state[fingerprint] = starts_at
        save_state(state)

    # Forget incidents that are no longer firing, so if the same rule
    # fires again later it is treated as a new incident, not a
    # duplicate of one already dispatched.
    resolved = [fp for fp in state if fp not in firing_fingerprints]
    if resolved:
        for fp in resolved:
            del state[fp]
        save_state(state)


def main() -> None:
    log(f"on-call-engineer starting - polling {ALERTS_URL} every {POLL_INTERVAL_SECONDS}s")
    state = load_state()
    while True:
        try:
            poll_once(state)
        except urllib.error.URLError as error:
            log(f"could not reach Grafana: {error}")
        except Exception as error:
            log(f"unexpected error polling alerts: {error}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
