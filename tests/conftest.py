from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mock_my_ai.config import get_config

get_config.cache_clear()
from mock_my_ai.db import configure_db
from mock_my_ai.main import create_app


@pytest.fixture(scope="session")
def client(tmp_path_factory) -> TestClient:
    # Isolated SQLite so console tests don't touch the developer's data/app.db
    db_dir = tmp_path_factory.mktemp("mock_my_ai_db")
    db_path = Path(db_dir) / "test.db"
    configure_db(db_path)

    # Ensure session secret is stable for the process
    cfg = get_config()
    cfg.console.db_path = str(db_path)

    app = create_app()
    with TestClient(app) as c:
        yield c


OPENAI_KEY = "sk-mock-openai-demo-key-0123456789abcdef"
ANTHROPIC_KEY = "sk-ant-mock-anthropic-demo-key-0123456789"
GEMINI_KEY = "AIzaMockGeminiDemoKey0123456789abcdef"
