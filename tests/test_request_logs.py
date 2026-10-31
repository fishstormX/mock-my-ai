from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from tests.conftest import OPENAI_KEY


def _register(client, prefix: str = "log") -> str:
    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    client.post(
        "/register",
        data={"email": email, "password": "password123", "display_name": prefix},
        follow_redirects=True,
    )
    return email


def _create_key(client) -> str:
    r = client.post("/console/keys", data={"name": "log-key"}, follow_redirects=True)
    m = re.search(r"sk-mock-[a-f0-9]{48}", r.text)
    assert m, "expected one-time raw API key"
    return m.group(0)


def test_request_logs_isolated_by_user(client):
    """User A must not see User B's traffic; sample-key traffic is not shown to console users."""
    from mock_my_ai.db import list_request_logs

    _register(client, "alice")
    key_a = _create_key(client)

    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key_a}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "alice-only-marker-xyz"}],
            "mock_seed": 101,
        },
    )
    assert r.status_code == 200

    # Sample key traffic (no user_id) — should not appear in Alice's console
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "sample-key-traffic"}],
            "mock_seed": 102,
        },
    )
    assert r.status_code == 200

    r = client.get("/console?tab=logs")
    assert r.status_code == 200
    assert "alice-only-marker-xyz" in r.text
    assert "sample-key-traffic" not in r.text
    # Full response JSON should be expandable
    assert "Response JSON" in r.text or "响应 JSON" in r.text
    assert '"choices"' in r.text or "choices" in r.text

    # Log out Alice, register Bob — Bob must not see Alice's marker
    client.get("/logout")
    _register(client, "bob")
    key_b = _create_key(client)
    client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {key_b}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "bob-only-marker-uvw"}],
            "mock_seed": 103,
        },
    )
    r = client.get("/console?tab=logs")
    assert "bob-only-marker-uvw" in r.text
    assert "alice-only-marker-xyz" not in r.text

    # Clear only clears own rows
    client.post("/console/logs/clear", follow_redirects=True)
    r = client.get("/console?tab=logs")
    assert "bob-only-marker-uvw" not in r.text

    # Direct DB: Alice's rows still exist if we query by her user — but clear was Bob's.
    # Re-login not needed; list without user_id still has Alice + sample rows.
    all_logs = list_request_logs(500)
    texts = " ".join((x.get("request_body") or "") for x in all_logs)
    assert "alice-only-marker-xyz" in texts


def test_request_log_retention_per_key_and_age(client):
    from mock_my_ai import db as dbmod

    _register(client, "ret")
    key = _create_key(client)

    # Insert 25 synthetic rows for this key → prune to 20
    from mock_my_ai.db import connect, resolve_api_key

    info = resolve_api_key(key)
    assert info is not None
    kid = info["key_id"]
    uid = info["user_id"]

    for i in range(25):
        dbmod.insert_request_log(
            method="POST",
            path="/v1/chat/completions",
            status=200,
            latency_ms=1,
            model="gpt-4o-mini",
            key_prefix=info["key_prefix"],
            client_ip="127.0.0.1",
            stream=False,
            request_body=f'{{"n":{i}}}',
            response_summary='{"ok":true}',
            response_body='{"ok":true}',
            user_id=uid,
            api_key_id=kid,
        )

    rows = dbmod.list_request_logs(100, user_id=uid)
    assert len(rows) == 20
    # Newest kept
    assert '"n":24' in (rows[0].get("request_body") or "")

    # Age prune: backdate all remaining, insert one fresh → old gone
    old = (datetime.now(timezone.utc) - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with dbmod._lock, connect() as conn:
        conn.execute(
            "UPDATE request_logs SET created_at = ? WHERE api_key_id = ?",
            (old, kid),
        )
    dbmod.insert_request_log(
        method="POST",
        path="/v1/chat/completions",
        status=200,
        latency_ms=1,
        model="gpt-4o-mini",
        key_prefix=info["key_prefix"],
        request_body='{"fresh":true}',
        response_body='{"fresh":true}',
        user_id=uid,
        api_key_id=kid,
    )
    rows = dbmod.list_request_logs(100, user_id=uid)
    assert len(rows) == 1
    assert '"fresh":true' in (rows[0].get("request_body") or "")


def test_landing_has_github_link(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "github.com/fishstormX/mock-my-ai" in r.text
