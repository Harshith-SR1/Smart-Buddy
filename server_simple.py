"""Simplified FastAPI server for Smart Buddy.

Avoids Pydantic version conflicts by using dict-based requests.
"""
import time
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from smart_buddy.memory import MemoryBank
from smart_buddy.agents.general_agent import GeneralAgent
from smart_buddy.agents.mentor import MentorAgent
from smart_buddy.agents.bestfriend import BestFriendAgent
from smart_buddy.agents.router import RouterAgent
from smart_buddy.metrics import metrics

app = FastAPI(title="Smart Buddy API", version="0.2.0")

# Shared memory and agents
memory = MemoryBank()
general_agent = GeneralAgent(memory=memory)
mentor_agent = MentorAgent(memory=memory)
bestfriend_agent = BestFriendAgent()
router_agent = RouterAgent(memory=memory)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "Smart Buddy API"}


@app.post("/chat")
def chat(request: Dict[str, Any]):
    """Chat endpoint accepting dict payload."""
    start_time = time.time()
    
    user_id = request.get("user_id", "user")
    session_id = request.get("session_id", "web_session")
    message = request.get("message", "").strip()
    mode = request.get("mode")
    
    if not message:
        raise HTTPException(status_code=400, detail="Empty message")
    
    try:
        if mode:
            # Direct mode routing
            envelope = {
                "meta": {"from": "api", "to": mode, "trace_id": f"api_{int(time.time()*1000)}"},
                "payload": {"user_id": user_id, "session_id": session_id, "text": message}
            }
            
            if mode == "general":
                result = general_agent.handle(envelope)
            elif mode == "mentor":
                result = mentor_agent.handle(envelope)
            elif mode == "bestfriend":
                result = bestfriend_agent.handle(envelope)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown mode: {mode}")
            
            reply = result.get("reply", "No reply")
            intent = mode
            trace_id = envelope["meta"]["trace_id"]
        else:
            # Auto routing
            routed = router_agent.route(user_id, session_id, message)
            envelope = routed.get("envelope", {})
            result = routed.get("result", {})
            reply = result.get("reply", "No reply")
            mode = envelope.get("meta", {}).get("to", "general")
            intent = envelope.get("payload", {}).get("intent", {}).get("intent", "unknown")
            trace_id = envelope.get("meta", {}).get("trace_id", "unknown")
        
        # Record metrics
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(mode=mode, intent=intent, latency_ms=latency_ms)
        
        return {
            "reply": reply,
            "trace_id": trace_id,
            "mode": mode,
            "latency_ms": round(latency_ms, 2)
        }
    
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(mode=mode or "unknown", intent="error", latency_ms=latency_ms, error=type(e).__name__)
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


@app.get("/metrics", response_class=HTMLResponse)
def get_metrics():
    """Real-time metrics dashboard."""
    return metrics.get_dashboard_html()


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": "Smart Buddy API", 
        "docs": "/docs", 
        "metrics": "/metrics",
        "endpoints": {
            "chat": "POST /chat",
            "tasks": "GET /tasks/{user_id}",
            "events": "GET /events/{user_id}",
            "metrics": "GET /metrics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Smart Buddy API Server...")
    print("📊 Metrics: http://127.0.0.1:8000/metrics")
    print("📖 Docs: http://127.0.0.1:8000/docs")
    uvicorn.run("server_simple:app", host="127.0.0.1", port=8000, reload=True)
