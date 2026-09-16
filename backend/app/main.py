from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, jobs, onboarding, preferences, profile
from app.db import init_db
from app.seed import ensure_seed_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_seed_user()
    yield


app = FastAPI(title="Resume Tailor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(onboarding.router)
app.include_router(profile.router)
app.include_router(preferences.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
