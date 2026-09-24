# e2e

Playwright tests that drive the real `docker-compose.yaml` stack (the
actual built Docker image, real Postgres) through a real browser, the way
a user would - as opposed to `backend/tests` (in-process API tests) or
`integration-tests` (plain HTTP against the compose stack, no browser/UI).

## Running

Requires Docker, and nothing already listening on `localhost:8000`:

```sh
make test-e2e
# or directly:
cd e2e && npm install && npx playwright install --with-deps chromium && npm test
```

`global-setup.ts` runs `docker compose up -d --build` and waits for the
app to become reachable before any test runs; `global-teardown.ts` runs
`docker compose down -v` afterward, so this always starts from and ends
on a clean slate. Expect it to take a couple of minutes: building the
image and starting Postgres both take real time.

## What's covered

`tests/invite-and-collaborate.spec.ts` drives the app's real collaboration
flow across two independent browser sessions (two `BrowserContext`s, each
with its own cookies/storage - the same isolation two different browsers
would give):

1. Log in as the admin (a seeded demo account) and create a project + task.
2. Invite a teammate by email from the project's Members page. (This app
   has no shareable join *link* - invitations are email-based; see the
   comment at the top of the spec.)
3. Register as that teammate in a second session, accept the invitation
   from the dashboard's "Pending invitations" list.
4. Edit the task as the teammate.
5. Reload as the admin and confirm the edit is visible (there's no live
   push sync in this app, so a real admin would need to refresh too).
