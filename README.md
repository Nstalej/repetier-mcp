# repetier-mcp 🖨️

**MCP server for Repetier-Host / Repetier-Server — monitor, control and diagnose your 3D printer with AI.**

Connect Claude (or any MCP-compatible AI) directly to your 3D printer.
Get live temperature readings, job progress, intelligent error diagnosis,
and printer-specific repair guidance — including a built-in knowledge base
for the **Artillery Sidewinder X1**.

> 🇬🇧 English README | [🇪🇸 Español](docs/README_es.md)

---

## ✨ What you can do

| Tell Claude...                                   | What happens                                      |
|--------------------------------------------------|---------------------------------------------------|
| "What's the printer temperature?"               | Returns hotend + bed temps in real time           |
| "My printer has layer shifting problems"         | Diagnoses causes, gives step-by-step repair guide |
| "Send M503 to read current settings"             | Sends G-code, returns EEPROM values               |
| "Check if temps are stable"                      | Takes 5 readings over 10s, detects instability    |
| "What port is my printer on?"                    | Scans serial ports and auto-detects printer       |

---

## 🚀 Quick start

### 1. Install repetier-mcp

```bash
pip install repetier-mcp
# or with uv:
uv tool install repetier-mcp
```

### 2. Connect your printer via USB

Plug in your printer and find the port:

```bash
# Linux / macOS
ls /dev/ttyUSB* /dev/ttyACM* /dev/cu.usbserial*

# Windows  →  Device Manager → Ports (COM & LPT)
```

> **Sidewinder X1 tip:** Use baud rate **250000**, not 115200.

### 3. Add to Claude Desktop

```json
{
  "mcpServers": {
    "repetier": {
      "command": "uvx",
      "args": ["repetier-mcp"],
      "env": {
        "REPETIER_MODE":  "serial",
        "REPETIER_PORT":  "/dev/ttyUSB0",
        "REPETIER_BAUD":  "250000",
        "PRINTER_MODEL":  "sidewinder_x1"
      }
    }
  }
}
```

Restart Claude Desktop. 🎉

---

## 🛠️ Available tools

| Tool                     | Description                                                   |
|--------------------------|---------------------------------------------------------------|
| `printer_status`         | Get temperatures, job progress and position                   |
| `send_gcode`             | Send any G-code / M-code command                             |
| `temperature_check`      | Multi-sample temperature stability analysis                   |
| `list_jobs`              | List print queue (Repetier-Server mode)                      |
| `diagnose_error`         | AI-powered error diagnosis with repair steps                 |
| `knowledge_base_summary` | Show all known error types and their symptoms                |
| `list_serial_ports`      | Scan and auto-detect printer port                            |
| `emergency_stop`         | Send M112 emergency stop                                     |

---

## ⚙️ Configuration

### Direct USB / serial (Repetier-Host)

| Variable          | Default        | Description                                      |
|-------------------|----------------|--------------------------------------------------|
| `REPETIER_MODE`   | `serial`       | Connection mode: `serial` or `server`            |
| `REPETIER_PORT`   | *(auto)*       | Serial port, e.g. `/dev/ttyUSB0` or `COM3`      |
| `REPETIER_BAUD`   | `115200`       | Baud rate — **use `250000` for Sidewinder X1**   |
| `PRINTER_MODEL`   | `sidewinder_x1`| Printer model for targeted diagnostics           |

### Repetier-Server (network)

| Variable              | Default     | Description                        |
|-----------------------|-------------|------------------------------------|
| `REPETIER_MODE`       | `server`    | Set to `server`                    |
| `REPETIER_HOST`       | `localhost` | Repetier-Server hostname/IP        |
| `REPETIER_HTTP_PORT`  | `3344`      | Repetier-Server port               |
| `REPETIER_API_KEY`    | *(empty)*   | API key (if authentication enabled)|
| `REPETIER_PRINTER`    | *(empty)*   | Printer slug/name in server        |

---

## 🔍 Diagnostic knowledge base

Built-in error database for the Artillery Sidewinder X1:

| Error type            | Key symptoms                                     |
|-----------------------|--------------------------------------------------|
| `thermal_runaway`     | THERMAL RUNAWAY, Heating failed, temp sensor     |
| `layer_shifting`      | Layer shift, skipped steps, position lost        |
| `z_offset_drift`      | First layer issues, bed leveling problems        |
| `extruder_clicking`   | Clicking, grinding, under extrusion              |
| `communication_error` | Printer offline, no response, timeout            |
| `bed_adhesion`        | Warping, not sticking, lifting corners           |

Ask Claude: *"My printer is making a clicking noise from the extruder"*
→ `diagnose_error("extruder clicking")` → full root cause analysis + repair steps.

---

## 📦 Part of the maker-mcp ecosystem

This server pairs with **[openscad-mcp](https://github.com/Nstalej/openscad-mcp)**
for a complete design → print workflow:

```
Claude  →  openscad-mcp  →  design .scad → export .stl
                                               ↓
        →  repetier-mcp  →  send to printer → monitor → diagnose
```

---

## 🗺️ Roadmap

- [ ] OctoPrint compatibility layer
- [ ] Klipper / Moonraker support
- [ ] Webcam snapshot integration
- [ ] Print time prediction analysis
- [ ] Filament usage tracking
- [ ] Sidewinder X1 EEPROM tuning wizard

---

## 🤝 Contributing

Issues and PRs are welcome. Especially:
- Additional printer models for the diagnostic KB
- Klipper / Moonraker adapter

```bash
git clone https://github.com/Nstalej/repetier-mcp
cd repetier-mcp
pip install -e ".[dev]"
pytest
```

---

## 📄 License

MIT © 2025 — See [LICENSE](LICENSE)
