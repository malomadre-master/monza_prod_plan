from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.routers import attachments, auth, orders, users
from app.seed import seed_admin, seed_work_centers


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        if settings.database_url.startswith("sqlite"):
            Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_admin(db)
            seed_work_centers(db)
        finally:
            db.close()
    except Exception:
        # tests / API without a reachable database
        pass
    yield


app = FastAPI(title="MONZA Production Planner", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(attachments.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "monza-prod-plan"}
