"""AAF Governance API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aaf.config import get_settings
from app.routers import governance, prompts

settings = get_settings()
app = FastAPI(title="AgileOps Agentic Framework", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(governance.router, prefix=settings.api_v1_prefix)
app.include_router(prompts.router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
