# CloudDesk cloud computing case study

## Problem and requirements

University IT teams often receive issues in chat threads or spreadsheets, where ownership and resolution history are hard to see. CloudDesk gives students an authenticated ticket form and gives IT admins a shared queue. Functional requirements include registration, private ticket tracking, status management, dashboard statistics, and SLA indicators. Non-functional requirements include access control, persistence, usable mobile layouts, portable deployment, and repeatable tests.

## Service models and architecture

IaaS supplies virtual machines and networks, which would require managing the operating system. PaaS runs an application from a source/image with less server administration; Render fills this role. SaaS is ready-to-use software delivered to users; CloudDesk would be SaaS to its end users once hosted. Supabase supplies managed PostgreSQL. The proposed cloud path is browser over HTTPS to Render's Docker/Gunicorn web service, then a TLS PostgreSQL connection to Supabase's IPv4-compatible session pooler. Render and Supabase reduce server and database administration for a small project. This path remains **unverified** until deployed. See the README architecture and ER diagrams.

## Implementation, database, and networking

Flask blueprints separate authentication, ticket views, administration, and JSON API. SQLAlchemy maps users, tickets, status activities, and login failures. Alembic migrations version schema changes for both SQLite and PostgreSQL. Ticket IDs are database primary keys. Foreign keys link tickets to creators and activities to tickets and actors. Both migrations, a foreign-key rejection, and ticket/status persistence were verified against a temporary local PostgreSQL 16 container; the real Supabase service remains untested. Locally, SQLite supports offline demos; the proposed cloud PostgreSQL database would survive web instance replacement. Render HTTPS and a TLS database URI still need live verification.

## Security

Werkzeug hashes passwords; Flask-Login manages sessions; admin accounts are provisioned by CLI. Every owner-scoped read and write checks identity on the server. Flask-WTF checks CSRF on cookie-authenticated forms and API mutations. Input choices and lengths are validated server side. Cookies are HttpOnly and SameSite=Lax; Render forces Secure cookies and trusted hosts. Failed logins are limited to five per normalized email per 15 minutes using HMAC email digests in the database. This basic limit does not stop distributed registration abuse or simultaneous attempts perfectly. Secrets come from environment variables. Operational backups and broader abuse protection remain future work.

## Docker, CI/CD, and monitoring

Docker packages Python, dependencies, and Gunicorn; a container runs that image. Compose uses a named SQLite volume for local persistence. GitHub Actions is configured to run Ruff, a dependency advisory audit, pytest, and Docker build on pull requests and main pushes. A successful main build can call the Render deploy hook; a missing hook skips deploy. There has been no GitHub Actions run. A liveness endpoint and stdout logs help find startup and request errors. They do not replace metrics, tracing, or alerts.

## Testing and performance

Pytest covers authentication, login rate limiting, access denial, validation, ticket lifecycle, SLA/timezone logic, API CSRF, production configuration, and migration/seed behavior. `scripts/benchmark.py` samples 20 local test-client calls for health, creation, retrieval, and stats; measured values belong in `docs/evaluation.md`. Local Docker evidence is separate from that benchmark. The cloud deployment is unverified until a real HTTPS URL, PostgreSQL persistence, and redeploy survival are observed.

## Scalability, cost, limitations, conclusion

Vertical scaling means increasing memory/CPU for the web service. Horizontal scaling would need multiple web replicas behind a load balancer and a shared PostgreSQL database, with connection limits sized for every worker; it is not implemented. SQLite supports local single-instance use. A managed database would decouple data from ephemeral web instances, though it would still require a backup plan. Current limits include no attachments, notifications, password reset, background jobs, business-hours SLA, pagination, or database readiness endpoint. [Cost assumptions and measured results](evaluation.md) separate local tests from cloud results. CloudDesk is locally demonstrable; external deployment and its persistence still need real verification.
