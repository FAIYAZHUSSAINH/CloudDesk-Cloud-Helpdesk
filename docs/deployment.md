# GitHub → Actions → Render → Supabase deployment

**Status, 13 October 2026:** local deployment is verified; external deployment is not. A reviewed initial commit is on local `main`, but this workspace has no Git remote, and the saved GitHub CLI token is invalid. No Supabase or Render credentials are available. Follow these steps using your own accounts, then record the real results in [evidence](evidence/README.md) and [evaluation](evaluation.md). Do not paste passwords or deploy-hook URLs into chat, commands, screenshots, or Git.

## 1. Publish your own GitHub repository

1. In your GitHub account, create a new empty repository named `CloudDesk-Cloud-Helpdesk`. Choose public or private according to your presentation needs. Leave GitHub's README/license/.gitignore initialization unchecked because this workspace has its own files. No open-source license has been chosen; do not add one without deciding its terms.
2. Check `git status --short`, `git log --oneline`, and `git remote -v` in this workspace. Confirm the initial local commit contains no `.env`, database, logs, credentials, cache, or virtual environment. The branch is `main`.
3. Connect **your** repository and verify the URL before pushing:

```powershell
git remote add origin https://github.com/<YOUR_GITHUB_USER>/CloudDesk-Cloud-Helpdesk.git
git remote get-url origin
git push -u origin main
```

Replace the placeholder with your own username. The push and external repository creation require your approval. For later changes, open a pull request, check CI, and merge to `main`. A workflow file alone is not evidence of a successful GitHub Actions run.

## 2. Prepare Supabase PostgreSQL

1. In Supabase, create a **Free** project. Set and store a unique database password in a password manager. Wait for provisioning and check the project's current plan/quota.
2. In **Connect**, choose the **Session pooler** URI. Supabase's direct connection is IPv6 by default; its shared session pooler supports IPv4, which fits Render's IPv4 network. Use the actual endpoint shown by your project. [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
3. Fill the password placeholder locally or in Render's secret field. If it contains URI-special characters, percent-encode it. Add `sslmode=require` as a URI query parameter if missing (`?sslmode=require`, or `&sslmode=require` if a query already exists). Stronger `verify-ca`/`verify-full` modes can be used with the provider CA configuration. Render startup refuses a PostgreSQL URI without an explicit TLS mode. [Supabase SSL guide](https://supabase.com/docs/guides/platform/ssl-enforcement)
4. The app accepts `postgres://`, `postgresql://`, and `postgresql+psycopg://` URLs; it normalizes the first two for psycopg. Its pool has `pool_pre_ping`, two connections per worker, no overflow, and 30-minute recycling. The Render Blueprint sets one web worker. The local SQLite database remains a separate offline fallback and must not be used in public hosting.

### Apply migrations and create an admin without a paid Render shell

Render's pre-deploy command requires a paid instance, so run migrations **before first service creation** from your trusted computer with this repository and local Python dependencies. Your computer must be able to reach Supabase. This PowerShell prompt hides input; it leaves the URL only in the current process environment during the commands and then clears it:

```powershell
$privateUri = Read-Host 'Supabase session-pooler URI with sslmode=require' -AsSecureString
$privatePtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($privateUri)
try { $env:DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($privatePtr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($privatePtr) }
try {
  .\.venv\Scripts\flask.exe --app run:app db upgrade
  .\.venv\Scripts\flask.exe --app run:app db current
  .\.venv\Scripts\flask.exe --app run:app create-admin
}
finally { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue }
```

`db current` should show `bb7aa36d7612`. `create-admin` prompts for its own unique password without echo. Do not run `seed-demo` against Supabase. For later schema changes, take a backup, use backward-compatible migrations, run the migration once while the old app still works, then deploy the matching code. Supabase table editor should show `users`, `tickets`, `ticket_activities`, `login_failures`, and `alembic_version`. In the database UI, verify the `tickets.user_id` and activity foreign keys after migration. These migrations passed on a temporary local PostgreSQL 16 container, but Supabase itself has not been tested.

## 3. Create the Render service

1. Connect the GitHub repository to Render. Use `render.yaml` as the Blueprint or create a Docker web service manually: image source is this repository, plan **Free** if available, health path `/api/health`, and direct auto-deploy **off**. Keep the service name `clouddesk` or record your chosen name.
2. Add Render secret environment variables: `SECRET_KEY` (a newly generated unpredictable string of at least 32 characters) and `DATABASE_URL` (the Supabase session-pooler URI with TLS mode). Set `SESSION_COOKIE_SECURE=1` and `WEB_CONCURRENCY=1`. Render supplies `RENDER=true`, `RENDER_EXTERNAL_HOSTNAME`, and `PORT`; do not hardcode the port. The Docker command binds Gunicorn to `0.0.0.0:${PORT}`. Add `ALLOWED_HOSTS=your.custom.domain` only if using a custom domain. Keep debug off.
3. Start the first deployment after the migration. Confirm the service becomes healthy, open its actual `https://...onrender.com` URL, and check the logs without exposing environment values. The app rejects SQLite, short secrets, missing TLS mode, or a missing Render hostname at startup.
4. Run the live smoke test: register a new ordinary user; log in; create/read a ticket; sign out; sign in as the CLI-provisioned admin; see the ticket on the dashboard; change it to In Progress and Resolved; confirm the activity and SLA label. In Supabase, match the ticket ID, status, and foreign keys. Redeploy or restart the web service and check the same ticket again. Record the public URL and screenshots only after these observations.

The free web service can sleep after inactivity, so wake it before a demonstration. Render's filesystem is ephemeral, which is why Supabase is the persistent data store. [Render free limits](https://render.com/docs/free)

## 4. Enable validated deployment

1. In Render, create a deploy hook and store its entire URL as GitHub Actions repository secret `RENDER_DEPLOY_HOOK_URL`. Treat it as a credential. Keep Render direct auto-deploy off (`autoDeployTrigger: off` in the Blueprint). [Render deploy hooks](https://render.com/docs/deploy-hooks), [Blueprint setting](https://render.com/docs/blueprint-spec)
2. Open a pull request: validation runs Ruff, `pip-audit`, pytest, and Docker build; the PR never calls the deploy hook. After merging to `main`, the deployment job requests a Render deployment **only after validation succeeds**. With no hook secret, it records “deployment skipped” and does not fail normal validation. A successful hook response proves only that a deploy was requested; confirm Render logs and the live health endpoint afterward.
3. Save the GitHub workflow run URL, test count, audit/build result, deploy step summary, Render deployment ID/status, and public health result. Add them to the evidence log. For a new migration, apply it safely before merging the code that needs it; the free tier cannot run a pre-deploy migration command.

## Recovery and checks

| Symptom | First checks |
|---|---|
| Startup error | Render logs; `SECRET_KEY` length, TLS PostgreSQL URI, `RENDER_EXTERNAL_HOSTNAME`, migration version |
| Database timeout | Pooler endpoint/password, SSL query, Supabase project pause state, IPv4 compatibility |
| HTTP 400 on correct hostname | `TRUSTED_HOSTS`; add a custom domain in `ALLOWED_HOSTS` if needed |
| HTTP 500 | Application logs and latest schema revision; API responses intentionally omit tracebacks |
| CI green, no deployment | Deployment job summary and presence of GitHub hook secret; direct Render auto-deploy setting |
| Old ticket missing | Confirm signed-in owner, target database, and whether the public app uses Supabase |
| Sleep/pause | Wake Render or resume Supabase, then recheck database connectivity and public flow |

`/api/health` is liveness, not database readiness. Stdout request/error logs are available in Docker and Render; full metrics, alerting, and backup recovery tests are not implemented. The [evidence checklist](evidence/README.md) identifies every screenshot needed for the faculty demo.
