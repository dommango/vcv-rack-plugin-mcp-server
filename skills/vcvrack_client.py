#!/usr/bin/env python3
"""
vcvrack_client.py — CLI client for the VCV Rack MCP HTTP Server

Usage:
  python vcvrack_client.py [--port PORT] <command> [args...]

Commands:
  status                              Server status and patch info
  mcp-position                        MCP Server module root position
  sample-rate                         Engine sample rate
  layout                              Rack spatial map — call before every add
  library [plugin_slug]               List installed plugins/modules
  modules                             List modules in current patch
  module <id>                         Detail for one module
  add <plugin_slug> <module_slug> <x> <y>  Add a module at explicit position
  remove <id>                         Remove a module
  params <id>                         Get parameter metadata and current raw values for a module
  set-param <id> <param_id> <value> [<param_id> <value> ...]  Set params (prefer small batches after inspecting params)
  cables                              List all cables
  connect <out_mod_id> <out_port_id> <in_mod_id> <in_port_id>  Connect ports
  disconnect <cable_id>               Remove a cable
  save <path>                         Save current patch
  load <path>                         Load a patch

Notes:
  - Always call `layout` before adding modules. Use the returned `suggested_positions`
    to pick explicit x y coordinates for each `add`. Never rely on auto-placement.
  - Prefer `append_mcp_row` for modules that belong with the main patch section.
    If the row already ends with `Audio 2`/other output modules, prefer
    `insert_before_output` so outputs remain at the far right.
  - When adding several modules in a row, compute the next x as: x + width (returned
    by each `add` response) — no need to call `layout` again between each add.
  - Always run `params <id>` before `set-param` so you can use the module's real
    min/max range, displayValue, and options instead of guessing from the name.
  - Many Rack controls use normalized raw values rather than literal Hz/seconds.
  - If a write times out, confirm Rack is responsive and retry with a smaller batch.
"""

import sys
import json
import argparse
import urllib.request
import urllib.error


def request(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            err = {"error": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot reach server: {e.reason}", file=sys.stderr)
        print("Make sure VCV Rack is running with the MCP Server module ON.", file=sys.stderr)
        sys.exit(1)


def pretty(obj):
    print(json.dumps(obj, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="VCV Rack MCP Server CLI client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--port", type=int, default=2600, help="Server port (default: 2600)")
    parser.add_argument("command", help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    args = parser.parse_args()

    base = f"http://127.0.0.1:{args.port}"
    cmd = args.command
    a = args.args

    # ── Status & info ──────────────────────────────────────────────────────
    if cmd == "status":
        pretty(request("GET", f"{base}/status"))

    elif cmd == "sample-rate":
        pretty(request("GET", f"{base}/sample-rate"))

    elif cmd == "mcp-position":
        pretty(request("GET", f"{base}/mcp-module/position"))

    elif cmd == "layout":
        pretty(request("GET", f"{base}/rack/layout"))

    # ── Library ────────────────────────────────────────────────────────────
    elif cmd == "library":
        if a:
            pretty(request("GET", f"{base}/library/{a[0]}"))
        else:
            pretty(request("GET", f"{base}/library"))

    # ── Modules ────────────────────────────────────────────────────────────
    elif cmd == "modules":
        pretty(request("GET", f"{base}/modules"))

    elif cmd == "module":
        if not a:
            parser.error("module requires <id>")
        pretty(request("GET", f"{base}/modules/{a[0]}"))

    elif cmd == "add":
        if len(a) < 4:
            parser.error(
                "add requires <plugin_slug> <module_slug> <x> <y>\n"
                "  Run `layout` first to get the correct x y coordinates."
            )
        body = {"plugin": a[0], "slug": a[1], "x": float(a[2]), "y": float(a[3])}
        pretty(request("POST", f"{base}/modules/add", body))

    elif cmd == "remove":
        if not a:
            parser.error("remove requires <id>")
        pretty(request("DELETE", f"{base}/modules/{a[0]}"))

    # ── Parameters ─────────────────────────────────────────────────────────
    elif cmd == "params":
        if not a:
            parser.error("params requires <id>")
        pretty(request("GET", f"{base}/modules/{a[0]}/params"))

    elif cmd == "set-param":
        if len(a) < 3 or len(a) % 2 == 0:
            parser.error("set-param requires <id> <param_id> <value> [<param_id> <value> ...]")
        mod_id = a[0]
        pairs = a[1:]
        params = [{"id": int(pairs[i]), "value": float(pairs[i+1])} for i in range(0, len(pairs), 2)]
        pretty(request("POST", f"{base}/modules/{mod_id}/params", {"params": params}))

    # ── Cables ─────────────────────────────────────────────────────────────
    elif cmd == "cables":
        pretty(request("GET", f"{base}/cables"))

    elif cmd == "connect":
        if len(a) < 4:
            parser.error("connect requires <out_mod_id> <out_port_id> <in_mod_id> <in_port_id>")
        body = {
            "outputModuleId": int(a[0]),
            "outputId":       int(a[1]),
            "inputModuleId":  int(a[2]),
            "inputId":        int(a[3]),
        }
        pretty(request("POST", f"{base}/cables", body))

    elif cmd == "disconnect":
        if not a:
            parser.error("disconnect requires <cable_id>")
        pretty(request("DELETE", f"{base}/cables/{a[0]}"))

    # ── Patch ──────────────────────────────────────────────────────────────
    elif cmd == "save":
        if not a:
            parser.error("save requires <path>")
        pretty(request("POST", f"{base}/patch/save", {"path": a[0]}))

    elif cmd == "load":
        if not a:
            parser.error("load requires <path>")
        pretty(request("POST", f"{base}/patch/load", {"path": a[0]}))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
