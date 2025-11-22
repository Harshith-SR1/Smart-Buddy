"""Lightweight HTTP server for Smart Buddy using Flask.

Avoids FastAPI/Pydantic version conflicts.
Perfect for local testing and demos.
"""
import time
import json
import logging
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, send_from_directory
import os

logger = logging.getLogger(__name__)
app = Flask(__name__)
AUDIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <title>Smart Buddy Audit Console</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #0d1117; color: #e6edf3; }
        h1 { color: #7dd3fc; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border-bottom: 1px solid rgba(255,255,255,0.1); padding: 8px; text-align: left; }
        th { text-transform: uppercase; font-size: 12px; letter-spacing: .05em; color: #bae6fd; }
        .status-open { color: #fbbf24; }
        .status-overridden { color: #22c55e; }
        .panel { background: #161b22; padding: 16px; border-radius: 8px; }
        input, textarea { width: 100%; padding: 8px; margin-top: 6px; border-radius: 4px; border: none; }
        button { margin-top: 10px; padding: 8px 14px; border: none; border-radius: 4px; background: #2563eb; color: white; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Smart Buddy Audit Console</h1>
    <div class=\"panel\">
        <form method=\"post\" action=\"/audit/override\">
            <label>Event ID</label>
            <input name=\"event_id\" type=\"number\" required />
            <label>Note</label>
            <textarea name=\"note\" rows=\"3\" required></textarea>
            <label>Actor</label>
            <input name=\"actor\" placeholder=\"judge\" />
            <button type=\"submit\">Override Event</button>
        </form>
    </div>
    <table>
        <tr><th>ID</th><th>Type</th><th>Trace</th><th>Severity</th><th>Status</th><th>Payload</th></tr>
        {% for event in events %}
            <tr>
                <td>{{ event.id }}</td>
                <td>{{ event.event_type }}</td>
                <td>{{ event.trace_id }}</td>
                <td>{{ event.severity }}</td>
                <td class=\"status-{{ event.status }}\">{{ event.status }}</td>
                <td><pre style=\"white-space: pre-wrap; font-size: 11px;\">{{ json.dumps(event.payload, indent=2) }}</pre></td>
            </tr>
        {% endfor %}
    </table>
</body>
</html>
"""


# Lazy initialization to avoid import errors on startup
_memory = None
_general_agent = None
_mentor_agent = None
_bestfriend_agent = None
_router_agent = None
_metrics = None


def get_agents():
    """Lazy load agents on first request."""
    global _memory, _general_agent, _mentor_agent, _bestfriend_agent, _router_agent, _metrics
    
    if _memory is None:
        from smart_buddy.memory import MemoryBank
        from smart_buddy.agents.general_agent import GeneralAgent
        from smart_buddy.agents.mentor import MentorAgent
        from smart_buddy.agents.bestfriend import BestFriendAgent
        from smart_buddy.agents.router import RouterAgent
        from smart_buddy.metrics import metrics
        from smart_buddy.audit import audit_trail  # noqa: F401 - ensure module initialized
        
        _memory = MemoryBank()
        _general_agent = GeneralAgent(memory=_memory)
        _mentor_agent = MentorAgent(memory=_memory)
        _bestfriend_agent = BestFriendAgent()
        _router_agent = RouterAgent(memory=_memory)
        _metrics = metrics
    
    assert _memory is not None
    assert _general_agent is not None
    assert _mentor_agent is not None
    assert _bestfriend_agent is not None
    assert _router_agent is not None
    assert _metrics is not None

    return _memory, _general_agent, _mentor_agent, _bestfriend_agent, _router_agent, _metrics


@app.route("/", methods=["GET"])
def root():
    """Serve the chat interface."""
    # Redirect to chat UI
    return redirect('/chat-ui')


@app.route("/chat-ui", methods=["GET"])
def chat_ui():
    """Serve the Google AI Agent-style chat interface."""
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    chat_html_path = os.path.join(static_dir, 'chat.html')
    
    try:
        with open(chat_html_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({"error": "Chat UI not found"}), 404


@app.route("/api", methods=["GET"])
def api_info():
    """API information endpoint."""
    return jsonify({
        "service": "Smart Buddy API",
        "version": "1.0",
        "endpoints": {
            "chat_ui": "GET / or GET /chat-ui",
            "chat": "POST /chat",
            "tasks": "GET /tasks/<user_id>",
            "events": "GET /events/<user_id>",
            "metrics": "GET /metrics",
            "health": "GET /health",
            "audit": "GET /audit"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Smart Buddy"})


@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint with file upload support."""
    memory, general_agent, mentor_agent, bestfriend_agent, router_agent, metrics = get_agents()
    start_time = time.time()
    
    # Check if this is a file upload (multipart/form-data) or JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle file upload
        user_id = request.form.get("user_id", "user")
        session_id = request.form.get("session_id", "web_session")
        message = request.form.get("message", "").strip()
        mode = request.form.get("mode")
        file_count = int(request.form.get("file_count", 0))
        
        # Process uploaded files with image/video support
        file_info = []
        image_data = []
        for i in range(file_count):
            file_key = f"file_{i}"
            if file_key in request.files:
                file = request.files[file_key]
                if file.filename:
                    # Read file content
                    content = file.read()
                    content_type = file.content_type or "unknown"
                    file_info.append({
                        "name": file.filename,
                        "size": len(content),
                        "type": content_type
                    })
                    
                    # Handle text files
                    if 'text' in content_type:
                        try:
                            text_content = content.decode('utf-8')
                            message += f"\n\n--- File: {file.filename} ---\n{text_content[:1000]}"
                        except:
                            message += f"\n\n[File: {file.filename} - binary content, {len(content)} bytes]"
                    
                    # Handle image files
                    elif 'image' in content_type:
                        import base64
                        b64_data = base64.b64encode(content).decode('utf-8')
                        image_data.append({
                            "filename": file.filename,
                            "mime_type": content_type,
                            "data": b64_data
                        })
                        message += f"\n\n[📷 Image: {file.filename}]"
                        logger.info(f"Image file received: {file.filename} ({len(content)} bytes)")
                    
                    # Handle video files
                    elif 'video' in content_type:
                        # Extract video metadata
                        video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
                        is_video = any(file.filename.lower().endswith(fmt) for fmt in video_formats)
                        if is_video:
                            message += f"\n\n[🎥 Video: {file.filename}, {len(content)} bytes, {content_type}]"
                            logger.info(f"Video file received: {file.filename} ({len(content)} bytes)")
                    
                    # Other binary files
                    else:
                        message += f"\n\n[📄 File: {file.filename} - {len(content)} bytes, {content_type}]"
        
        if file_info:
            file_summary = ", ".join([f"{f['name']} ({f['size']} bytes)" for f in file_info])
            logger.info(f"Received {len(file_info)} files: {file_summary}")
        
        # If images present, enhance message for vision analysis
        if image_data:
            message += f"\n\nI've uploaded {len(image_data)} image(s). Please analyze what you see."
    else:
        # Handle regular JSON request
        data = request.get_json() or {}
        user_id = data.get("user_id", "user")
        session_id = data.get("session_id", "web_session")
        message = data.get("message", "").strip()
        mode = data.get("mode")
    
    if not message:
        return jsonify({"error": "Empty message"}), 400
    
    try:
        if mode:
            # Direct mode
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
                return jsonify({"error": f"Unknown mode: {mode}"}), 400
            
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
        
        # Metrics
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(mode=mode, intent=intent, latency_ms=latency_ms)
        
        return jsonify({
            "reply": reply,
            "trace_id": trace_id,
            "mode": mode,
            "latency_ms": round(latency_ms, 2)
        })
    
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_request(mode=mode or "unknown", intent="error", latency_ms=latency_ms, error=type(e).__name__)
        return jsonify({"error": str(e)}), 500


@app.route("/tasks/<user_id>", methods=["GET"])
def get_tasks(user_id):
    memory, _, _, _, _, _ = get_agents()
    tasks = memory.get("tasks", user_id, []) or []
    return jsonify({"user_id": user_id, "tasks": tasks, "count": len(tasks)})


@app.route("/events/<user_id>", methods=["GET"])
def get_events(user_id):
    memory, _, _, _, _, _ = get_agents()
    events = memory.get("events", user_id, []) or []
    return jsonify({"user_id": user_id, "events": events, "count": len(events)})


@app.route("/mentor/<user_id>", methods=["GET"])
def get_mentor(user_id):
    memory, _, _, _, _, _ = get_agents()
    content = memory.get("mentor", user_id, {}) or {}
    return jsonify({"user_id": user_id, "mentor_content": content})


@app.route("/metrics", methods=["GET"])
def get_metrics():
    """HTML metrics dashboard."""
    _, _, _, _, _, metrics = get_agents()
    return metrics.get_dashboard_html()


@app.route("/audit", methods=["GET"])
def audit_console():
    from smart_buddy.audit import audit_trail

    events = audit_trail.list_events(limit=150)
    return render_template_string(AUDIT_TEMPLATE, events=events, json=json)


@app.route("/audit/export", methods=["GET"])
def audit_export():
    from smart_buddy.audit import audit_trail

    events = audit_trail.export()
    return jsonify({"count": len(events), "events": events})


@app.route("/audit/override", methods=["POST"])
def audit_override():
    from smart_buddy.audit import audit_trail

    data = request.form or request.get_json() or {}
    try:
        event_id = int(data.get("event_id", 0))
    except (TypeError, ValueError):
        event_id = 0
    note = (data.get("note") or "").strip()
    actor = (data.get("actor") or "console").strip() or "console"
    if event_id <= 0 or not note:
        resp = {"status": "error", "message": "event_id and note required"}
    else:
        updated = audit_trail.override(event_id, note, actor=actor)
        resp = {"status": "ok" if updated else "not_found"}
    if request.content_type and "application/json" in request.content_type:
        return jsonify(resp)
    if resp.get("status") == "ok":
        return redirect(url_for("audit_console"))
    return jsonify(resp), 400


if __name__ == "__main__":
    print("🚀 Smart Buddy API Server Starting...")
    print("📊 Metrics Dashboard: http://127.0.0.1:8000/metrics")
    print("💬 Chat Endpoint: POST http://127.0.0.1:8000/chat")
    print("📖 Health Check: http://127.0.0.1:8000/health")
    app.run(host="127.0.0.1", port=8000, debug=True)
