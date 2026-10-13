# CloudDesk evidence register

Evidence is dated 13 October 2026 unless a later date is written beside an item. Screenshots in this folder are captured from the actual **local Docker** app at `http://127.0.0.1:8000`; they must not be described as Render/Supabase evidence. The [verification table](../evaluation.md) distinguishes implemented configuration from external verification.

| Item requested for evaluation | Status | Evidence to show or capture |
|---|---|---|
| Local application and user login | Captured | [Desktop login](login-desktop.png), [user dashboard](user-dashboard-local.png) |
| Ticket creation | Captured | [Ticket #5 after creation](ticket-created-local.png) with ID, status, priority |
| Admin dashboard | Captured | [Live counts and charts](admin-dashboard-local.png) after charts finished drawing |
| Ticket resolution and SLA | Captured | [Ticket #5 resolved](ticket-resolved-local.png) with activity and SLA Met |
| Supabase PostgreSQL records | Schema reported by user; screenshot and ticket record pending | User reported five migrated tables and private admin creation. After deployment, capture a ticket ID/status and visible foreign key columns in Table Editor, hiding credentials |
| Docker image/container | Verified; screenshot pending | Capture `docker compose ps`, `docker images clouddesk-web`, and `/api/health` result; include date and host |
| Successful GitHub Actions | Captured | [Real success screenshot](github-actions-success.png), [run 38352615426](https://github.com/FAIYAZHUSSAINH/CloudDesk-Cloud-Helpdesk/actions/runs/38352615426): Ruff, audit, 11 tests, Docker build; Render hook explicitly skipped |
| Render deployment | Not available | Capture service deployment status and logs after the deploy hook; hide environment values and hook URL |
| Public HTTPS application | Not available | Capture browser address bar, health 200, user ticket, admin flow, and post-redeploy persistence |
| Application logs | Local available; screenshot pending | Capture `docker compose logs --tail 30 web` without passwords; later capture Render logs |

The local run verified migration `bb7aa36d7612`, HTTP health 200, and 4 tickets/4 users after Docker container recreation. The browser flow then created and resolved ticket #5. A later Docker HTTP benchmark added 10 clearly named benchmark tickets; screenshots show the earlier dashboard state. GitHub Actions has a real passing run. The user completed the Supabase migration/admin setup and reported all five tables, but cloud ticket evidence is pending. Render has no public URL yet. The green deploy job performed no cloud deployment because the hook secret is absent.

## Manual cloud evidence checklist

1. Open the public `https://...onrender.com` URL and its `/api/health`; capture the address bar and response.
2. Register and log in as a new user; create a uniquely named test ticket. Save its ID and show its detail view.
3. Sign in as the private admin account. Capture dashboard counts, the ticket's status changes, activity history, and SLA label.
4. In Supabase table editor, locate the same ticket by ID, show the status and `user_id`, and verify `ticket_activities`. Crop out project credentials, query strings, and account details.
5. Trigger an ordinary deployment from a validated `main` commit. Capture the actual GitHub run URL and Render deployment status; then reload the same ticket and record that it persists.
6. Capture Render request logs and the current service plan. Never show `DATABASE_URL`, `SECRET_KEY`, deploy-hook URL, cookies, or passwords.

If cloud services sleep or pause during the presentation, use the verified local Docker flow and accurately describe the external items as unverified. The screenshots should be taken from the real interfaces; do not substitute generated images or typed console examples.
