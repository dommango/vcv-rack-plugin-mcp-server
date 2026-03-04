#!/usr/bin/env python3
"""
vcv_rack_mcp_server.py
MCP Server — VCV Rack 2 Bridge

Exposes VCV Rack internals as MCP tools so any MCP client (Claude, Cursor,
etc.) can build and manipulate patches programmatically.

The VCV Rack plugin (RackMcpServer.cpp) must be running inside Rack with the
HTTP server enabled. Default: http://127.0.0.1:2600

Install dependencies:
    pip install mcp httpx

Run:
    python vcv_rack_mcp_server.py
    # or with a custom port:
    RACK_PORT=2601 python vcv_rack_mcp_server.py

MCP client config (Claude Desktop, claude_desktop_config.json):
{
  "mcpServers": {
    "vcvrack": {
      "command": "python",
      "args": ["/path/to/vcv_rack_mcp_server.py"]
    }
  }
}
"""

import os
import sys
import json
import httpx
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Config ─────────────────────────────────────────────────────────────────
RACK_PORT = int(os.environ.get("RACK_PORT", 2600))
RACK_BASE = f"http://127.0.0.1:{RACK_PORT}"
TIMEOUT   = 10.0  # seconds

server = Server("vcv-rack-mcp-server")
client = httpx.AsyncClient(base_url=RACK_BASE, timeout=TIMEOUT)

# ── Helper ──────────────────────────────────────────────────────────────────

async def rack(method: str, path: str, body: dict | None = None) -> dict:
    """Call the VCV Rack HTTP bridge and return parsed JSON data."""
    try:
        if method == "GET":
            r = await client.get(path)
        elif method == "POST":
            r = await client.post(path, json=body)
        elif method == "DELETE":
            r = await client.delete(path)
        else:
            raise ValueError(f"Unknown method: {method}")
        r.raise_for_status()
        result = r.json()
        if result.get("status") == "error":
            raise RuntimeError(result.get("message", "Unknown error from Rack"))
        return result.get("data", result)
    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to VCV Rack on port {RACK_PORT}. "
            "Make sure the Rack MCP Server module is in your patch and its server is enabled."
        )

def text(s: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=s)]

def jtext(obj) -> list[types.TextContent]:
    return text(json.dumps(obj, indent=2))

# ── Tool definitions ────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [

        types.Tool(
            name="rack_status",
            description=(
                "Check if VCV Rack is reachable and get basic patch info "
                "(sample rate, number of modules currently in the patch)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),

        types.Tool(
            name="rack_list_modules",
            description=(
                "List all modules currently placed in the VCV Rack patch. "
                "Returns each module's ID, plugin slug, module slug, name, "
                "and port counts. Use the returned IDs with other tools."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),

        types.Tool(
            name="rack_get_module",
            description=(
                "Get full detail for a single module: all parameters with "
                "names, min/max/current values, and all input/output port names."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_id": {
                        "type": "integer",
                        "description": "The numeric module ID from rack_list_modules"
                    }
                },
                "required": ["module_id"]
            },
        ),

        types.Tool(
            name="rack_library_search",
            description=(
                "Search the VCV Rack module library (all installed plugins) to find "
                "modules suitable for the user's goal. Pass a free-text query and/or "
                "tag filters. Returns plugin/module slugs needed for rack_add_module.\n\n"
                "Common tags: VCO, VCF, VCA, LFO, Envelope, Sequencer, Utility, "
                "Mixer, Reverb, Delay, Distortion, Quantizer, Sampler, MIDI, Clock."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text search (name, description). E.g. 'oscillator', 'wavefolder', 'clock divider'."
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tag filter. E.g. 'VCO' or 'Sequencer,Clock'."
                    }
                }
            },
        ),

        types.Tool(
            name="rack_library_plugin",
            description=(
                "Get all modules available in a specific installed plugin. "
                "Useful after rack_library_search to explore a plugin's full catalogue."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "plugin_slug": {
                        "type": "string",
                        "description": "Plugin slug, e.g. 'VCV', 'Fundamental', 'Befaco'."
                    }
                },
                "required": ["plugin_slug"]
            },
        ),

        types.Tool(
            name="rack_add_module",
            description=(
                "Add a module to the VCV Rack patch. Use rack_library_search first "
                "to find the correct plugin_slug and module_slug. "
                "Returns the new module's ID for use with other tools."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "plugin_slug": {
                        "type": "string",
                        "description": "Plugin slug, e.g. 'VCV' or 'Fundamental'."
                    },
                    "module_slug": {
                        "type": "string",
                        "description": "Module slug, e.g. 'VCO', 'VCF', 'ADSR'."
                    },
                    "x": {
                        "type": "integer",
                        "description": "Horizontal position in rack pixels (optional, default 0).",
                        "default": 0
                    },
                    "y": {
                        "type": "integer",
                        "description": "Vertical position in rack pixels (optional, default 0).",
                        "default": 0
                    }
                },
                "required": ["plugin_slug", "module_slug"]
            },
        ),

        types.Tool(
            name="rack_remove_module",
            description="Remove a module from the patch by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "module_id": {"type": "integer", "description": "Module ID to remove."}
                },
                "required": ["module_id"]
            },
        ),

        types.Tool(
            name="rack_set_params",
            description=(
                "Set one or more parameter values on a module. "
                "Use rack_get_module to discover parameter IDs, names, and valid ranges."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_id": {
                        "type": "integer",
                        "description": "Target module ID."
                    },
                    "params": {
                        "type": "array",
                        "description": "List of {id, value} objects.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id":    {"type": "integer", "description": "Parameter index."},
                                "value": {"type": "number",  "description": "New value (must be within min/max)."}
                            },
                            "required": ["id", "value"]
                        }
                    }
                },
                "required": ["module_id", "params"]
            },
        ),

        types.Tool(
            name="rack_list_cables",
            description="List all cables (patch connections) currently in the patch.",
            inputSchema={"type": "object", "properties": {}},
        ),

        types.Tool(
            name="rack_connect",
            description=(
                "Connect an output port of one module to an input port of another. "
                "Use rack_get_module to discover port IDs and names. "
                "Returns the new cable's ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "output_module_id": {"type": "integer", "description": "Module with the output port."},
                    "output_id":        {"type": "integer", "description": "Output port index (0-based)."},
                    "input_module_id":  {"type": "integer", "description": "Module with the input port."},
                    "input_id":         {"type": "integer", "description": "Input port index (0-based)."}
                },
                "required": ["output_module_id", "output_id", "input_module_id", "input_id"]
            },
        ),

        types.Tool(
            name="rack_disconnect",
            description="Remove a cable by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cable_id": {"type": "integer", "description": "Cable ID from rack_list_cables."}
                },
                "required": ["cable_id"]
            },
        ),

        types.Tool(
            name="rack_save_patch",
            description="Save the current patch to disk.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path, e.g. '/home/user/my_patch.vcv'."}
                },
                "required": ["path"]
            },
        ),

        types.Tool(
            name="rack_load_patch",
            description="Load a patch from disk, replacing the current patch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute file path to a .vcv patch file."}
                },
                "required": ["path"]
            },
        ),
    ]

# ── Tool handlers ────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        match name:

            case "rack_status":
                data = await rack("GET", "/status")
                return jtext(data)

            case "rack_list_modules":
                data = await rack("GET", "/modules")
                return jtext(data)

            case "rack_get_module":
                mid = arguments["module_id"]
                data = await rack("GET", f"/modules/{mid}")
                return jtext(data)

            case "rack_library_search":
                params = {}
                if q := arguments.get("query"):  params["q"] = q
                if t := arguments.get("tags"):   params["tags"] = t
                qs = "&".join(f"{k}={v}" for k, v in params.items())
                path = f"/library?{qs}" if qs else "/library"
                data = await rack("GET", path)
                return jtext(data)

            case "rack_library_plugin":
                slug = arguments["plugin_slug"]
                data = await rack("GET", f"/library/{slug}")
                return jtext(data)

            case "rack_add_module":
                body = {
                    "plugin": arguments["plugin_slug"],
                    "slug":   arguments["module_slug"],
                    "x":      arguments.get("x", 0),
                    "y":      arguments.get("y", 0),
                }
                data = await rack("POST", "/modules/add", body)
                return jtext(data)

            case "rack_remove_module":
                data = await rack("DELETE", f"/modules/{arguments['module_id']}")
                return jtext(data)

            case "rack_set_params":
                mid    = arguments["module_id"]
                params = arguments["params"]
                data = await rack("POST", f"/modules/{mid}/params", {"params": params})
                return jtext(data)

            case "rack_list_cables":
                data = await rack("GET", "/cables")
                return jtext(data)

            case "rack_connect":
                body = {
                    "outputModuleId": arguments["output_module_id"],
                    "outputId":       arguments["output_id"],
                    "inputModuleId":  arguments["input_module_id"],
                    "inputId":        arguments["input_id"],
                }
                data = await rack("POST", "/cables", body)
                return jtext(data)

            case "rack_disconnect":
                data = await rack("DELETE", f"/cables/{arguments['cable_id']}")
                return jtext(data)

            case "rack_save_patch":
                data = await rack("POST", "/patch/save", {"path": arguments["path"]})
                return jtext(data)

            case "rack_load_patch":
                data = await rack("POST", "/patch/load", {"path": arguments["path"]})
                return jtext(data)

            case _:
                return text(f"Unknown tool: {name}")

    except Exception as e:
        return text(f"Error: {e}")


# ── Entry point ──────────────────────────────────────────────────────────────

async def main():
    print(f"VCV Rack MCP Server (vcv-rack-mcp-server) starting (Rack on port {RACK_PORT})", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
