# Verification, performance, and cost

Evidence recorded on 13 October 2026 (Asia/Kolkata). The public [GitHub repository](https://github.com/FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk) and [successful CI run](https://github.com/FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk/actions/runs/38352615426) are verified. Render/Supabase deployment is **not verified**: this workspace has no Supabase credentials, Render service, public URL, or cloud database persistence test.

| Component | Implemented | Verified | Evidence |
|---|---|---|---|
| Authentication | Yes | Local | Registration/login/logout, role and login-limit tests; real local login screenshot |
| Tickets | Yes | Local | Create/read/update, ownership, and API tests; Docker retains 4 seeded tickets |
| Admin dashboard | Yes | Local | Admin status/activity/statistics tests |
| SLA | Yes | Local | UTC/IST and met/breached tests |
| SQLite | Yes | Local | Alembic migrations; Docker named volume retained 4 tickets after recreation |
| PostgreSQL | Yes | Local PostgreSQL 16 only | Both migrations, tables, foreign key, ticket/status activity, and reconnect persistence; Supabase connection needed |
| Docker | Yes | Local | Image build; migration to `bb7aa36d7612`; container health 200; 4 tickets/4 users after recreate |
| GitHub repository | Yes | Public remote verified | [FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk](https://github.com/FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk), local `main` tracks `origin/main` |
| GitHub Actions | Yes | Real run passed | [Run 38352615426](https://github.com/FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk/actions/runs/38352615426): Ruff, audit, 11 tests, Docker build; Render trigger skipped |
| Render | Blueprint configured | No service | `render.yaml`; deployment URL needed |
| Public HTTPS | Planned | No | Public browser/health test needed |
| Security | Controls implemented | Local tests and audit only | 11 pytest tests, Ruff, pip-audit clean; not a certification |
| Monitoring | Basic liveness/logging | Local | `/api/health` returned 200, container logs available; no cloud alerts |

## Security audit

Git had no commits at audit start, so no earlier repository history could have exposed a secret. `.env`, `.env.*` except `.env.example`, local databases, virtual environments, Terraform state, credentials, and logs are ignored; Docker excludes the same local material. A `detect-secrets` scan of candidate commit files produced only placeholder/test values and the words `SECRET_KEY` in documentation and source. No actual credential was found in those files. The initial `pip-audit` reported four advisories across Flask 3.1.1 and python-dotenv 1.1.1; pins were updated to Flask 3.1.3 and python-dotenv 1.2.2, and the repeated audit reported **no known vulnerabilities** for `requirements.txt` on this date. This is a point-in-time dependency check.

The application has hashed passwords, CLI-only admin creation, owner/admin checks, CSRF on mutations, generic login errors, a five-failure/15-minute account login limit in the shared database, secure production cookies, trusted Render hosts, a PostgreSQL-only Render startup check, and generic server errors. The account limiter is not an IP/global quota, and concurrent attempts may briefly exceed the threshold. Liveness does not check the database. Backups, alerts, password reset, and broader abuse protection are outstanding operational work.

A temporary local PostgreSQL 16 container accepted both Alembic migrations. The verification created a user/admin, inserted and resolved a ticket, found its activity row after a new application connection, and confirmed `tickets.user_id` rejects an invalid foreign key. The temporary container was removed. This checks PostgreSQL compatibility locally; it does **not** prove Supabase connectivity, Render networking, or cloud persistence.

## Local test-client latency

Run `python scripts/benchmark.py`. It creates a temporary SQLite database with Alembic, signs in through the login route, and measures 20 calls for each operation. Results include Flask request handling but exclude browser rendering, network, Gunicorn, Docker, Render cold starts, and Supabase latency. This host used Windows, Python 3.12, Flask 3.1.3, temporary SQLite, and 0 HTTP errors.

| Route | Requests | Mean | Median | p95 |
|---|---:|---:|---:|---:|
| `GET /api/health` | 20 | 0.27 ms | 0.26 ms | 0.29 ms |
| `POST /api/tickets` | 20 | 4.18 ms | 3.98 ms | 4.83 ms |
| `GET /api/tickets/<id>` | 20 | 1.04 ms | 1.00 ms | 1.21 ms |
| `GET /api/dashboard/stats` | 20 | 1.21 ms | 1.11 ms | 1.47 ms |

## Docker localhost HTTP latency

Run `python scripts/benchmark_http.py` only against the local seeded Docker app. It signs in over HTTP with the demo account, sends 10 requests per route through Gunicorn to the SQLite named volume, and creates 10 clearly named benchmark tickets. The run below had 0 HTTP errors. Results include localhost networking and Docker/Gunicorn; they exclude browser rendering, public internet, Render cold starts, and Supabase. The first browser screenshots were captured before these benchmark tickets were added.

| Route | Requests | Mean | Median | p95 |
|---|---:|---:|---:|---:|
| `GET /api/health` | 10 | 11.47 ms | 15.36 ms | 19.81 ms |
| `POST /api/tickets` | 10 | 8.71 ms | 5.60 ms | 35.64 ms |
| `GET /api/tickets/<id>` | 10 | 5.73 ms | 2.38 ms | 16.69 ms |
| `GET /api/dashboard/stats` | 10 | 10.08 ms | 3.51 ms | 32.86 ms |

These are small samples on this host and do not establish capacity. Public Render HTTPS: **not measured**. Never present either local table as hosted performance.

## Cost assumptions (provider documentation checked 13 October 2026)

| Service | Assumed plan | Relevant free limits and demo effect |
|---|---|---|
| GitHub repository | GitHub Free | Host source and Actions workflow; no paid plan assumed. [Plans](https://github.com/pricing) |
| GitHub Actions | GitHub Free, standard hosted runner | Public repositories have free standard runner usage; private repositories on GitHub Free have a 2,000 minute monthly allowance and 500 MB artifact storage. Check usage before large builds. [Billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [limits](https://docs.github.com/en/actions/reference/limits) |
| Render web service | Free instance if available | 750 free instance hours/month per workspace; spins down after 15 idle minutes and may take roughly a minute to wake. Filesystem is ephemeral; database must be external. Free tier has no pre-deploy command. [Free limits](https://render.com/docs/free), [deploy commands](https://render.com/docs/deploys) |
| Supabase database | Free project | 500 MB database quota, two active projects, 7-day inactivity pause; exceeding database quota can place it in read-only mode. Keep the demo project active and leave capacity. [Pricing](https://supabase.com/pricing), [database size](https://supabase.com/docs/guides/platform/database-size), [pause policy](https://supabase.com/docs/guides/platform/free-project-pausing) |

Assumed recurring platform fee is $0 only while usage stays within each provider's free allowance and a free plan remains available. This is no production cost guarantee. Data transfer, build time, usage caps, and billing terms must be checked in the connected account before deployment.

## Scalability

One free web instance and one managed database keep the design small. Vertical scaling would increase CPU/RAM and potentially worker count. Horizontal scaling would add web replicas behind a load balancer, all using the shared PostgreSQL database; it has not been implemented. The PostgreSQL engine has `pool_pre_ping`, a two-connection pool per process, no overflow, and 30-minute connection recycling. At one configured Render worker, this caps steady pool connections at two; worker/replica count must be included when sizing the database connection limit. SQLite remains suitable only for the local single-instance demo.
