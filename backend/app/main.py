from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import init_db
from .api import profile, cv, applications, examples, linkedin, settings, ai, scanner

app = FastAPI(title="CareerKit Local", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
