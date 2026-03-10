# VCV Rack — AI Patch Builder

Control VCV Rack 2 programmatically using `skills/vcvrack_client.py`.

```text
python skills/vcvrack_client.py [--port PORT] <command> [args...]
```

Default port: **2600**. Pass `--port XXXX` if the user configured a different one.

## Before You Start

Check the server is reachable:

```bash
python skills/vcvrack_client.py status
```

Expected response:

```json
{
  "ok": true,
  "data": {
    "server": "VCV Rack MCP Bridge",
    "version": "1.0.0",
    "sampleRate": 44100.0,
    "moduleCount": 3
  }
}
```

If this fails, ask the user to:

1. Open VCV Rack 2
2. Add the **MCP Server** module (search "MCP Server" in the module browser)
3. Click **ON/OFF** until the green STATUS LED lights up

Two operating constraints are easy to miss:

1. Rack changes are applied on Rack's UI thread, so if Rack is blocked by a modal, menu, file picker, or otherwise not updating normally, tool calls may time out.
2. Parameter values are module-defined raw values. Do not assume a control expects literal Hz, seconds, or waveform names until `params` shows that clearly.

---

## Concepts: Signal Chains & Wiring

In VCV Rack, **modules do nothing on their own**. You must connect them with **virtual cables** to form a **signal chain**.

1.  **Source:** A module that generates a signal (e.g., `VCO` for sound, `LFO` for modulation).
2.  **Processor:** A module that modifies a signal (e.g., `VCF` for filtering, `VCA` for volume).
3.  **Sink:** A module that consumes a signal or sends it to the real world (e.g., `Audio Interface`).

### Audio Interface Configuration (IMPORTANT)

**The MCP Server cannot automatically configure the "Audio Interface" module's driver or device.**

- **Agent Responsibility:** Automatically add the `AudioInterface2` module (from the `Core` plugin) and connect the final output of your signal chain to its inputs (usually 0 for L and 1 for R).
- **User Responsibility:** Once the module is added, the user **MUST** manually click the module in VCV Rack to select their preferred **Audio Driver** (e.g., Core Audio, ASIO, JACK) and **Device** (e.g., Built-in Output, Focusrite USB).
- **Check for existing:** Before adding a new audio module, use `modules` to see if one is already present. If so, use its `id` instead of adding a new one.

**Other modules (VCO, VCF, VCA, etc.) should be managed totally automatically by the agent.**

---

## Command Reference

### status — Server health check
... (rest of status) ...

### layout — Rack spatial map (**call this before every `add`**)

```bash
python skills/vcvrack_client.py layout
```

### mcp-position — MCP Server root anchor

```bash
python skills/vcvrack_client.py mcp-position
```

Use this when you only need the MCP Server module's root `x/y` position. It returns the same anchor used by `layout` as `mcp_module`, but without the rest of the rack geometry.

Response:

```json
{
  "ok": true,
  "data": {
    "grid_unit_px": 15,
    "row_height_px": 380,
    "mcp_module": { "x": 30315, "y": 38000 },
    "rows": [
      { "row": 100, "y": 38000, "left_edge": 30315, "right_edge": 30405, "module_count": 1 }
    ],
    "suggested_positions": [
      { "label": "append_row_100", "description": "Append to row 100 (y=38000, 1 modules)", "x": 30405, "y": 38000 },
      { "label": "append_mcp_row", "description": "Append directly to the row containing the MCP module", "x": 30405, "y": 38000 },
      { "label": "insert_before_output", "description": "Insert before the terminal output module on the MCP row so Audio stays at the far right", "x": 31200, "y": 38000 },
      { "label": "new_row",        "description": "Start a fresh row below all existing modules, horizontally aligned with the MCP module", "x": 30315, "y": 38380 }
    ]
  }
}
```

**Coordinate system:**
- `x` and `y` are in VCV Rack pixel units. Pass them directly to `add`.
- One **HP** (the standard module width unit) = **15 px**.
- One **row** = **380 px** tall. Rows stack vertically: row 0 at y=0, row 1 at y=380, etc.
- `mcp_module` is the layout anchor. Treat its `x/y` as the reference point for the patch section controlled by the MCP server.
- `right_edge` of a row is the x coordinate of the first free slot in that row.

**Placement rules (follow strictly):**
1. **Always call `layout` first.** Never add a module without knowing the current rack geometry.
2. **Always pass explicit `x y`** to `add`. Never rely on auto-placement.
3. If the new module belongs near the MCP Server, prefer `append_mcp_row`. This is the safest default for building one contiguous patch near the root MCP module.
4. If the row already ends with an audio output module and you are extending the signal chain, prefer `insert_before_output` so `Audio 2` stays at the far right.
5. To extend a different existing row, pick the matching `append_row_N`.
6. To start a logically separate section, use `new_row`, which begins directly below the current patch and keeps the same horizontal anchor as `mcp_module.x`.
7. Modules are snapped to the HP grid (15 px). The server handles snapping automatically, so passing `right_edge` directly is always safe.

### add — Add a module to the patch

```bash
# ALWAYS provide x y (obtained from `layout`)
python skills/vcvrack_client.py add <plugin_slug> <module_slug> <x> <y>
```

Response:

```json
{ "ok": true, "data": { "id": 42, "plugin": "VCV", "slug": "VCO-1", "x": 1220, "y": 0, "width": 120 } }
```

> **Save the returned `id`** — you need it for params and cables.
> **Save the returned `width`** — add it to the module's `x` to get the `x` for the next module in the same row.

... (rest of commands) ...

### connect — Connect two ports (Create a Cable)

```bash
python skills/vcvrack_client.py connect <out_mod_id> <out_port_id> <in_mod_id> <in_port_id>
```

Response:

```json
{ "ok": true, "data": { "id": 7 } }
```

> **CRITICAL:** Use `module <id>` to find the correct `outputs` (source) and `inputs` (destination) IDs. Wires are the "glue" that makes the patch work.

... (rest of file) ...

---

## Standard Workflow: The "Patch Building" Loop

Building a patch is an iterative process of adding, configuring, and **wiring**:

```
status → library → layout → add (x y) → module → connect → set-param → save
```

1.  **`status`** — Confirm server is alive.
2.  **`library`** — Find exact plugin + module slugs.
3.  **`layout`** — **Always call this before adding any module.** Read `suggested_positions` to pick the right `x y` for each `add`. After adding a module, use its returned `width` to compute the next free x in the same row (`next_x = x + width`), so you can batch-add several modules without calling `layout` again after each one.
4.  **`add <plugin> <slug> <x> <y>`** — Place the module at the coordinates from step 3. Never omit `x y`.
5.  **`module <id>`** — **Discovery Phase.** List the available inputs, outputs, and parameters.
6.  **`connect`** — **Wiring Phase.** Link an `output` of one module to the `input` of another. (e.g., VCO Sine Out -> Audio In).
7.  **`set-param`** — **Tuning Phase.** Adjust knobs using the raw ranges returned by `params`. Prefer one or two changes at a time, then re-read the params to verify the result.
8.  **`save`** — Persist your creation.

## Parameter Safety Rules

- Always run `params <id>` immediately before `set-param`.
- Use `displayValue` and `options` when present; they are better guides than guessing from the parameter name.
- Keep writes inside the reported `min` and `max`.
- If a write fails or times out, reduce the batch size and verify Rack is still responsive before retrying.


---

## Examples

See the `skills/examples/` folder for ready-to-run walkthroughs:

| File | Patch |
|------|-------|
| `examples/01_vco_to_audio.md` | VCO → Audio out (minimal test tone) |
| `examples/02_vco_vcf_vca.md` | VCO → VCF → VCA → Audio (classic subtractive voice) |
| `examples/03_lfo_modulation.md` | LFO modulating VCF cutoff |
