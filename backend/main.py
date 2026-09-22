from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import users, cv

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CV Analyser API")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(cv.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the CV Analyser API"}
