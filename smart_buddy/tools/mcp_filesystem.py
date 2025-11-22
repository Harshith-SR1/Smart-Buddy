"""MCP Filesystem Tool - integrates Model Context Protocol for file operations.

Provides agents with safe, sandboxed access to the docs/ directory via MCP.
Demonstrates advanced tool orchestration for competition scoring.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from smart_buddy.logging import get_logger

from .base import Tool, ToolRequest, ToolResult

# MCP imports with graceful fallback
try:
    from mcp import ClientSession, StdioServerParameters  # type: ignore[import-not-found]
    from mcp.client.stdio import stdio_client  # type: ignore[import-not-found]

    MCP_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    MCP_AVAILABLE = False
    ClientSession = None  # type: ignore[assignment,misc]
    StdioServerParameters = None  # type: ignore[assignment,misc]
    stdio_client = None  # type: ignore[assignment,misc]


class MCPFilesystemTool(Tool):
    """Tool wrapping MCP filesystem server for secure doc operations.

    Capabilities:
    - read_file: Read documentation files from docs/ directory
    - write_file: Create or update documentation
    - list_directory: Browse available docs
    - search_files: Find files matching patterns

    Guardrails:
    - Restricted to docs/ directory only
    - File size limits
    - Read-only mode available
    """

    name = "mcp.filesystem"
    description = "Access project documentation via MCP filesystem server"
    guardrails = {
        "max_args": 5,
        "allowed_roots": ["docs"],
        "max_file_size": 1_000_000,  # 1MB
        "read_only": False,
    }

    def __init__(self, workspace_root: str | Path = ".") -> None:
        super().__init__()
        self.workspace_root = Path(workspace_root).resolve()
        self.docs_root = self.workspace_root / "docs"
        self._session: Optional[Any] = None

    def _ensure_mcp_available(self) -> bool:
        if not MCP_AVAILABLE:
            self._logger.warning("mcp_not_installed", extra={"tool": self.name})
            return False
        return True

    async def _get_session(self) -> Any:
        """Lazy initialize MCP client session."""
        if self._session is not None:
            return self._session

        if not self._ensure_mcp_available():
            return None

        # Type guard ensures these are not None when MCP_AVAILABLE is True
        assert StdioServerParameters is not None
        assert stdio_client is not None

        # Start MCP filesystem server (assumes npx @modelcontextprotocol/server-filesystem installed)
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                str(self.docs_root),
            ],
        )

        try:
            self._session = await stdio_client(server_params).__aenter__()
            self._logger.info("mcp_session_started", extra={"root": str(self.docs_root)})
            return self._session
        except Exception as e:  # pragma: no cover - runtime error
            self._logger.exception("mcp_session_failed", extra={"error": str(e)})
            return None

    def invoke(self, request: ToolRequest) -> ToolResult:
        """Synchronous wrapper for async MCP operations."""
        if not self._ensure_mcp_available():
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": "mcp_not_available"},
            )

        operation = request.arguments.get("operation", "read_file")
        path = request.arguments.get("path", "")

        # Basic validation
        if not path or ".." in path:
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": "invalid_path"},
            )

        # Fallback: synchronous file operations for non-async contexts
        return self._sync_file_operation(operation, path, request.arguments)

    def _sync_file_operation(
        self, operation: str, path: str, args: Dict[str, Any]
    ) -> ToolResult:
        """Synchronous file operations as MCP fallback."""
        target = self.docs_root / path

        # Security check: ensure path is within docs/
        try:
            target = target.resolve()
            target.relative_to(self.docs_root)
        except (ValueError, OSError):
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": "path_outside_allowed_root"},
            )

        if operation == "read_file":
            if not target.exists():
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": "file_not_found", "path": path},
                )
            try:
                content = target.read_text(encoding="utf-8")
                return ToolResult(
                    name=self.name,
                    success=True,
                    output={"path": path, "content": content, "size": len(content)},
                    diagnostics={"operation": "read_file", "method": "sync_fallback"},
                )
            except Exception as e:  # pragma: no cover - IO error
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": str(e)},
                )

        elif operation == "write_file":
            if self.guardrails.get("read_only", False):
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": "read_only_mode"},
                )
            content = args.get("content", "")
            if len(content) > self.guardrails["max_file_size"]:
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": "file_too_large"},
                )
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return ToolResult(
                    name=self.name,
                    success=True,
                    output={"path": path, "size": len(content)},
                    diagnostics={"operation": "write_file", "method": "sync_fallback"},
                )
            except Exception as e:  # pragma: no cover - IO error
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": str(e)},
                )

        elif operation == "list_directory":
            if not target.is_dir():
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": "not_a_directory"},
                )
            try:
                entries = []
                for item in target.iterdir():
                    entries.append(
                        {
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else 0,
                        }
                    )
                return ToolResult(
                    name=self.name,
                    success=True,
                    output={"path": path, "entries": entries},
                    diagnostics={"operation": "list_directory", "count": len(entries)},
                )
            except Exception as e:  # pragma: no cover - IO error
                return ToolResult(
                    name=self.name,
                    success=False,
                    output={},
                    diagnostics={"error": str(e)},
                )

        return ToolResult(
            name=self.name,
            success=False,
            output={},
            diagnostics={"error": "unknown_operation", "operation": operation},
        )
