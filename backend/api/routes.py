# backend/api/routes.py
"""
FastAPI router that wires OpenAPI endpoints to the VertexLLM implementation.

This module maps endpoints from openapi.yaml:
- POST /v1/generate -> VertexLLM.generate_async
- POST /v1/citation/verify -> placeholder verification logic
- POST /v1/plagiarism/check -> placeholder plagiarism check
- POST /v1/embeddings -> placeholder embeddings call (should call Vertex embeddings or other service)
- POST /v1/memory/query -> simple memory lookup (uses VertexLLM internal cache if conversation_id provided)
- GET /health -> service health
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import time
import os
import logging
import httpx
import html

from pydantic import BaseModel, Field

# Import the models and default instance
from backend.models.vertex_llm import (
    GenerateRequest,
    GenerateResponse,
    get_default_llm,
    VertexLLM,
)

router = APIRouter()

logger = logging.getLogger("esh27-routes")

async def send_telegram_notification(message: str) -> None:
    bot_token = os.getenv("ESH27BOT")
    chat_id = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )

# New models for leads endpoint
class LeadWorkRequest(BaseModel):
    name: str = Field(..., description="Name of the contractor or daily worker")
    phone: str = Field(..., description="Phone number")
    city: str = Field(..., description="City")
    trade: str = Field(..., description="Trade profession")
    role: str = Field(..., description="Role")
    count: int = Field(1, description="Count of workers")
    notes: Optional[str] = Field(None, description="Additional notes")


# Lightweight models for the other endpoints (these mirror openapi.yaml)
class CitationVerifyRequest(BaseModel):
    content: str
    citations: List[Dict[str, Any]]


class CitationVerifyResponse(BaseModel):
    verified: bool
    details: Dict[str, Any] = {}


class PlagiarismCheckRequest(BaseModel):
    content: str
    language: Optional[str] = "en"


class PlagiarismCheckResponse(BaseModel):
    plagiarism_score: float = 0.0
    matches: List[Dict[str, Any]] = []


class EmbeddingsRequest(BaseModel):
    input: List[str]


class EmbeddingsResponse(BaseModel):
    embeddings: List[Dict[str, Any]]


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class MemoryQueryResponse(BaseModel):
    results: List[Dict[str, Any]] = []


# health meta
_start_time = time.time()

@router.get("/health", tags=["health"])
async def health():
    return JSONResponse(status_code=200, content={"status": "ok", "uptime_seconds": time.time() - _start_time})


# Dependency provider for LLM instance
def get_llm() -> VertexLLM:
    return get_default_llm()


@router.post("/api/v1/leads/work", tags=["leads"])
async def create_lead_work(req: LeadWorkRequest):
    """
    Capture a new contractor/daily worker lead.
    Validates payload and sends an immediate Telegram notification.
    """
    message = (
        f"<b>New Lead: {html.escape(req.role)}</b>\n"
        f"<b>Name:</b> {html.escape(req.name)}\n"
        f"<b>Phone:</b> <a href='tel:{html.escape(req.phone)}'>{html.escape(req.phone)}</a>\n"
        f"<b>City:</b> {html.escape(req.city)}\n"
        f"<b>Trade:</b> {html.escape(req.trade)}\n"
        f"<b>Count:</b> {req.count}"
    )
    if req.notes:
        message += f"\n<b>Notes:</b> {html.escape(req.notes)}"

    await send_telegram_notification(message)
    return JSONResponse(status_code=200, content={"status": "success", "message": "Lead captured successfully"})


@router.post("/v1/generate", response_model=GenerateResponse, tags=["generation"])
async def generate_endpoint(request: GenerateRequest, llm: VertexLLM = Depends(get_llm)):
    """
    Generate text using VertexLLM.generate_async.
    Security (Bearer/API Key) should be enforced by upstream middleware / dependencies.
    """
    try:
        response = await llm.generate_async(request)
        return response
    except Exception as exc:
        # Map to 500 for generic server errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/v1/citation/verify", response_model=CitationVerifyResponse, tags=["verification"])
async def citation_verify(req: CitationVerifyRequest):
    """
    Basic placeholder: in production, implement citation resolution and verification logic.
    For now, returns verified=False and notes there is no authoritative verification.
    """
    # Placeholder logic: return false unless citations explicitly mention "cloud.google.com"
    details = {}
    verified = True
    for c in req.citations:
        url = c.get("url", "")
        if "cloud.google.com" not in url:
            verified = False
            details[c.get("citation_id", "unknown")] = "No authoritative match found"
        else:
            details[c.get("citation_id", "unknown")] = "Authoritative Google Cloud doc matched"
    return CitationVerifyResponse(verified=verified, details=details)


@router.post("/v1/plagiarism/check", response_model=PlagiarismCheckResponse, tags=["verification"])
async def plagiarism_check(req: PlagiarismCheckRequest):
    """
    Placeholder plagiarism checker. Integrate with a real plagiarism detection service for production.
    """
    # Very naive heuristic: if content contains "Copied:" assume higher score
    score = 0.0
    matches = []
    if "Copied:" in req.content:
        score = 0.9
        matches.append({"source": "example-suspect", "excerpt": "Copied: ...", "similarity": 0.92})
    return PlagiarismCheckResponse(plagiarism_score=score, matches=matches)


@router.post("/v1/embeddings", response_model=EmbeddingsResponse, tags=["embeddings"])
async def embeddings(req: EmbeddingsRequest):
    """
    Placeholder embeddings endpoint. Replace with Vertex Embeddings or external vectorizer in production.
    Returns very small deterministic vectors to let the calling services function.
    """
    embeddings_out = []
    for text in req.input:
        # deterministic pseudo-embedding: map characters to small floats (not useful for production)
        vec = [float((ord(ch) % 10) - 5) / 10.0 for ch in (text[:32] or " ")]
        embeddings_out.append({"input": text, "vector": vec})
    return EmbeddingsResponse(embeddings=embeddings_out)


@router.post("/v1/memory/query", response_model=MemoryQueryResponse, tags=["embeddings", "memory"])
async def memory_query(req: MemoryQueryRequest, conversation_id: Optional[str] = None, llm: VertexLLM = Depends(get_llm)):
    """
    Query the in-memory TTL conversation cache. If conversation_id is provided and context exists,
    perform a fuzzy top-k by simple substring scoring. This is intentionally simple; replace with
    a vector DB and real similarity search for production.
    """
    results = []
    if conversation_id:
        try:
            # Accessing protected member _get_context intentionally for demo; wrap in a safer API in production.
            context = llm._get_context(conversation_id)
            if context:
                # Naive scoring: number occurrences of query terms
                q = req.query.lower()
                lines = [ln.strip() for ln in context.splitlines() if ln.strip()]
                for idx, ln in enumerate(lines):
                    score = (ln.lower().count(q)) / max(1, len(q))
                    if score > 0:
                        results.append({"id": f"{conversation_id}:{idx}", "text": ln, "score": float(score)})
                # sort and top_k
                results = sorted(results, key=lambda r: r["score"], reverse=True)[: req.top_k or 5]
        except Exception:
            pass
    return MemoryQueryResponse(results=results)
