from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models.database import init_db
from app.routers import calculator, financial, history, scientific

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Calculator API", version="2.0.0", lifespan=lifespan)

# The frontend is normally served by this same app (http://localhost:8000), so CORS is
# only needed if you open the HTML from somewhere else (file://, python -m http.server...).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calculator.router, prefix="/api/calculator", tags=["calculator"])
app.include_router(scientific.router, prefix="/api/scientific", tags=["scientific"])
app.include_router(financial.router, prefix="/api/financial", tags=["financial"])
app.include_router(history.router, prefix="/api/history", tags=["history"])


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Must be last: serves index.html, styles.css, *.js at "/".
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
