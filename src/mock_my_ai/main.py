from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from mock_my_ai.request_log import RequestLogMiddleware

from mock_my_ai import __version__
from mock_my_ai.config import get_config
from mock_my_ai.routes import anthropic_routes, gemini_routes, openai_routes, web


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    from mock_my_ai.db import configure_db
    from mock_my_ai.models_catalog_refresh import ensure_catalog

    configure_db(cfg.db_path())
    # Load cache / bundled snapshot; refresh in background if stale.
    ensure_catalog(allow_network=True)
    yield


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title="Mock My AI",
        description=(
            "Open-source mock server compatible with OpenAI, Anthropic, and Gemini API shapes. "
            "Responses are corpus-based fakes — never real provider calls."
        ),
        version=__version__,
        docs_url="/api/docs" if cfg.server.docs_enabled else None,
        redoc_url="/api/redoc" if cfg.server.docs_enabled else None,
        openapi_url="/openapi.json" if cfg.server.docs_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=cfg.session_secret(),
        session_cookie="mock_my_ai_session",
        same_site="lax",
        https_only=False,
        max_age=14 * 24 * 3600,
    )
    # Outer-ish: added after Session so it wraps closer to the app for body access.
    app.add_middleware(RequestLogMiddleware)

    # Marketing / console routes first so `/` is the product site (not the old inline page).
    app.include_router(web.router)
    app.include_router(openai_routes.router)
    app.include_router(anthropic_routes.router)
    app.include_router(gemini_routes.router)

    pkg = Path(__file__).resolve().parent
    static_dir = pkg / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    docs_site = Path(__file__).resolve().parents[2] / "site"
    if docs_site.is_dir():
        app.mount("/docs", StaticFiles(directory=str(docs_site), html=True), name="mkdocs")

    @app.get("/healthz")
    async def healthz() -> dict:
        from mock_my_ai.corpus import get_corpus

        c = get_corpus()
        return {
            "status": "ok",
            "version": __version__,
            "corpus": {lang: c.count(lang) for lang in cfg.corpus.primary_languages},
        }

    @app.get("/docs")
    async def docs_redirect():
        if docs_site.is_dir():
            return RedirectResponse(url="/docs/")
        return RedirectResponse(url="/api/docs")

    return app


app = create_app()


def run() -> None:
    import uvicorn

    cfg = get_config()
    uvicorn.run(
        "mock_my_ai.main:app",
        host=cfg.server.host,
        port=cfg.server.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
