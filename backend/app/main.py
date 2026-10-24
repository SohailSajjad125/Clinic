import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import ai, scheduler
from .api import admin, audit, auth, billing, clinical, doctors, documents, misc, portal, public, settings as clinic_settings, staff, trash
from .core.config import IS_DEV, settings

log = logging.getLogger("clinicos")
JSON_LIMIT, UPLOAD_LIMIT = 1 * 1024 * 1024, 12 * 1024 * 1024
GLOBAL_LIMIT, GLOBAL_WINDOW = int(__import__("os").getenv("GLOBAL_RATE_LIMIT", "600")), 60
_ip_hits: dict = defaultdict(deque)
DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


@asynccontextmanager
async def lifespan(_):
    if IS_DEV:
        log.warning("ENVIRONMENT=%s: API docs are enabled and production checks are relaxed. Never run like this on the internet.", settings.environment)
    scheduler.start()
    yield


app = FastAPI(title="ClinicOS API", version="1.1.0", lifespan=lifespan, debug=False,
              docs_url="/docs" if IS_DEV else None, redoc_url=None, openapi_url="/openapi.json" if IS_DEV else None)


class Hardening:
    """Pure-ASGI middleware: security headers on every response, global per-IP rate limit, request size limits."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        ip = (scope.get("client") or ("unknown",))[0]
        now, q = time.monotonic(), _ip_hits[ip]
        while q and now - q[0] > GLOBAL_WINDOW:
            q.popleft()
        if len(q) >= GLOBAL_LIMIT:
            return await self._reply(scope, receive, send, 429, "Too many requests. Please slow down.", {"retry-after": "30"})
        q.append(now)
        limit = UPLOAD_LIMIT if "/documents" in path else JSON_LIMIT
        cl = dict(scope["headers"]).get(b"content-length")
        if cl and cl.isdigit() and int(cl) > limit:
            return await self._reply(scope, receive, send, 413, "That request is too large.")
        seen = 0

        async def limited_receive():
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > limit:
                    raise StarletteHTTPException(413, "That request is too large.")
            return msg

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                h = list(message.get("headers", []))
                add = {b"x-content-type-options": b"nosniff", b"x-frame-options": b"DENY", b"referrer-policy": b"no-referrer", b"cross-origin-resource-policy": b"same-site",
                       b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=()", b"cache-control": b"no-store"}
                if not IS_DEV:
                    add[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"
                if path not in DOC_PATHS:
                    add[b"content-security-policy"] = b"default-src 'none'; frame-ancestors 'none'"
                have = {k.lower() for k, _ in h}
                h += [(k, v) for k, v in add.items() if k not in have]
                message = {**message, "headers": h}
            await send(message)

        started = False

        async def tracked_send(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send_with_headers(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except Exception:  # last line of defence: even crashes get a generic body plus security and CORS headers
            log.exception("Unhandled error on %s %s", scope["method"], path)
            if not started:
                await self._reply(scope, receive, tracked_send, 500, "Something went wrong on our side. Please try again.")

    async def _reply(self, scope, receive, send, code, detail, extra=None):
        resp = JSONResponse({"detail": detail}, status_code=code, headers=extra)
        return await resp(scope, receive, send)


app.add_middleware(Hardening)
app.add_middleware(  # added last = outermost, so even rate-limit/size errors carry CORS headers
    CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,  # bearer tokens, no cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"], max_age=600)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    # FastAPI's default echoes the submitted values (including passwords) back. Send only where and why.
    return JSONResponse(status_code=422, content={"detail": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


for r in (auth.router, staff.router, staff.trash, trash.router, clinical.router, doctors.router, billing.router, documents.router, portal.router, clinic_settings.router, audit.router, admin.router, misc.router, ai.router, public.router):
    app.include_router(r, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
