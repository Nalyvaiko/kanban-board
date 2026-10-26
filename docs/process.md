# Process

- Tasks are GitHub issues, one at a time
- Read the acceptance criteria before starting and before closing
- Commit regularly
- Branch off `main`; do not commit directly to `main`

## Roles

- **PM** - grooms a task before anyone implements it, follows `team/pm.md`
- **Software Engineer** - implements one groomed task, follows `team/software-engineer.md`
- **DevOps Engineer** - implements one groomed task that touches CI/CD, Docker, or
  AWS infrastructure, follows `team/devops-engineer.md`
- **SRE** - implements one groomed task that touches metrics, dashboards, alerting,
  or the on-call automation, follows `team/sre.md`
- **QA** - checks the result against the acceptance criteria, follows `team/qa-engineer.md`

Which engineer implements a task depends on what it touches, not on how it arrived -
a task that only touches `backend/` or `frontend/` goes to the Software Engineer; one
that touches `.github/workflows/`, `Dockerfile`, `docker-compose.yml`, or `cloudformation/`
goes to the DevOps Engineer; one that touches `observability/` or `on-call-engineer/`
goes to the SRE. A task can need more than one - groom it as one issue with
acceptance criteria covering both, and run the right implementer for each criterion.

## Orchestrator

The main session is the orchestrator. It launches the PM, the implementing
engineer(s), and QA as subagents. It does not groom, implement, or test itself.

## Lifecycle

1. Pick the next open issue from the backlog (`tasks.md`, kept in sync with the
   GitHub issues)
2. PM grooms it
3. The right engineer(s) implement it
4. QA verifies it
5. On FAIL, back to step 3 with the QA comment as input
6. On PASS, the orchestrator closes the issue itself - see "Closing issues" below
7. Repeat until the backlog is empty

## Closing issues

The orchestrator closes an issue explicitly (`gh issue close`, with a comment
saying what verified it) after QA outputs PASS. Do not depend on a PR's
`Closes #N`/`Fixes #N` to do this for you, even when it links correctly: issues
#22 and #23 both had a correctly-established link (confirmed via the GitHub
API - `closingIssuesReferences` showed the link, the PR showed `merged: true`)
and GitHub still did not auto-close either one. Keep `Closes #N` in PR
descriptions anyway - it's a useful cross-reference in the UI - but it is never
the thing that actually closes the issue; the explicit close in step 6 is.

## Rules

- Do not skip step 2
- The engineer does not close the issue
- QA does not fix the code, only outputs PASS or FAIL
- The orchestrator closes the issue only after QA outputs PASS, and does so
  explicitly - see "Closing issues" above
- Keep `tasks.md` and the GitHub issues in sync when tasks change
- Verify empirically before claiming something works: run the real command, hit
  the real endpoint, bring up the real stack. Static review (reading the diff) is
  not a substitute for running it, for anything that can actually be run.
