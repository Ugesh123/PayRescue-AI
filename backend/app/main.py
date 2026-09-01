import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.core.database import get_session
from app.api import routes_transactions, routes_dashboard, routes_webhooks, routes_analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="PayRescue AI")

# Vite's dev server runs on 5173 by default. Without this, every frontend
# fetch call fails at the browser level before it even reaches FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_transactions.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_webhooks.router)
app.include_router(routes_analytics.router)


@app.get("/health")
def health_check(session: Session = Depends(get_session)):
    session.exec(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
