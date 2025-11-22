"""Tool abstraction with guardrails and registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from smart_buddy.logging import get_logger
from smart_buddy.audit import audit_trail


@dataclass
class ToolRequest:
    """Request to invoke a tool."""
    name: str
    arguments: Dict[str, Any]
    user_id: str
    session_id: str
    trace_id: str


@dataclass
class ToolResult:
    """Result from tool invocation."""
    name: str
    success: bool
    output: Any
    diagnostics: Dict[str, Any] = field(default_factory=dict)


class Tool:
    name: str = "tool"
    description: str = ""
    guardrails: Dict[str, Any] = {}

    def __init__(self) -> None:
        self._logger = get_logger(f"smart_buddy.tools.{self.name}")

    def is_allowed(self, request: ToolRequest) -> bool:
        max_args = self.guardrails.get("max_args", 10)
        return len(request.arguments) <= max_args

    def invoke(self, request: ToolRequest) -> ToolResult:  # pragma: no cover - abstract
        raise NotImplementedError


class ToolRegistry:
    """Registers tools and enforces guardrails per invocation."""

    def __init__(self, tools: Optional[List[Tool]] = None) -> None:
        self._logger = get_logger("smart_buddy.tools.registry")
        self._tools: Dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        self._logger.info("tool_registered", extra={"tool": tool.name})

    def call(
        self,
        name: str,
        *,
        user_id: str,
        session_id: str,
        trace_id: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        request = ToolRequest(
            name=name,
            arguments=arguments or {},
            user_id=user_id,
            session_id=session_id,
            trace_id=trace_id,
        )
        if not tool.is_allowed(request):
            self._logger.warning(
                "tool_blocked_guardrail",
                extra={"tool": name, "trace_id": trace_id},
            )
            audit_trail.record(
                "tool_call",
                trace_id=trace_id,
                severity="warn",
                payload={
                    "tool": name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "arguments": request.arguments,
                    "result": "guardrail_violation",
                },
            )
            return ToolResult(
                name=name,
                success=False,
                output={},
                diagnostics={"error": "guardrail_violation"},
            )
        try:
            result = tool.invoke(request)
            self._logger.info(
                "tool_invoked",
                extra={
                    "tool": name,
                    "trace_id": trace_id,
                    "success": result.success,
                },
            )
            audit_trail.record(
                "tool_call",
                trace_id=trace_id,
                severity="info" if result.success else "warn",
                payload={
                    "tool": name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "arguments": request.arguments,
                    "success": result.success,
                    "diagnostics": result.diagnostics,
                },
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.exception(
                "tool_exception", extra={"tool": name, "trace_id": trace_id}
            )
            audit_trail.record(
                "tool_call",
                trace_id=trace_id,
                severity="error",
                payload={
                    "tool": name,
                    "user_id": user_id,
                    "session_id": session_id,
                    "arguments": request.arguments,
                    "success": False,
                    "diagnostics": {"error": str(exc)},
                },
            )
            return ToolResult(
                name=name,
                success=False,
                output={},
                diagnostics={"error": str(exc)},
            )


# ---------------------------------------------------------------------------
# Default tool bundle
# ---------------------------------------------------------------------------
from . import calendar, docs, web  # noqa: E402  pylint: disable=wrong-import-position

try:
    from . import mcp_filesystem  # noqa: E402  pylint: disable=wrong-import-position
    MCP_FILESYSTEM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional MCP dependency
    mcp_filesystem = None  # type: ignore[assignment]
    MCP_FILESYSTEM_AVAILABLE = False

try:
    from . import mcp_memory  # noqa: E402  pylint: disable=wrong-import-position
    MCP_MEMORY_AVAILABLE = True
except ImportError:  # pragma: no cover - optional MCP dependency
    mcp_memory = None  # type: ignore[assignment]
    MCP_MEMORY_AVAILABLE = False

try:
    from . import mcp_time  # noqa: E402  pylint: disable=wrong-import-position
    MCP_TIME_AVAILABLE = True
except ImportError:  # pragma: no cover - optional MCP dependency
    mcp_time = None  # type: ignore[assignment]
    MCP_TIME_AVAILABLE = False


def build_default_registry(memory=None, docs_root: str | Path = "docs") -> ToolRegistry:
    tools_list = [
        calendar.CalendarTool(memory=memory),
        docs.DocumentLookupTool(docs_root=docs_root),
        web.CuratedWebSearchTool(),
    ]
    
    # Add MCP filesystem tool if available
    if MCP_FILESYSTEM_AVAILABLE and mcp_filesystem is not None:
        tools_list.append(mcp_filesystem.MCPFilesystemTool(workspace_root=Path(docs_root).parent))
    
    # Add MCP memory tool if available
    if MCP_MEMORY_AVAILABLE and mcp_memory is not None:
        tools_list.append(mcp_memory.MCPMemoryTool())
    
    # Add MCP time tool if available
    if MCP_TIME_AVAILABLE and mcp_time is not None:
        tools_list.append(mcp_time.MCPTimeTool())
    
    registry = ToolRegistry(tools=tools_list)
    return registry
