from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import battles, formats, internal_router, leaderboard_router, providers

app = FastAPI(title="Agent Arena", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(formats.router)
app.include_router(providers.router)
app.include_router(battles.router)
app.include_router(leaderboard_router.router)
app.include_router(internal_router.router)


@app.get("/health")
def health():
    return {"status": "ok", "project": settings()["APPWRITE_PROJECT_ID"]}
