import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import users, cv
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cvanalyser")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")
    yield

app = FastAPI(
    title="CV Analyser API",
    docs_url="/docs" if os.environ.get("ENVIRONMENT", "development").lower() != "production" else None,
    redoc_url="/redoc" if os.environ.get("ENVIRONMENT", "development").lower() != "production" else None,
    lifespan=lifespan
)

# Global unhandled exception handler to prevent leaking internal traces in production
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    if os.environ.get("ENVIRONMENT", "development").lower() == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Parse allowed origins from environment (comma-separated list)
cors_origins_raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:80,http://localhost")
allow_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(cv.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the CV Analyser API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
