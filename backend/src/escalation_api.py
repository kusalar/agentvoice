"""
escalation_api.py — FastAPI REST API for the Human Escalation Dashboard.

Runs on port 8001.  Start with:
    uv run uvicorn src.escalation_api:app --port 8001 --reload

Endpoints:
    GET  /api/escalations              — list all tickets (optional ?status= filter)
    GET  /api/escalations/{ref_id}     — single ticket
    POST /api/escalations/{ref_id}/status  — update status { "status": "in_progress" }
    POST /api/escalations/{ref_id}/resolve — shortcut to mark resolved + trigger callback
    GET  /api/escalations/stats        — counts per status & urgency
"""

import asyncio
import logging
import os
import sys

# Ensure src/ is importable when running from backend root
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from escalations import (
    get_escalation,
    init_escalations_db,
    list_escalations,
    update_escalation_status,
)

logger = logging.getLogger("escalation_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Local Commerce — Escalation Dashboard API",
    description="Manage human-in-the-loop escalation tickets for the voice agent.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow Next.js dev server (ports 3000, 3001) and production origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_escalations_db()
    logger.info("Escalation API started — DB initialized.")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class StatusUpdate(BaseModel):
    status: str  # open | in_progress | resolved


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def read_root():
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Ignore favicon requests."""
    return Response(status_code=204)

@app.get("/api/escalations/stats")
def get_stats():
    """Return counts of tickets by status and urgency."""
    all_tickets = list_escalations()
    stats = {
        "total": len(all_tickets),
        "by_status": {"open": 0, "in_progress": 0, "resolved": 0},
        "by_urgency": {"emergency": 0, "high": 0, "medium": 0, "low": 0},
    }
    for t in all_tickets:
        s = t.get("status", "open")
        u = t.get("urgency", "medium")
        if s in stats["by_status"]:
            stats["by_status"][s] += 1
        if u in stats["by_urgency"]:
            stats["by_urgency"][u] += 1
    return stats


@app.get("/api/escalations")
def get_all_escalations(status: str | None = Query(default=None)):
    """
    List all escalation tickets.
    Optional query param: ?status=open | in_progress | resolved
    """
    tickets = list_escalations(status_filter=status)
    return {"tickets": tickets, "count": len(tickets)}


@app.get("/api/escalations/{ref_id}")
def get_single_escalation(ref_id: str):
    """Fetch a single escalation ticket by its reference ID."""
    ticket = get_escalation(ref_id.upper())
    if not ticket:
        raise HTTPException(status_code=404, detail=f"No ticket found with ref_id '{ref_id}'.")
    return ticket


@app.post("/api/escalations/{ref_id}/status")
def update_status(ref_id: str, body: StatusUpdate):
    """Update the status of an escalation ticket."""
    result = update_escalation_status(ref_id.upper(), body.status)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Update failed."))
    return result


@app.post("/api/escalations/{ref_id}/resolve")
async def resolve_and_callback(ref_id: str):
    """
    Mark ticket as resolved and (optionally) trigger outbound callback via Day 6 dial.py.
    The callback is fire-and-forget; failure does not prevent resolution.
    """
    result = update_escalation_status(ref_id.upper(), "resolved")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Resolve failed."))

    # Attempt outbound callback
    ticket = get_escalation(ref_id.upper())
    callback_attempted = False
    callback_error = None
    if ticket:
        caller_user_id = ticket.get("caller_user_id", "")
        if caller_user_id:
            try:
                from dial import make_outbound_call
                # Fire-and-forget in background
                asyncio.create_task(make_outbound_call(user_id=caller_user_id))
                callback_attempted = True
                logger.info(f"Outbound callback triggered for user_id='{caller_user_id}' (ticket {ref_id})")
            except Exception as e:
                callback_error = str(e)
                logger.warning(f"Outbound callback failed for ticket {ref_id}: {e}")

    return {
        **result,
        "callback_attempted": callback_attempted,
        "callback_error": callback_error,
    }


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("escalation_api:app", host="0.0.0.0", port=8001, reload=True)
