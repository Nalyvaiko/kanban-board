# Backlog

One-to-one with the GitHub issues. Plan and decisions live in [`plan.md`](plan.md).

Per `process.md`: read a task's acceptance criteria (on the issue itself) before
starting and again before closing.

| # | Status | Task | Area |
| --- | --- | --- | --- |
| [#7](https://github.com/Nalyvaiko/kanban-board/issues/7) | ✅ Closed | Build the MVP kanban board (backend + frontend) | Software Engineer |
| [#8](https://github.com/Nalyvaiko/kanban-board/issues/8) | ✅ Closed | Persist data in a real database instead of an in-memory store | Software Engineer |
| [#9](https://github.com/Nalyvaiko/kanban-board/issues/9) | ✅ Closed | Add Postgres support and a Docker Compose stack | DevOps Engineer |
| [#10](https://github.com/Nalyvaiko/kanban-board/issues/10) | ✅ Closed | Add integration and end-to-end test coverage | Software Engineer |
| [#11](https://github.com/Nalyvaiko/kanban-board/issues/11) | ✅ Closed | Deploy to AWS via CloudFormation (cheapest-viable) | DevOps Engineer |
| [#12](https://github.com/Nalyvaiko/kanban-board/issues/12) | ✅ Closed | Build a CI/CD pipeline with automated AWS deploy | DevOps Engineer |
| [#13](https://github.com/Nalyvaiko/kanban-board/issues/13) | ✅ Closed | Split dev and production into independent environments | DevOps Engineer |
| [#14](https://github.com/Nalyvaiko/kanban-board/issues/14) | ✅ Closed | Build once, deploy everywhere via ECR | DevOps Engineer |
| [#15](https://github.com/Nalyvaiko/kanban-board/issues/15) | ✅ Closed | Instrument the backend with OpenTelemetry | SRE |
| [#16](https://github.com/Nalyvaiko/kanban-board/issues/16) | ✅ Closed | Stand up an observability stack | SRE |
| [#17](https://github.com/Nalyvaiko/kanban-board/issues/17) | ✅ Closed | Track business metrics and visualize them | SRE |
| [#18](https://github.com/Nalyvaiko/kanban-board/issues/18) | ✅ Closed | Deploy the observability stack to AWS | DevOps Engineer + SRE |
| [#19](https://github.com/Nalyvaiko/kanban-board/issues/19) | ✅ Closed | Alert on repeated task-creation failures | SRE |
| [#20](https://github.com/Nalyvaiko/kanban-board/issues/20) | ✅ Closed | Automate on-call response to firing alerts | SRE |
| [#21](https://github.com/Nalyvaiko/kanban-board/issues/21) | ✅ Closed | Find and fix the real bug behind repeated task-creation failures | Software Engineer |
| [#22](https://github.com/Nalyvaiko/kanban-board/issues/22) | ✅ Closed | Prove the alert/on-call pipeline catches a real regression | SRE |
| [#23](https://github.com/Nalyvaiko/kanban-board/issues/23) | ✅ Closed | Improve on-call README: problem statement and expected behavior | SRE |
| [#24](https://github.com/Nalyvaiko/kanban-board/issues/24) | ✅ Closed | Define the agent team and development process | - (meta/docs) |
| [#26](https://github.com/Nalyvaiko/kanban-board/issues/26) | 🟡 Open - [PR #27](https://github.com/Nalyvaiko/kanban-board/pull/27) pending | Stop relying on GitHub auto-close keywords; close issues per process.md instead | - (meta/docs) |

Issues #7-24 were filed retroactively against work already merged to `main` -
each issue's close comment cites the exact commit(s) that satisfied its
acceptance criteria. #22 and #23 are a cautionary tale, not an auto-close
success story: their PRs (#5, #6) merged with a correctly-linked `Closes #N`,
and GitHub still never auto-closed them - they sat open until the user asked
why. Closed explicitly once that was noticed. See `process.md`'s "Closing
issues" section (added by #26) for the rule this led to: the orchestrator
always closes explicitly, `Closes #N` is a cross-reference only.

New tasks go on this list and as a GitHub issue together, using
[`task-template.md`](task-template.md). Keep this table in sync with the issues -
if they ever disagree, the GitHub issue is correct and this table is stale.
