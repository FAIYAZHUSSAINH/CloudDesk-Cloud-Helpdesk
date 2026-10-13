"""Small authenticated HTTP benchmark for the local Docker demo.

Requires the locally seeded Aarav account and DEMO_USER_PASSWORD in ignored .env.
Creates 10 benchmark tickets; use only against a local disposable/demo database.
"""

import http.cookiejar
import json
import math
import re
import statistics
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from dotenv import dotenv_values


BASE_URL = "http://127.0.0.1:8000"
SAMPLES = 10


def main():
    password = dotenv_values(Path(__file__).resolve().parents[1] / ".env").get("DEMO_USER_PASSWORD")
    if not password:
        raise SystemExit("Set DEMO_USER_PASSWORD in ignored .env and seed the local Docker demo first")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def send(path, data=None, headers=None):
        request = urllib.request.Request(BASE_URL + path, data=data, headers=headers or {})
        with opener.open(request, timeout=10) as response:
            return response.status, response.read()

    _, login_page = send("/login")
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', login_page).group(1).decode()
    login_data = urllib.parse.urlencode({"email": "aarav@example.test", "password": password, "csrf_token": csrf}).encode()
    status, dashboard = send("/login", login_data, {"Content-Type": "application/x-www-form-urlencoded"})
    if status != 200 or b"Good to see you" not in dashboard:
        raise SystemExit("Local demo login failed; check the seeded account password")
    _, ticket_page = send("/tickets/new")
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', ticket_page).group(1).decode()
    headers = {"Content-Type": "application/json", "X-CSRFToken": csrf}
    run_id = uuid.uuid4().hex[:8]

    def measure(operation):
        durations = []
        errors = 0
        last = None
        for index in range(SAMPLES):
            start = time.perf_counter()
            code, body = operation(index)
            durations.append((time.perf_counter() - start) * 1000)
            errors += code >= 400
            last = body
        ordered = sorted(durations)
        return {
            "requests": SAMPLES,
            "mean_ms": round(statistics.mean(durations), 2),
            "median_ms": round(statistics.median(durations), 2),
            "p95_ms": round(ordered[math.ceil(0.95 * SAMPLES) - 1], 2),
            "errors": errors,
        }, last

    health, _ = measure(lambda _: send("/api/health"))

    def create(index):
        payload = {"title": f"HTTP benchmark {run_id} #{index}", "description": "Local Docker latency sample", "category": "Software", "priority": "Low"}
        return send("/api/tickets", json.dumps(payload).encode(), headers)

    creation, created = measure(create)
    ticket_id = json.loads(created)["ticket"]["id"]
    retrieval, _ = measure(lambda _: send(f"/api/tickets/{ticket_id}"))
    stats, _ = measure(lambda _: send("/api/dashboard/stats"))
    print(json.dumps({"environment": "Docker Gunicorn over localhost HTTP, SQLite named volume; 10 requests per route", "created_ticket_prefix": f"HTTP benchmark {run_id}", "results": {"health": health, "creation": creation, "retrieval": retrieval, "stats": stats}}, indent=2))


if __name__ == "__main__":
    main()
