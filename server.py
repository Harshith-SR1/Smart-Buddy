"""FastAPI server exposing Smart Buddy multi-agent endpoints.

Endpoints:
  POST /chat    -> Unified chat interface; optional `mode` to force agent.
  GET  /tasks/{user_id}  -> List tasks for user.
  GET  /events/{user_id} -> List calendar events for user.
  GET  /mentor/{user_id} -> Retrieve saved mentor plans/content.
  GET  /health  -> Basic health check.
  GET  /metrics -> Real-time metrics dashboard.

Design:
  - If `mode` provided in request body (general|mentor|bestfriend) dispatch directly.
  - Otherwise uses RouterAgent intent classification.
  - Returns trace_id for observability.
  - MemoryBank shared across agent instances.
  - Metrics collection for all requests.
"""

import time
from typing import Optional, Literal, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from smart_buddy.memory import MemoryBank
from smart_buddy.agents.general_agent import GeneralAgent
from smart_buddy.agents.mentor import MentorAgent
from smart_buddy.agents.bestfriend import BestFriendAgent
from smart_buddy.agents.router import RouterAgent
from smart_buddy.logging import get_logger
from smart_buddy.metrics import metrics

app = FastAPI(title="Smart Buddy API", version="0.2.0")
logger = get_logger(__name__)

# Shared memory instance
memory = MemoryBank()

# Instantiate agents
general_agent = GeneralAgent(memory=memory)
mentor_agent = MentorAgent(memory=memory)
bestfriend_agent = BestFriendAgent()
router_agent = RouterAgent(memory=memory)


class ChatRequest(BaseModel):
    user_id: str = "user"
    session_id: Optional[str] = "web_session"
    message: str
    mode: Optional[Literal["general", "mentor", "bestfriend"]] = None


class ChatResponse(BaseModel):
    reply: str
    trace_id: Optional[str] = None
    mode: str
    raw: Dict[str, Any]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Unified chat endpoint with metrics tracking.

    If `mode` specified, dispatch directly to that agent; else use RouterAgent
    for intent classification and routing.
    """
    start_time = time.time()
    text = req.message.strip()
    error = None
    
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")

    try:
        if req.mode:
            envelope = {
                "meta": {"from": "api", "to": req.mode, "trace_id": "direct"},
                "payload": {
                    "user_id": req.user_id,
                    "session_id": req.session_id or "web_session",
                    "text": text,
                },
            }
            if req.mode == "general":
                result = general_agent.handle(envelope)
            elif req.mode == "mentor":
                result = mentor_agent.handle(envelope)
            elif req.mode == "bestfriend":
                result = bestfriend_agent.handle(envelope)
            else:
                raise HTTPException(status_code=400, detail="Unsupported mode")
            reply = result.get("reply") or result.get("message") or "(no reply)"
            mode = req.mode
            intent = req.mode
            trace_id = envelope["meta"]["trace_id"]
        else:
            routed = router_agent.route(req.user_id, req.session_id or "web_session", text)
            envelope = routed.get("envelope", {})
            result = routed.get("result", {})
            reply = result.get("reply") or "(no reply)"
            mode = envelope.get("meta", {}).get("to", "general")
            intent = envelope.get("payload", {}).get("intent", {}).get("intent", "unknown")
            trace_id = envelope.get("meta", {}).get("trace_id")
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Record metrics
        metrics.record_request(
            mode=mode,
            intent=intent,
            latency_ms=latency_ms,
            tokens=0,  # TODO: extract from LLM response if available
            error=None
        )
        
        return ChatResponse(reply=reply, trace_id=trace_id, mode=mode, raw=result)
    
    except Exception as e:
        error = str(e)
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(
            mode=req.mode or "unknown",
            intent="error",
            latency_ms=latency_ms,
            error=type(e).__name__
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{user_id}")
def get_tasks(user_id: str) -> Dict[str, Any]:
    tasks = memory.get("tasks", user_id, []) or []
    return {"user_id": user_id, "tasks": tasks, "count": len(tasks)}


@app.get("/events/{user_id}")
def get_events(user_id: str) -> Dict[str, Any]:
    events = memory.get("events", user_id, []) or []
    return {"user_id": user_id, "events": events, "count": len(events)}


@app.get("/mentor/{user_id}")
def get_mentor_content(user_id: str) -> Dict[str, Any]:
    content = memory.get("mentor", user_id, {}) or {}
    return {"user_id": user_id, "mentor_content": content}


# Convenience root
@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Smart Buddy API. POST /chat to interact.", "docs": "/docs", "metrics": "/metrics"}


@app.get("/metrics", response_class=HTMLResponse)
def get_metrics():
    """Real-time metrics dashboard."""
    return metrics.get_dashboard_html()


if __name__ == "__main__":
    # Allow running via: python server.py
    import uvicorn
    print("🚀 Starting Smart Buddy API Server...")
    print("📊 Metrics dashboard: http://127.0.0.1:8000/metrics")
    print("📖 API docs: http://127.0.0.1:8000/docs")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
