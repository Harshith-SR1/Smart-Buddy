"""Quick test for MCP filesystem tool integration."""
from smart_buddy.tools.base import build_default_registry


def test_mcp_tool_available():
    """Verify MCP filesystem tool registers when mcp package installed."""
    registry = build_default_registry(docs_root="docs")
    
    tool_names = list(registry._tools.keys())
    print(f"✅ Registered tools: {tool_names}")
    
    # Check if MCP tool is available
    if "mcp.filesystem" in tool_names:
        print("✅ MCP filesystem tool successfully registered!")
        mcp_tool = registry._tools["mcp.filesystem"]
        print(f"   Description: {mcp_tool.description}")
        print(f"   Guardrails: {mcp_tool.guardrails}")
    else:
        print("⚠️  MCP filesystem tool not available (mcp package not installed)")
    
    return "mcp.filesystem" in tool_names


def test_mcp_read_file():
    """Test MCP tool can read documentation files."""
    from smart_buddy.tools.mcp_filesystem import MCPFilesystemTool
    from smart_buddy.tools.base import ToolRequest
    
    tool = MCPFilesystemTool(workspace_root=".")
    
    # Try reading install.md from docs/
    request = ToolRequest(
        name="mcp.filesystem",
        arguments={"operation": "read_file", "path": "install.md"},
        user_id="test",
        session_id="test_session",
        trace_id="test_trace_001",
    )
    
    result = tool.invoke(request)
    
    if result.success:
        print(f"✅ Read file successfully: {result.output.get('path')}")
        print(f"   Size: {result.output.get('size')} bytes")
        print(f"   Preview: {result.output.get('content', '')[:100]}...")
    else:
        print(f"❌ Read failed: {result.diagnostics}")
    
    return result.success


def test_mcp_list_directory():
    """Test MCP tool can list docs directory."""
    from smart_buddy.tools.mcp_filesystem import MCPFilesystemTool
    from smart_buddy.tools.base import ToolRequest
    
    tool = MCPFilesystemTool(workspace_root=".")
    
    request = ToolRequest(
        name="mcp.filesystem",
        arguments={"operation": "list_directory", "path": "."},
        user_id="test",
        session_id="test_session",
        trace_id="test_trace_002",
    )
    
    result = tool.invoke(request)
    
    if result.success:
        print(f"✅ Listed directory: {result.output.get('path')}")
        entries = result.output.get('entries', [])
        print(f"   Found {len(entries)} items:")
        for entry in entries[:5]:
            print(f"     - {entry['name']} ({entry['type']})")
    else:
        print(f"❌ List failed: {result.diagnostics}")
    
    return result.success


if __name__ == "__main__":
    print("🧪 Testing MCP Filesystem Tool Integration\n")
    print("=" * 60)
    
    print("\n1. Tool Registration Test")
    print("-" * 60)
    test_mcp_tool_available()
    
    print("\n2. Read File Test")
    print("-" * 60)
    test_mcp_read_file()
    
    print("\n3. List Directory Test")
    print("-" * 60)
    test_mcp_list_directory()
    
    print("\n" + "=" * 60)
    print("✅ MCP integration tests complete!")
