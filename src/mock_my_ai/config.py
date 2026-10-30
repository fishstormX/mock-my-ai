from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    docs_enabled: bool = True


class AuthConfig(BaseModel):
    require_api_key: bool = True
    # When True, any key matching accepted_prefixes is allowed (legacy demo mode).
    # When False (default for console product feel), only sample keys + DB console keys.
    accept_prefix_keys: bool = False
    accepted_prefixes: list[str] = Field(
        default_factory=lambda: ["sk-mock-", "sk-ant-mock-", "AIzaMock"]
    )
    sample_keys: dict[str, str] = Field(default_factory=dict)
    session_secret: str | None = None


class GenerationConfig(BaseModel):
    # In-response tool_use count (per HTTP call). Random inclusive range;
    # soft-stop / agent_tool_steps_max still end multi-turn Claude loops.
    tool_loop_min: int = 0
    tool_loop_max: int = 3
    # Across-conversation agent loop budget (prior tool_use/tool_result in
    # messages). Once reached, respond with text+thinking only (end_turn).
    agent_tool_steps_max: int = 3
    cache_ratio_min: float = 0.20
    cache_ratio_max: float = 0.80
    deepseek_cache_ratio_min: float = 0.90
    deepseek_cache_ratio_max: float = 0.99
    thinking_enabled_default: bool = True
    thinking_token_min: int = 20
    thinking_token_max: int = 120
    search_enabled_default: bool = False
    default_temperature: float = 1.0
    max_output_segments: int = 3


class ToolsConfig(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["echo", "list_files"])
    list_files_root: str = "./"
    list_files_max: int = 50


class CustomModel(BaseModel):
    id: str
    owned_by: str = "custom"
    family: str = "openai"
    parameter_count: str | None = None
    context_window: int | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class ModelsConfig(BaseModel):
    catalog_source: str = "https://models.dev/api.json"
    catalog_cache_path: str = "data/models_catalog_cache.json"
    catalog_ttl_hours: float = 24
    catalog_auto_refresh: bool = True
    custom: list[CustomModel] = Field(default_factory=list)


class CorpusConfig(BaseModel):
    path: str = "data/corpus"
    custom_qa_path: str = "data/corpus/custom_qa.json"
    primary_languages: list[str] = Field(
        default_factory=lambda: ["en", "zh", "ja", "es", "fr"]
    )
    fallback_language: str = "en"


class ConsoleConfig(BaseModel):
    db_path: str = "data/app.db"
    public_base_url: str = ""


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    corpus: CorpusConfig = Field(default_factory=CorpusConfig)
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)
    root: Path = Field(default_factory=_project_root)

    def db_path(self) -> Path:
        p = Path(self.console.db_path)
        return p if p.is_absolute() else self.root / p

    def session_secret(self) -> str:
        if self.auth.session_secret:
            return self.auth.session_secret
        secret_file = self.root / "data" / ".session_secret"
        if secret_file.exists():
            return secret_file.read_text(encoding="utf-8").strip()
        import secrets as _secrets

        secret_file.parent.mkdir(parents=True, exist_ok=True)
        val = _secrets.token_urlsafe(48)
        secret_file.write_text(val, encoding="utf-8")
        return val

    def corpus_dir(self) -> Path:
        p = Path(self.corpus.path)
        return p if p.is_absolute() else self.root / p

    def custom_qa_file(self) -> Path:
        p = Path(self.corpus.custom_qa_path)
        return p if p.is_absolute() else self.root / p

    def list_files_root(self) -> Path:
        p = Path(self.tools.list_files_root)
        return p if p.is_absolute() else self.root / p


class Settings(BaseSettings):
    mock_my_ai_config: str | None = None
    mock_my_ai_require_api_key: bool | None = None

    model_config = {"env_file": ".env", "extra": "ignore"}


def load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


@lru_cache
def get_config() -> AppConfig:
    settings = Settings()
    root = _project_root()
    cfg_path = Path(settings.mock_my_ai_config) if settings.mock_my_ai_config else root / "config" / "default.yaml"
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    raw = load_yaml_config(cfg_path)
    app = AppConfig.model_validate({**raw, "root": root})
    if settings.mock_my_ai_require_api_key is not None:
        app.auth.require_api_key = settings.mock_my_ai_require_api_key
    if os.getenv("MOCK_MY_AI_ACCEPT_PREFIX_KEYS"):
        app.auth.accept_prefix_keys = os.environ["MOCK_MY_AI_ACCEPT_PREFIX_KEYS"].lower() in (
            "1",
            "true",
            "yes",
        )
    if os.getenv("MOCK_MY_AI_PUBLIC_BASE_URL"):
        app.console.public_base_url = os.environ["MOCK_MY_AI_PUBLIC_BASE_URL"].rstrip("/")
    if os.getenv("MOCK_MY_AI_SESSION_SECRET"):
        app.auth.session_secret = os.environ["MOCK_MY_AI_SESSION_SECRET"]
    # Allow env overrides for host/port
    if os.getenv("MOCK_MY_AI_HOST"):
        app.server.host = os.environ["MOCK_MY_AI_HOST"]
    if os.getenv("MOCK_MY_AI_PORT"):
        app.server.port = int(os.environ["MOCK_MY_AI_PORT"])
    return app
