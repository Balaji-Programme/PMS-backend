import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.router import api_router

from app.utils.exceptions import add_exception_handlers
from app.models import *
from fastapi.staticfiles import StaticFiles

if not os.path.exists("uploads"):
    os.makedirs("uploads")

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not IS_PRODUCTION:
        Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()

app = FastAPI(
    title    = settings.PROJECT_NAME,
    version  = settings.VERSION,
    lifespan = lifespan,
    docs_url    = None if IS_PRODUCTION else "/docs",
    redoc_url   = None if IS_PRODUCTION else "/redoc",
    openapi_url = f"{settings.API_V1_STR}/openapi.json" if not IS_PRODUCTION else None,
)

add_exception_handlers(app)

app.add_middleware(GZipMiddleware, minimum_size=1024)

if IS_PRODUCTION:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "trucszohoreplicaapp.azurewebsites.net",
        "*.azurewebsites.net",
        "localhost",
        "127.0.0.1",
    ],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

_raw_origins: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if settings.BACKEND_CORS_ORIGINS:
    _raw_origins.extend([o.strip() for o in settings.BACKEND_CORS_ORIGINS])



if IS_PRODUCTION:
    _raw_origins = [o for o in _raw_origins if "azure" in o or "technorucs" in o] or ["https://trucszohoreplicaapp.azurewebsites.net"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_raw_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "ConsistencyLevel",
        "X-Forwarded-For",
        "X-Forwarded-Proto",
    ],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

class ForceHTTPSMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            if b"x-forwarded-proto" in headers:
                scope["scheme"] = headers[b"x-forwarded-proto"].decode("latin1").strip()
            elif IS_PRODUCTION:
                scope["scheme"] = "https"
        return await self.app(scope, receive, send)

app.add_middleware(ForceHTTPSMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to TechnoRUCS PMS Backend API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
