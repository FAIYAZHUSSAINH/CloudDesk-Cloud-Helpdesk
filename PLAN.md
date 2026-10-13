# CloudDesk implementation plan

## Requirements and decisions
- Flask application factory with blueprints, SQLAlchemy models, Flask-Login sessions, global CSRF, and Flask-Migrate.
- SQLite is the offline default; `DATABASE_URL` selects PostgreSQL. UTC timestamps are stored as timezone-aware values through a SQLAlchemy type and displayed in Asia/Kolkata.
- Public registration creates users only. Admin provisioning and demo seeding require explicit CLI credentials.
- Cookie-authenticated JSON writes require the same CSRF token as HTML forms.
- Optional S3 and Terraform are deferred until the core MVP is verified; they are not needed for the academic demonstration.

## Phases
1. Models, migrations, authentication, ticket and admin workflows, API, templates.
2. Security, regression tests, lint, local demo and performance measurements.
3. Docker, CI, Render/Supabase configuration and documentation.

## Acceptance criteria
- Users can register, log in, create and edit their unresolved tickets, and cannot access others' tickets.
- Admins can view all tickets, change status, see database-backed statistics and activity.
- SLA and timezone behavior, API authorization, CSRF, and persistence pass automated tests.
- Local application starts; Docker build/runtime are checked when the engine is available.

## Risks and verification
- Docker engine or cloud credentials may be unavailable. Record these checks as unverified and give exact manual steps.
- SQLite returns naive datetimes by default; a custom UTC type normalizes them on read. Test this explicitly.
- Run `ruff check .`, `pytest`, migration smoke checks, and a local HTTP smoke test.
