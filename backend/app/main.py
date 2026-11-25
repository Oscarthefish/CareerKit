import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.database import init_db
from .api import profile, cv, applications, examples, linkedin, settings, ai, scanner, reachouts, insights
from .ai.base import ModelError

log = logging.getLogger("careerkit")

app = FastAPI(title="CareerKit Local", version="1.0.0")


@app.exception_handler(ModelError)
async def model_error(request: Request, exc: ModelError):
    # 502: the backend is fine, the model behind it failed.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# Registered before CORSMiddleware so it sits inside it: an unhandled error
# then still gets CORS headers. Without them the browser discards the 500 and
# the frontend can only report "Cannot reach the CareerKit API".
@app.middleware("http")
async def readable_unhandled_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - last-resort handler
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={
            "detail": f"The backend hit an unexpected error ({type(exc).__name__}: {exc}). See the backend log."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8899", "http://127.0.0.1:8899",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "CareerKit Local"}


app.include_router(profile.router)
app.include_router(cv.router)
app.include_router(applications.router)
app.include_router(examples.router)
app.include_router(linkedin.router)
app.include_router(settings.router)
app.include_router(ai.router)
app.include_router(scanner.router)
app.include_router(reachouts.router)
app.include_router(insights.router)
