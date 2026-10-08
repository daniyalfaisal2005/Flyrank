from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db
from .config import APP_PORT
from .routes.watches import router as watches_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    print("PagePulse: database schema ready")
    yield


app = FastAPI(title="PagePulse", version="0.2.0", lifespan=lifespan)
app.include_router(watches_router)


@app.get("/health")
def health():
    db_ok = db.db_healthy()
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=APP_PORT)
