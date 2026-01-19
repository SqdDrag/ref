from __future__ import annotations

import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from hashlib import sha256

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from db.models import User, WebCheck
from db.session import get_session_factory


router = APIRouter()
_templates = Jinja2Templates(directory="web/templates")

_CAPTCHA_TTL = 300
_CAPTCHA_SECRET = os.getenv("CAPTCHA_SECRET", "dev-secret")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _sign(payload: str) -> str:
    return hmac.new(_CAPTCHA_SECRET.encode("utf-8"), payload.encode("utf-8"), sha256).hexdigest()


def _build_captcha(user_id: int, token: str) -> dict:
    a = secrets.randbelow(7) + 2
    b = secrets.randbelow(7) + 2
    ts = int(time.time())
    nonce = secrets.token_urlsafe(8)
    payload = f"{user_id}:{token}:{a}:{b}:{ts}:{nonce}"
    sig = _sign(payload)
    return {"a": a, "b": b, "ts": ts, "nonce": nonce, "sig": sig}


def _verify_captcha(user_id: int, token: str, a: int, b: int, ts: int, nonce: str, sig: str, answer: str) -> bool:
    if int(time.time()) - ts > _CAPTCHA_TTL:
        return False
    payload = f"{user_id}:{token}:{a}:{b}:{ts}:{nonce}"
    if not hmac.compare_digest(_sign(payload), sig):
        return False
    return answer.strip() == str(int(a) + int(b))


async def _token_ok(user_id: int, token: str) -> bool:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return bool(user and user.web_token and user.web_token == token)


async def _finish_verification(user_id: int, token: str, ip: str) -> bool:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.web_token or user.web_token != token:
            session.add(WebCheck(user_id=user_id, ip=ip, status="fail"))
            await session.commit()
            return False
        ip_result = await session.execute(select(User).where(User.ip == ip))
        existing = ip_result.scalar_one_or_none()
        if existing and existing.id != user_id:
            user.is_blocked = True
            session.add(WebCheck(user_id=user_id, ip=ip, status="fail"))
            await session.commit()
            return False
        user.ip = ip
        user.web_verified = True
        user.captcha_passed = True
        session.add(WebCheck(user_id=user_id, ip=ip, status="success"))
        await session.commit()
        return True


@router.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request, user_id: int, token: str):
    if not await _token_ok(user_id, token):
        return _templates.TemplateResponse(
            "verify.html",
            {"request": request, "status": "fail"},
        )
    captcha = _build_captcha(user_id, token)
    return _templates.TemplateResponse(
        "verify.html",
        {"request": request, "status": "captcha", "user_id": user_id, "token": token, **captcha},
    )


@router.post("/verify", response_class=HTMLResponse)
async def verify_submit(
    request: Request,
    user_id: int = Form(...),
    token: str = Form(...),
    answer: str = Form(...),
    a: int = Form(...),
    b: int = Form(...),
    ts: int = Form(...),
    nonce: str = Form(...),
    sig: str = Form(...),
):
    ip = _client_ip(request)
    ok = _verify_captcha(user_id, token, a, b, ts, nonce, sig, answer)
    if not ok:
        captcha = _build_captcha(user_id, token)
        return _templates.TemplateResponse(
            "verify.html",
            {
                "request": request,
                "status": "retry",
                "user_id": user_id,
                "token": token,
                **captcha,
            },
        )
    verified = await _finish_verification(user_id, token, ip)
    return _templates.TemplateResponse(
        "verify.html",
        {"request": request, "status": "success" if verified else "fail"},
    )


@router.get("/api/check-status")
async def check_status(user_id: int):
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.web_verified:
            return JSONResponse({"status": "fail"})
    return JSONResponse({"status": "success"})
