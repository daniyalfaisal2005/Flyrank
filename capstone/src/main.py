from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from . import db
from .checker import run_check_cycle
from .config import APP_PORT, CHECK_INTERVAL_MINUTES
from .routes.auth import router as auth_router
from .routes.jobs import router as jobs_router
from .routes.watches import router as watches_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_check_cycle,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="check_cycle",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    job = scheduler.get_job("check_cycle")
    print(f"PagePulse: schema ready | checker every {CHECK_INTERVAL_MINUTES} min "
          f"| next run: {job.next_run_time}", flush=True)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="PagePulse", version="0.4.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(watches_router)
app.include_router(jobs_router)


@app.get("/health")
def health():
    db_ok = db.db_healthy()
    return {"status": "ok" if db_ok else "degraded", "database": "up" if db_ok else "down"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=APP_PORT)
