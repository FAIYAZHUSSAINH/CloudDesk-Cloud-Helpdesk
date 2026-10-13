"""Small, repeatable local Flask test-client latency sample."""

import json
import re
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask_migrate import upgrade

from app import create_app
from app.extensions import db
from app.models import User


def measure(name, operation, samples=20):
    durations = []
    errors = 0
    for _ in range(samples):
        start = time.perf_counter()
        response = operation()
        durations.append((time.perf_counter() - start) * 1000)
        errors += response.status_code >= 400
    ordered = sorted(durations)
    return {"operation": name, "samples": samples, "mean_ms": round(statistics.mean(durations), 2), "median_ms": round(statistics.median(durations), 2), "p95_ms": round(ordered[18], 2), "errors": errors}


def main():
    with tempfile.TemporaryDirectory() as temporary:
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(Path(temporary) / 'bench.db').as_posix()}"})
        with app.app_context():
            upgrade()
            user = User(name="Benchmark User", email="benchmark@example.test", role="user")
            user.set_password("benchmark-only-password")
            db.session.add(user)
            db.session.commit()
        client = app.test_client()
        csrf = re.search(rb'name="csrf_token" value="([^"]+)"', client.get("/login").data).group(1).decode()
        client.post("/login", data={"email": "benchmark@example.test", "password": "benchmark-only-password", "csrf_token": csrf})
        headers = {"X-CSRFToken": csrf}
        payload = {"title": "Benchmark ticket", "description": "Local benchmark request", "category": "Software", "priority": "Low"}
        first = client.post("/api/tickets", json=payload, headers=headers).json["ticket"]["id"]
        results = [
            measure("GET /api/health", lambda: client.get("/api/health")),
            measure("POST /api/tickets", lambda: client.post("/api/tickets", json=payload, headers=headers)),
            measure("GET /api/tickets/<id>", lambda: client.get(f"/api/tickets/{first}")),
            measure("GET /api/dashboard/stats", lambda: client.get("/api/dashboard/stats")),
        ]
        print(json.dumps({"environment": "Flask test client, Python 3.12, temporary SQLite; no network", "results": results}, indent=2))
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


if __name__ == "__main__":
    main()
