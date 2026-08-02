import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers.chat import router as chat_router
from app.services import faq_service, session_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dostt Support Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router)


@app.on_event("startup")
async def startup() -> None:
    faq_service.load_faqs()
    asyncio.create_task(session_service.cleanup_loop())
    logger.info("Dostt Support Chatbot started.")


# Serve the compiled React frontend (production)
_STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"
_INDEX = _STATIC_DIR / "index.html"

if _STATIC_DIR.exists():
    # Explicit SPA routes — must be declared before StaticFiles mount
    @app.get("/user")
    @app.get("/USER")
    @app.get("/listener")
    @app.get("/LISTENER")
    async def spa_root():
        return FileResponse(str(_INDEX))

    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
    logger.info("Serving frontend from %s", _STATIC_DIR)
else:
    logger.info(
        "Frontend build not found at %s — run 'npm run build' inside /frontend to serve the UI.",
        _STATIC_DIR,
    )
