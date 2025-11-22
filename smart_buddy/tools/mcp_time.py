"""MCP Time Server Integration for Smart Buddy.

Provides time, date, timezone utilities via Model Context Protocol.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

from .base import Tool, ToolRequest, ToolResult

try:
    import pytz  # type: ignore[import-not-found]
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    pytz = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class MCPTimeTool(Tool):
    """Time and date operations via MCP protocol."""
    
    name = "mcp.time"
    description = "Get current time, dates, timezones, and time calculations"
    guardrails = {"max_args": 7}
    
    def __init__(self) -> None:
        super().__init__()
        if not PYTZ_AVAILABLE:
            self._logger.warning("pytz_not_installed", extra={"tool": self.name})
    
    def invoke(self, request: ToolRequest) -> ToolResult:
        """Execute time operation via ToolRequest."""
        action = request.arguments.get("action", "now")
        timezone = request.arguments.get("timezone", "UTC")
        from_timezone = request.arguments.get("from_timezone")
        to_timezone = request.arguments.get("to_timezone")
        time_str = request.arguments.get("time_str")
        amount = int(request.arguments.get("amount", 0))
        unit = request.arguments.get("unit", "hours")
        format_str = request.arguments.get("format", "%Y-%m-%d %H:%M:%S")
        
        try:
            output = self.execute(action, timezone, from_timezone, to_timezone,
                                time_str, amount, unit, format_str)
            return ToolResult(
                name=self.name,
                success=output.get("success", False),
                output=output,
                diagnostics={}
            )
        except Exception as e:
            return ToolResult(
                name=self.name,
                success=False,
                output={},
                diagnostics={"error": str(e)}
            )
    
    def execute(self, action: str, timezone: str = "UTC", 
                from_timezone: Optional[str] = None, to_timezone: Optional[str] = None,
                time_str: Optional[str] = None, amount: int = 0, unit: str = "hours",
                format: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
        """Execute time operation.
        
        Args:
            action: Operation type
            timezone: Target timezone
            from_timezone: Source timezone for conversion
            to_timezone: Target timezone for conversion
            time_str: Time string to parse
            amount: Amount to add/subtract
            unit: Time unit
            format: Output format
            
        Returns:
            Operation result
        """
        if not PYTZ_AVAILABLE:
            return {
                "success": False,
                "error": "pytz not installed. Run: pip install pytz"
            }
        
        try:
            if action == "now":
                return self._get_current_time(timezone, format)
            elif action == "timezone":
                return self._get_timezone_info(timezone)
            elif action == "convert":
                if not time_str or not from_timezone or not to_timezone:
                    return {"success": False, "error": "time_str, from_timezone, and to_timezone required"}
                return self._convert_timezone(time_str, from_timezone, to_timezone, format)
            elif action == "add":
                if not time_str:
                    return {"success": False, "error": "time_str required for add"}
                return self._add_time(time_str, amount, unit, timezone, format)
            elif action == "subtract":
                if not time_str:
                    return {"success": False, "error": "time_str required for subtract"}
                return self._subtract_time(time_str, amount, unit, timezone, format)
            elif action == "format":
                if not time_str:
                    return {"success": False, "error": "time_str required for format"}
                return self._format_time(time_str, format, timezone)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"MCP time error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_current_time(self, timezone: str, format: str) -> Dict[str, Any]:
        """Get current time in specified timezone."""
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return {
                "success": True,
                "time": now.strftime(format),
                "timezone": timezone,
                "iso": now.isoformat(),
                "unix": int(now.timestamp())
            }
        except Exception as e:
            # Fallback to UTC
            now = datetime.now(pytz.UTC)
            return {
                "success": True,
                "time": now.strftime(format),
                "timezone": "UTC",
                "iso": now.isoformat(),
                "unix": int(now.timestamp()),
                "warning": f"Invalid timezone {timezone}, using UTC"
            }
    
    def _get_timezone_info(self, timezone: str) -> Dict[str, Any]:
        """Get timezone information."""
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            return {
                "success": True,
                "timezone": timezone,
                "offset": now.strftime("%z"),
                "abbreviation": now.strftime("%Z"),
                "current_time": now.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": f"Invalid timezone: {timezone}"}
    
    def _convert_timezone(self, time_str: str, from_tz: str, to_tz: str, format: str) -> Dict[str, Any]:
        """Convert time between timezones."""
        if not time_str or not from_tz or not to_tz:
            return {"success": False, "error": "Time string and timezones required"}
        
        try:
            from_zone = pytz.timezone(from_tz)
            to_zone = pytz.timezone(to_tz)
            
            # Parse time string
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            dt_from = from_zone.localize(dt.replace(tzinfo=None))
            dt_to = dt_from.astimezone(to_zone)
            
            return {
                "success": True,
                "original": dt_from.strftime(format),
                "converted": dt_to.strftime(format),
                "from_timezone": from_tz,
                "to_timezone": to_tz
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_time(self, time_str: str, amount: int, unit: str, timezone: str, format: str) -> Dict[str, Any]:
        """Add time to a datetime."""
        try:
            tz = pytz.timezone(timezone)
            base_time = datetime.now(tz) if not time_str else datetime.fromisoformat(time_str)
            
            delta_map = {
                "seconds": timedelta(seconds=amount),
                "minutes": timedelta(minutes=amount),
                "hours": timedelta(hours=amount),
                "days": timedelta(days=amount),
                "weeks": timedelta(weeks=amount)
            }
            
            new_time = base_time + delta_map.get(unit, timedelta(hours=amount))
            return {
                "success": True,
                "original": base_time.strftime(format),
                "result": new_time.strftime(format),
                "added": f"{amount} {unit}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _subtract_time(self, time_str: str, amount: int, unit: str, timezone: str, format: str) -> Dict[str, Any]:
        """Subtract time from a datetime."""
        return self._add_time(time_str, -amount, unit, timezone, format)
    
    def _format_time(self, time_str: str, format: str, timezone: str) -> Dict[str, Any]:
        """Format a time string."""
        try:
            dt = datetime.fromisoformat(time_str) if time_str else datetime.now(pytz.timezone(timezone))
            return {
                "success": True,
                "formatted": dt.strftime(format),
                "iso": dt.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
