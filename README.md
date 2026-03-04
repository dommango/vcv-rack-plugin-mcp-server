# vcv-rack-mcp-server — VCV Rack 2 × AI/MCP

> Connect Claude (or any MCP client) to VCV Rack 2. Build patches, add modules,
> connect cables and tweak parameters — all through natural language.

```
Claude ↔ MCP Server (Python) ↔ HTTP ↔ vcv-rack-mcp-server plugin (C++) ↔ Rack Engine
```

---

## Installation (end users)

### From VCV Library *(once published)*
1. Open VCV Rack → Library menu → Log in
2. Find **vcv-rack-mcp-server** → click Subscribe
3. Restart Rack — the module appears in the browser under **Utility**

### From GitHub Releases (manual)
1. Go to [Releases](https://github.com/YOUR_USERNAME/vcv-rack-mcp-server/releases)
2. Download the `.vcvplugin` for your OS (Windows / Mac / Linux)
3. Double-click it — Rack installs it automatically

---

## Quick start

1. Add the **MCP Bridge** module to any patch
2. Set the **port** knob (default: **2600**)
3. Click the **Enable** button — the LED turns green
4. Run the MCP server:
   ```bash
   pip install mcp httpx
   python vcv_rack_mcp_server.py
   ```
5. Add to your Claude Desktop config (`claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "vcvrack": {
         "command": "python",
         "args": ["/absolute/path/to/vcv_rack_mcp_server.py"]
       }
     }
   }
   ```
6. Ask Claude: *"Build me a basic subtractive synth: VCO → VCF → VCA with an ADSR envelope."*

---

## Building from source

### Prerequisites
- **Rack SDK 2.x** — [download here](https://vcvrack.com/downloads)
- C++17 compiler (GCC 9+, Clang 10+, MSVC 2019+)
- `curl` or `wget` (for dependency download)

### Option A — Makefile (VCV Library standard)

```bash
export RACK_DIR=/path/to/Rack-SDK-2.x.x

make dep     # downloads cpp-httplib automatically (once)
make         # builds plugin .so / .dylib / .dll
make install # installs to your Rack plugins folder
make dist    # creates vcv-rack-mcp-server-VERSION-PLATFORM.vcvplugin
```

### Option B — CMake (IDE-friendly, auto-downloads everything)

```bash
cmake -B build -DRACK_DIR=/path/to/Rack-SDK-2.x.x
cmake --build build
cmake --install build
```

CMake uses `FetchContent` to download `cpp-httplib` automatically — no manual steps.

### Tip: find your Rack SDK path

| OS | Default location |
|---|---|
| Linux | `~/Rack-SDK` (wherever you unzipped it) |
| macOS | `~/Rack-SDK` |
| Windows | `C:\Users\YOU\Rack-SDK` |

---

## HTTP API Reference

All responses: `{ "status": "ok", "data": ... }` or `{ "status": "error", "message": "..." }`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/status` | Server alive, sample rate, module count |
| GET | `/modules` | List all modules in patch |
| GET | `/modules/:id` | Full detail: params + ports |
| POST | `/modules/add` | Add a module `{plugin, slug, x?, y?}` |
| DELETE | `/modules/:id` | Remove a module |
| GET | `/modules/:id/params` | Get all param values |
| POST | `/modules/:id/params` | Set params `{params:[{id,value}]}` |
| GET | `/cables` | List all cables |
| POST | `/cables` | Connect ports |
| DELETE | `/cables/:id` | Disconnect a cable |
| GET | `/library` | All installed plugins + modules |
| GET | `/library?q=oscillator` | Free-text module search |
| GET | `/library?tags=VCO,Filter` | Tag-filtered search |
| GET | `/library/:plugin` | All modules in one plugin |
| POST | `/patch/save` | Save patch `{path}` |
| POST | `/patch/load` | Load patch `{path}` |

---

## MCP Tools (AI-facing)

| Tool | Purpose |
|---|---|
| `rack_status` | Check Rack is reachable |
| `rack_list_modules` | See what's in the patch |
| `rack_get_module` | Inspect params & ports |
| `rack_library_search` | **Find modules by name/tags** |
| `rack_library_plugin` | Browse a plugin's catalogue |
| `rack_add_module` | Add a module |
| `rack_remove_module` | Remove a module |
| `rack_set_params` | Turn knobs |
| `rack_list_cables` | See all connections |
| `rack_connect` | Patch a cable |
| `rack_disconnect` | Remove a cable |
| `rack_save_patch` | Save to disk |
| `rack_load_patch` | Load from disk |

---

## CI / Releasing

GitHub Actions (`.github/workflows/build-plugin.yml`) automatically:

- Builds for **Windows x64**, **Linux x64**, **macOS x64**, **macOS ARM64** on every push
- Creates a **GitHub Release** with all four `.vcvplugin` packages when you push a version tag:

```bash
git tag v2.0.0
git push origin v2.0.0
```

The tag version must match `plugin.json` → `"version"`.

---

## VCV Library submission

1. Fork [VCVRack/community](https://github.com/VCVRack/community)
2. Add your entry to `plugins.json`
3. Open a PR — VCV will build and publish the plugin automatically on merge

See the [VCV Library guide](https://vcvrack.com/manual/PluginDevelopmentTutorial#releasing-your-plugin) for full details.

---

## License

MIT — see [LICENSE](LICENSE).  
Uses [cpp-httplib](https://github.com/yhirose/cpp-httplib) (MIT).
