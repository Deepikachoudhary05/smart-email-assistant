from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from app.database.db import init_db
from app.routes import email_routes

load_dotenv()

# Initialize database
init_db()

app = FastAPI(
    title="Smart Email Proposal Agent API",
    description="Gmail integration and proposal generation API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(email_routes.router)

# Health endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Smart Email Proposal Agent API is running"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Smart Email Proposal Agent API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FASTAPI_PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)