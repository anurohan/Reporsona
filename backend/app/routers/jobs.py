from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.database import SessionLocal, get_db
from app.models import Job
from app.schemas import JobOut
from app.services.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


def _snapshot(job_id: str) -> dict | None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return None
        return {
            "event": "SNAPSHOT",
            "job_id": job.id,
            "persona_id": job.persona_id,
            "status": job.status,
            "progress": job.progress,
            "current_stage": job.current_stage,
            "stages": job.stages,
            "stats": job.stats,
            "error": job.error,
        }
    finally:
        db.close()


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request):
    snap = _snapshot(job_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = job_manager.subscribe(job_id)

    async def event_gen():
        try:
            # initial snapshot so late subscribers get current state
            yield {"event": "SNAPSHOT", "data": json.dumps(snap)}

            if snap["status"] in ("completed", "failed"):
                terminal = "COMPLETED" if snap["status"] == "completed" else "FAILED"
                yield {"event": terminal, "data": json.dumps(snap)}
                return

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    # keep-alive; also re-check terminal state from DB
                    cur = _snapshot(job_id)
                    yield {"event": "PING", "data": json.dumps({"progress": cur["progress"] if cur else 0})}
                    if cur and cur["status"] in ("completed", "failed"):
                        break
                    continue

                yield {"event": event.get("event", "MESSAGE"), "data": json.dumps(event)}
                if event.get("event") in ("COMPLETED", "FAILED"):
                    break
        finally:
            job_manager.unsubscribe(job_id, queue)

    return EventSourceResponse(event_gen())
