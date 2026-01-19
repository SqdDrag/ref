from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from db.models import User, WebCheck
from db.session import get_session_factory


router = APIRouter()
_templates = Jinja2Templates(directory="web/templates")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _issue_captcha(user_id: int, token: str) -> tuple[bool, int, int]:
    a = secrets.randbelow(7) + 2
    b = secrets.randbelow(7) + 2
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.web_token or user.web_token != token:
            return False, a, b
        user.web_captcha_answer = str(a + b)
        user.web_captcha_at = datetime.now(timezone.utc)
        await session.commit()
    return True, a, b


async def _process_check(user_id: int, token: str, ip: str, answer: str) -> bool:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.web_token or user.web_token != token:
            session.add(WebCheck(user_id=user_id, ip=ip, status="fail"))
            await session.commit()
            return False
        if not user.web_captcha_answer or user.web_captcha_answer != answer.strip():
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
    ok, a, b = await _issue_captcha(user_id, token)
    return _templates.TemplateResponse(
        "verify.html",
        {"request": request, "status": "captcha" if ok else "fail", "a": a, "b": b, "user_id": user_id, "token": token},
    )


@router.post("/verify", response_class=HTMLResponse)
async def verify_submit(request: Request, user_id: int = Form(...), token: str = Form(...), answer: str = Form(...)):
    ip = _client_ip(request)
    ok = await _process_check(user_id, token, ip, answer)
    if ok:
        return _templates.TemplateResponse(
            "verify.html",
            {"request": request, "status": "success"},
        )
    issued, a, b = await _issue_captcha(user_id, token)
    return _templates.TemplateResponse(
        "verify.html",
        {
            "request": request,
            "status": "retry" if issued else "fail",
            "a": a,
            "b": b,
            "user_id": user_id,
            "token": token,
        },
    )


@router.get("/api/verify")
async def verify_api(request: Request, user_id: int, token: str, answer: str = ""):
    ip = _client_ip(request)
    ok = await _process_check(user_id, token, ip, answer)
    return JSONResponse({"status": "success" if ok else "fail"})


@router.get("/api/check-status")
async def check_status(user_id: int):
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.web_verified:
            return JSONResponse({"status": "fail"})
    return JSONResponse({"status": "success"})


