"""Marketing site + auth pages + console (Jinja2)."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from mock_my_ai import __version__
from mock_my_ai.config import get_config
from mock_my_ai.i18n import Translator, pick_lang
from mock_my_ai.models_catalog import builtin_models_flat, catalog_source_info

router = APIRouter(tags=["Web Console"])

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _lang(request: Request) -> str:
    return pick_lang(
        request.cookies.get("lang"),
        request.query_params.get("lang"),
        request.headers.get("accept-language"),
    )


def _tr(request: Request) -> Translator:
    return Translator(_lang(request))


def _user(request: Request) -> dict[str, Any] | None:
    uid = request.session.get("user_id")
    if not uid:
        return None
    from mock_my_ai.db import get_user_by_id

    return get_user_by_id(int(uid))


def _base_url(request: Request) -> str:
    cfg = get_config()
    if cfg.console.public_base_url:
        return cfg.console.public_base_url
    # Prefer forwarded proto/host behind nginx
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")


def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
    lang = _lang(request)
    t = Translator(lang)
    user = _user(request)
    cfg = get_config()
    return {
        "request": request,
        "t": t,
        "lang": lang,
        "user": user,
        "version": __version__,
        "base_url": _base_url(request),
        "sample_keys": cfg.auth.sample_keys,
        "studio": "妙妙鱼",
        "author": "fishstormX",
        "contact": "stormnetwork@163.com",
        **extra,
    }


def _set_lang_cookie(resp: Response, lang: str) -> None:
    resp.set_cookie("lang", lang, max_age=365 * 24 * 3600, httponly=False, samesite="lax")


@router.get("/set-lang")
async def set_lang(request: Request, lang: str = "en", next: str = "/"):
    lang = lang if lang in ("en", "zh") else "en"
    # Prevent open redirect
    if not next.startswith("/"):
        next = "/"
    resp = RedirectResponse(url=next, status_code=303)
    _set_lang_cookie(resp, lang)
    return resp


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    resp = templates.TemplateResponse(request, "landing.html", _ctx(request))
    if "lang" not in request.cookies:
        _set_lang_cookie(resp, _lang(request))
    return resp


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _user(request):
        return RedirectResponse("/console", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", _ctx(request, error=None))


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    from mock_my_ai.db import authenticate_user

    t = _tr(request)
    user = authenticate_user(email, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            _ctx(request, error=t("err_invalid_credentials"), email=email),
            status_code=400,
        )
    request.session["user_id"] = user["id"]
    return RedirectResponse("/console", status_code=303)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if _user(request):
        return RedirectResponse("/console", status_code=303)
    return templates.TemplateResponse(request, "auth/register.html", _ctx(request, error=None))


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
):
    from mock_my_ai.db import create_user

    t = _tr(request)
    try:
        user = create_user(email, password, display_name or None)
    except ValueError as e:
        code = str(e)
        msg = {
            "email_taken": t("err_email_taken"),
            "password_too_short": t("err_password_short"),
            "invalid_email": t("err_invalid_email"),
        }.get(code, t("err_generic"))
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            _ctx(request, error=msg, email=email, display_name=display_name),
            status_code=400,
        )
    request.session["user_id"] = user["id"]
    return RedirectResponse("/console", status_code=303)


@router.post("/logout")
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/me")
async def me(request: Request):
    user = _user(request)
    if not user:
        return JSONResponse({"authenticated": False}, status_code=401)
    return {"authenticated": True, "user": user}


def _require_user(request: Request) -> dict[str, Any] | RedirectResponse:
    user = _user(request)
    if not user:
        return RedirectResponse(f"/login?next={quote(str(request.url.path))}", status_code=303)
    return user


@router.get("/console", response_class=HTMLResponse)
async def console_home(request: Request):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import (
        get_search_enabled,
        list_api_keys,
        list_custom_models,
        list_ip_whitelist,
        list_request_logs,
    )

    keys = list_api_keys(user["id"])
    ips = list_ip_whitelist(user["id"])
    customs = list_custom_models(user["id"])
    builtins = builtin_models_flat()
    catalog_meta = catalog_source_info()
    flash_key = request.session.pop("flash_raw_key", None)
    flash_msg = request.session.pop("flash_msg", None)
    active = request.query_params.get("tab", "keys")
    logs = list_request_logs(100) if active == "logs" else []
    return templates.TemplateResponse(
        request,
        "console/index.html",
        _ctx(
            request,
            keys=keys,
            ips=ips,
            customs=customs,
            builtins=builtins,
            catalog_meta=catalog_meta,
            flash_raw_key=flash_key,
            flash_msg=flash_msg,
            active_tab=active,
            search_enabled=get_search_enabled(),
            request_logs=logs,
        ),
    )


@router.post("/console/keys")
async def console_create_key(request: Request, name: str = Form("default")):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import create_api_key

    created = create_api_key(user["id"], name=name or "default")
    request.session["flash_raw_key"] = created["raw_key"]
    request.session["flash_msg"] = "key_created"
    return RedirectResponse("/console?tab=keys", status_code=303)


@router.post("/console/keys/{key_id}/revoke")
async def console_revoke_key(request: Request, key_id: int):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import revoke_api_key

    revoke_api_key(user["id"], key_id)
    return RedirectResponse("/console?tab=keys", status_code=303)


@router.post("/console/ips")
async def console_add_ip(request: Request, cidr: str = Form(...)):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import add_ip_whitelist

    try:
        add_ip_whitelist(user["id"], cidr)
    except ValueError:
        request.session["flash_msg"] = "invalid_cidr"
    return RedirectResponse("/console?tab=ips", status_code=303)


@router.post("/console/ips/{entry_id}/delete")
async def console_del_ip(request: Request, entry_id: int):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import remove_ip_whitelist

    remove_ip_whitelist(user["id"], entry_id)
    return RedirectResponse("/console?tab=ips", status_code=303)


@router.post("/console/models")
async def console_add_model(
    request: Request,
    model_id: str = Form(...),
    family: str = Form("openai"),
    owned_by: str = Form("custom"),
    parameter_count: str = Form(""),
    context_window: str = Form(""),
    thinking: str | None = Form(None),
    search: str | None = Form(None),
    multimodal: str | None = Form(None),
):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import upsert_custom_model

    cw: int | None = None
    if context_window.strip():
        try:
            cw = int(context_window.strip().replace(",", "").replace("_", ""))
        except ValueError:
            cw = None
    features = {
        "thinking": thinking == "on",
        "search": search == "on",
        "multimodal_input": multimodal == "on",
    }
    try:
        upsert_custom_model(
            user["id"],
            model_id,
            family=family,
            owned_by=owned_by or "custom",
            parameter_count=parameter_count.strip() or None,
            context_window=cw,
            features=features,
        )
    except ValueError as e:
        request.session["flash_msg"] = str(e)
    return RedirectResponse("/console?tab=models", status_code=303)


@router.post("/console/models/{row_id}/delete")
async def console_del_model(request: Request, row_id: int):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import delete_custom_model

    delete_custom_model(user["id"], row_id)
    return RedirectResponse("/console?tab=models", status_code=303)



@router.post("/console/settings/search")
async def console_set_search(request: Request, search_enabled: str | None = Form(None)):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import set_search_enabled

    set_search_enabled(search_enabled == "on")
    request.session["flash_msg"] = "search_saved"
    return RedirectResponse("/console?tab=settings", status_code=303)


@router.post("/console/logs/clear")
async def console_clear_logs(request: Request):
    user = _require_user(request)
    if isinstance(user, RedirectResponse):
        return user
    from mock_my_ai.db import clear_request_logs

    clear_request_logs()
    request.session["flash_msg"] = "logs_cleared"
    return RedirectResponse("/console?tab=logs", status_code=303)


@router.get("/models", response_class=HTMLResponse)
async def models_public(request: Request):
    """Public model browser (no login required)."""
    from mock_my_ai.db import list_custom_models

    builtins = builtin_models_flat()
    customs = list_custom_models(user_id=None)
    catalog_meta = catalog_source_info()
    return templates.TemplateResponse(
        request,
        "models.html",
        _ctx(request, builtins=builtins, customs=customs, catalog_meta=catalog_meta),
    )
