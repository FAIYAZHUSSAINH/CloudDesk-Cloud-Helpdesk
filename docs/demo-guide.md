# 5–7 minute CloudDesk demonstration

## Prepare

Use the Docker fallback from the README: `docker compose build`, `docker compose run --rm web flask --app run:app db upgrade`, `docker compose up -d`, then open `http://127.0.0.1:8000`. The named volume already has local demo accounts on this machine; on another machine run `seed-demo` with two private local passwords first. Keep the [architecture diagram](../README.md), terminal, browser, workflow, [evaluation](evaluation.md), and [evidence register](evidence/README.md) ready. Only use a public Render URL if its live checks have actually passed.

## Timed walkthrough

1. **0:00–0:40 — problem and architecture.** Explain why chat and spreadsheets lose ownership/status history. Show browser → Render PaaS → Supabase managed PostgreSQL, with GitHub Actions validating and triggering deploy. Identify this as the proposed cloud path until verified.
2. **0:40–1:20 — user access.** Open the local app, log in as `aarav@example.test` using the private local demo password, and show the user's own ticket counts. Point out cookie sessions and role checks.
3. **1:20–2:20 — create a ticket.** Make a new Network/High ticket with a real location and symptom. Show its unique ID, Open status, IST timestamp, and illustrative 2-hour SLA.
4. **2:20–3:00 — private queue.** Filter My Tickets by priority/status and explain that server-side owner checks protect detail and API routes. Log out.
5. **3:00–4:20 — admin flow.** Log in as `admin@example.test` with its separate local password. Show live dashboard cards/charts. Open the new ticket, set In Progress then Resolved, and show the status activity, resolution timestamp, SLA label, and updated counts. Reopen if asked.
6. **4:20–5:10 — persistence.** Show `docker compose ps` and the named SQLite volume. Restart the container if time permits and reload the ticket. For a verified cloud demo, show the same ID/status in Supabase and after a Render redeploy. State clearly which database is being shown.
7. **5:10–6:10 — operations and security.** Show the Dockerfile (non-root Gunicorn on `PORT`), the GitHub workflow (Ruff, dependency audit, pytest, Docker build, main-only hook), migration files, CSRF, secure production cookies, trusted host setting, and the five-failure login limit. Show a real CI run/Render log only if available.
8. **6:10–7:00 — evaluation.** Quote the separate local test-client and Docker HTTP timings in `evaluation.md`. Explain Render sleep, Supabase pause/storage limits, vertical scaling, and how a future load balancer plus shared PostgreSQL would allow horizontal scaling. Do not present local timings as cloud results.

## What to show

- User can see only their own tickets; admin sees the shared queue.
- A new ticket has unique ID, Open status, chosen category/priority, and IST time.
- Admin transitions record activity and a resolution time; dashboard counts change.
- A local container restart preserves SQLite records. Public persistence requires real Supabase and redeploy checks.
- [Local screenshots](evidence/README.md) already show login, user dashboard, ticket #5 creation, admin dashboard, and ticket #5 resolved with SLA Met. They are genuine Docker browser captures, not cloud captures.

## Backup path and troubleshooting

```powershell
docker compose run --rm web flask --app run:app db upgrade
docker compose up -d
docker compose ps
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

If Render is asleep or Supabase is paused, use the local Docker demo and say the live cloud path is unavailable or unverified. If Docker fails, use the local Python/SQLite instructions in the README. If login fails, use the passwords entered for local seed data; reseeding does not reset an existing password. If a ticket is absent, check the signed-in user and database. Keep passwords, cookies, database URLs, and deploy-hook URLs out of screenshots.
