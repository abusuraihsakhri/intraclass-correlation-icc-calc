"""FastAPI service: ICC point estimates plus the existing audit endpoints."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from icc_calc import calculate_from_ratings
from .base import AuditLogger
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(
    title="Intraclass Correlation Calculator API",
    description="Balanced-design ANOVA ICCs and a separate experimental audit API.",
    version="3.1.0",
)


class ChatRequest(BaseModel):
    query: str


class ICCRequest(BaseModel):
    ratings: list[list[float]] = Field(
        ..., description="Rectangular rows of subjects, columns of the same raters"
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "intraclass-correlation-icc-calc",
            "version": "3.1.0"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "audit_integrity_verified": AuditLogger.verify_integrity(),
    }


@app.post("/api/icc")
def api_icc(payload: ICCRequest):
    try:
        return calculate_from_ratings(payload.ratings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    return supervisor.process_task(payload).to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(),
            "verified": AuditLogger.verify_integrity()}
