from __future__ import annotations

import re
import uuid

from tests.conftest import OPENAI_KEY


def test_landing_is_marketing_site(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.text
    assert "Mock My AI" in html
    assert "tailwind" in html.lower() or "bg-accent" in html or "shadow-glow" in html
    assert "/register" in html
    assert "v1/chat/completions" in html


def test_models_page(client):
    r = client.get("/models")
    assert r.status_code == 200
    assert "gpt-4o-mini" in r.text
    assert "parameter" in r.text.lower() or "参数" in r.text or "Params" in r.text or "参数量" in r.text


def test_register_login_create_key_and_chat(client):
    email = f"user_{uuid.uuid4().hex[:10]}@example.com"
    password = "password123"

    # Register
    r = client.post(
        "/register",
        data={"email": email, "password": password, "display_name": "Tester"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert r.headers["location"] == "/console"

    # Console HTML while logged in
    r = client.get("/console")
    assert r.status_code == 200
    assert "Tester" in r.text or email.split("@")[0] in r.text

    # Create API key
    r = client.post(
        "/console/keys",
        data={"name": "ci-key"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    r = client.get("/console?tab=keys")
    assert r.status_code == 200
    # Raw key shown once in flash banner
    m = re.search(r"sk-mock-[a-f0-9]{48}", r.text)
    assert m, "expected one-time raw API key in console flash"
    raw_key = m.group(0)

    # Chat with console key
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello from console key"}],
            "mock_seed": 11,
        },
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"]

    # Sample key still works
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "still demo"}],
            "mock_seed": 12,
        },
    )
    assert r.status_code == 200


def test_ip_whitelist_denies_other_ip(client):
    email = f"ip_{uuid.uuid4().hex[:10]}@example.com"
    password = "password123"

    client.post(
        "/register",
        data={"email": email, "password": password, "display_name": "IPUser"},
        follow_redirects=True,
    )
    r = client.post("/console/keys", data={"name": "locked"}, follow_redirects=True)
    m = re.search(r"sk-mock-[a-f0-9]{48}", r.text)
    assert m, "expected one-time raw key after create"
    raw_key = m.group(0)

    # Restrict to an IP that is NOT the TestClient host ("testclient")
    r = client.post(
        "/console/ips",
        data={"cidr": "203.0.113.50"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    # Call without matching IP → 403
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {raw_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "blocked?"}],
            "mock_seed": 13,
        },
    )
    assert r.status_code == 403
    detail = r.json()["detail"]
    # FastAPI may wrap detail
    blob = str(detail)
    assert "ip_not_allowed" in blob or "allowlist" in blob.lower() or "not on" in blob.lower()

    # Matching X-Forwarded-For allows
    r = client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {raw_key}",
            "X-Forwarded-For": "203.0.113.50",
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "allowed"}],
            "mock_seed": 14,
        },
    )
    assert r.status_code == 200


def test_custom_model_in_console_and_list(client):
    email = f"model_{uuid.uuid4().hex[:10]}@example.com"
    client.post(
        "/register",
        data={"email": email, "password": "password123", "display_name": "Mod"},
        follow_redirects=True,
    )
    mid = f"my-org/custom-{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/console/models",
        data={
            "model_id": mid,
            "family": "openai",
            "owned_by": "custom",
            "parameter_count": "8B",
            "context_window": "32000",
            "thinking": "on",
            "multimodal": "on",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert mid in r.text

    r = client.get("/models")
    assert mid in r.text
    assert "8B" in r.text

    r = client.get("/v1/models", headers={"Authorization": f"Bearer {OPENAI_KEY}"})
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()["data"]}
    assert mid in ids


def test_logout_and_console_requires_login(client):
    client.get("/logout")
    r = client.get("/console", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")


def test_set_lang(client):
    r = client.get("/set-lang?lang=en&next=/", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.cookies.get("lang") == "en"


def test_console_search_toggle_and_request_logs(client):
    import uuid

    email = f"set_{uuid.uuid4().hex[:10]}@example.com"
    client.post(
        "/register",
        data={"email": email, "password": "password123", "display_name": "Setter"},
        follow_redirects=True,
    )

    # Settings tab shows search switch (default off)
    r = client.get("/console?tab=settings")
    assert r.status_code == 200
    assert "setting_search" not in r.text  # i18n resolved
    assert "Mock search" in r.text or "模拟搜索" in r.text or "search" in r.text.lower()

    # Enable search via console
    r = client.post(
        "/console/settings/search",
        data={"search_enabled": "on"},
        follow_redirects=True,
    )
    assert r.status_code == 200

    # Search-capable model now gets citations
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": "sk-ant-mock-anthropic-demo-key-0123456789"},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "hello search please"}],
            "mock_seed": 70,
        },
    )
    assert r.status_code == 200
    assert r.json()["mock_my_ai"]["search_results"]

    # Disable again
    r = client.post(
        "/console/settings/search",
        data={},  # unchecked checkbox → off
        follow_redirects=True,
    )
    assert r.status_code == 200

    r = client.post(
        "/v1/messages",
        headers={"x-api-key": "sk-ant-mock-anthropic-demo-key-0123456789"},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "hello again"}],
            "mock_seed": 71,
        },
    )
    assert r.status_code == 200
    assert r.json()["mock_my_ai"]["search_results"] is None

    # Request logs are key-isolated: sample-key traffic does not appear for this user.
    # Create a console key, call the API, then expect the path in logs.
    r = client.post("/console/keys", data={"name": "log-check"}, follow_redirects=True)
    m = re.search(r"sk-mock-[a-f0-9]{48}", r.text)
    assert m
    raw = m.group(0)
    r = client.post(
        "/v1/messages",
        headers={"x-api-key": raw},
        json={
            "model": "claude-sonnet-4-5",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": "console-log-check"}],
            "mock_seed": 72,
        },
    )
    assert r.status_code == 200

    r = client.get("/console?tab=logs")
    assert r.status_code == 200
    assert "/v1/messages" in r.text
    assert "console-log-check" in r.text

