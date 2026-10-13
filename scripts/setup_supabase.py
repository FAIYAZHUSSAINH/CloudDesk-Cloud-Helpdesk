"""Apply CloudDesk migrations to a Supabase session-pooler database."""

import os
import secrets
import subprocess
import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = "[YOUR-PASSWORD]"


def connection_url(template: str, password: str) -> str:
    if template.count(PLACEHOLDER) != 1:
        raise ValueError("Paste the Session pooler URI with [YOUR-PASSWORD] unchanged.")
    if not password:
        raise ValueError("The database password cannot be empty.")

    url = template.replace(PLACEHOLDER, quote(password, safe=""))
    parts = urlsplit(url)
    if (
        parts.scheme not in {"postgres", "postgresql"}
        or not parts.hostname
        or not parts.hostname.endswith(".pooler.supabase.com")
        or parts.port != 5432
        or not parts.username
        or not parts.username.startswith("postgres.")
        or parts.path != "/postgres"
    ):
        raise ValueError("Use the Supabase Shared pooler Session mode URI (port 5432).")
    ssl_mode = dict(parse_qsl(parts.query)).get("sslmode")
    if ssl_mode and ssl_mode not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("The URI must use sslmode=require or stronger.")
    if not ssl_mode:
        url += ("&" if parts.query else "?") + "sslmode=require"
    return url


def main() -> int:
    if sys.argv[1:] not in ([], ["--copy-render-url"]):
        print("Usage: setup_supabase.py [--copy-render-url]", file=sys.stderr)
        return 2
    print("Copy the URI from Supabase Connect > Session pooler.")
    print("Leave [YOUR-PASSWORD] in the URI; the password is entered separately.")
    template = input("Session pooler URI: ").strip()
    password = getpass("Supabase database password (hidden): ")
    try:
        url = connection_url(template, password)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    finally:
        del password

    if sys.argv[1:] == ["--copy-render-url"]:
        result = subprocess.run(["clip.exe"], input=url, text=True, check=False)
        if result.returncode:
            print("Could not copy the URL to the Windows clipboard.", file=sys.stderr)
            return result.returncode
        print("DATABASE_URL copied to the clipboard. Paste it into Render, then clear the clipboard.")
        return 0

    environment = os.environ.copy()
    environment["DATABASE_URL"] = url
    environment["SECRET_KEY"] = "migration-only-" + secrets.token_hex(32)
    for command in (("db", "upgrade"), ("db", "current")):
        result = subprocess.run(
            [sys.executable, "-m", "flask", "--app", "run:app", *command],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        if result.returncode:
            print("Supabase setup stopped; the command above failed.", file=sys.stderr)
            return result.returncode
    print("Expected revision: bb7aa36d7612")
    if input("Create a private CloudDesk admin now? [y/N]: ").strip().lower() in {"y", "yes"}:
        result = subprocess.run(
            [sys.executable, "-m", "flask", "--app", "run:app", "create-admin"],
            cwd=ROOT,
            env=environment,
            check=False,
        )
        if result.returncode:
            print("Admin creation failed; migration is still applied.", file=sys.stderr)
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
