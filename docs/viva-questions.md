# CloudDesk viva questions and concise answers

1. **What problem does CloudDesk solve?** It centralizes IT requests with status, ownership, history, and SLA indicators.
2. **What is cloud computing?** On-demand compute, storage, and managed services delivered over a network.
3. **What is IaaS?** Infrastructure such as virtual machines and networks that you configure and operate.
4. **What is PaaS?** A platform that runs your application while managing much of the server setup; Render is used this way.
5. **What is SaaS?** Complete software delivered to end users; a hosted CloudDesk would be SaaS to students.
6. **Why Render?** It can run the Docker image and provide HTTPS, logs, and a deploy hook with simple operations.
7. **Why Supabase?** It supplies managed PostgreSQL so ticket data survives web instance replacement.
8. **Why PostgreSQL instead of SQLite in cloud?** PostgreSQL supports shared network access and concurrent hosted use; SQLite is best for the local single-instance demo.
9. **What is an application factory?** `create_app()` builds and configures Flask so tests and deployments can use different settings.
10. **Why Flask blueprints?** They keep authentication, tickets, admin, and API routes understandable without separate services.
11. **What is an ORM?** SQLAlchemy maps Python objects to database tables and parameterizes queries.
12. **Why migrations?** Alembic applies versioned schema changes without rebuilding production data.
13. **What is a foreign key?** A database link ensuring a ticket references an existing user.
14. **What is REST here?** Resource-oriented JSON endpoints under `/api` with HTTP methods and status codes.
15. **How does login work?** Flask-Login stores an authenticated user ID in a signed session cookie.
16. **Are passwords stored directly?** No. Werkzeug stores a salted password hash.
17. **What prevents admin self-promotion?** Public registration hardcodes `role=user`; admin creation is a CLI command.
18. **How are private tickets protected?** Every detail/update route checks the signed-in user's ID against `ticket.user_id`.
19. **What is CSRF?** A forged cross-site request using a victim's cookie; form and API writes require a token.
20. **Why UTC timestamps?** UTC avoids ambiguous storage; the interface converts to Asia/Kolkata for display.
21. **How is SLA calculated?** Compare resolution time or current time with creation plus the priority's illustrative 2/8/24-hour limit.
22. **What happens on reopen?** `resolved_at` is cleared and an activity row records the change.
23. **What is a Docker image?** A packaged filesystem and startup command for the app.
24. **What is a Docker container?** A running instance of an image.
25. **Why use a named volume?** It keeps local SQLite records when a container is replaced.
26. **What is CI/CD?** Automated validation and, after success, a controlled deployment trigger.
27. **What did GitHub Actions validate?** The verified main-branch run passed Ruff, `pip-audit`, 11 pytest tests, and Docker image build. PRs use the same validation job without production deployment.
28. **What is the deploy hook?** A secret Render URL called only after the main branch validation job passes.
29. **What monitoring exists?** A health endpoint and stdout request/error logs; full metrics/tracing are future work.
30. **What is vertical scaling?** Giving one instance more CPU or memory.
31. **What is horizontal scaling?** Running more web instances behind a load balancer; it is not implemented here.
32. **What would S3 add?** Private screenshot storage with short-lived authorized access; it is not implemented.
33. **What would Terraform add?** Versioned provisioning for an optional S3 bucket; it is not implemented or applied.
34. **What external result is verified?** The public GitHub repository and Actions validation run are verified. Live Render/Supabase deployment and public app persistence still need actual credentials and checks.
35. **How are brute-force login attempts limited?** Five failed attempts for one normalized email in 15 minutes yield HTTP 429. HMAC email digests and timestamps live in the shared database so workers share the count.
36. **What limits does that rate limiter have?** It is per account, not a global network firewall; concurrent attempts can slightly exceed the threshold.
37. **How does Render avoid using SQLite by accident?** Startup rejects non-PostgreSQL URLs, missing TLS mode, weak secrets, or a missing Render hostname.
38. **Why use Supabase's session pooler?** The direct endpoint is IPv6 by default, while the session pooler supports IPv4 access suitable for Render; the app opens a small pool per worker.
39. **Why run migrations before a free Render deployment?** The free instance lacks the paid pre-deploy command, so the trusted local CLI upgrades Supabase before the matching app version is deployed.
40. **What does a successful deploy-hook response prove?** Only that Render accepted a deploy request; service health and ticket persistence still need separate checks.
