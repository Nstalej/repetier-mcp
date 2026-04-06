# repetier-mcp

**MCP server for Repetier-Host / Repetier-Server -- monitor, control and diagnose your 3D printer with AI.**

Connect Claude (or any MCP-compatible AI) directly to your 3D printer.
Get live temperature readings, job progress, intelligent error diagnosis,
and printer-specific repair guidance -- including a built-in knowledge base
for the **Artillery Sidewinder X1**.

> English README | [Espanol](docs/README_es.md)

---

## What you can do

| Tell Claude...                                   | What happens                                      |
|--------------------------------------------------|---------------------------------------------------|
| "What's the printer temperature?"               | Returns hotend + bed temps in real time           |
| "My printer has layer shifting problems"         | Diagnoses causes, gives step-by-step repair guide |
| "Send M503 to read current settings"             | Sends G-code, returns EEPROM values               |
| "Check if temps are stable"                      | Takes 5 readings over 10s, detects instability    |
| "Upload and print benchy.gcode"                  | Uploads file to server and starts printing        |
| "Pause the print"                                | Pauses current job via Repetier-Server            |
| "Set bed temperature to 60"                      | Sets heated bed to 60C                            |
| "What port is my printer on?"                    | Scans serial ports and auto-detects printer       |

---

## Quick start

### Install from GitHub

```bash
pip install git+https://github.com/Nstalej/repetier-mcp.git
```

Or with `uv` (recommended -- faster, no dependency conflicts):

```bash
pip install uv
uv pip install git+https://github.com/Nstalej/repetier-mcp.git
```

For **serial mode** (direct USB), also install pyserial:

```bash
pip install "repetier-mcp[serial] @ git+https://github.com/Nstalej/repetier-mcp.git"
```

For development:

```bash
git clone https://github.com/Nstalej/repetier-mcp.git
cd repetier-mcp
pip install -e ".[dev]"
pytest
```

---

## Connection Modes

repetier-mcp supports two connection modes:

### Mode 1: Repetier-Server (recommended)

Connects via HTTP REST API to Repetier-Server running on your network.
Supports all features including file upload, pause/resume, and job management.

### Mode 2: Direct Serial (USB)

Connects directly to the printer via USB/serial port (pyserial).
Classic mode for Repetier-Host users. Requires the `serial` extra.

---

## Configuration

### Repetier-Server mode

| Variable                 | Default                    | Description                          |
|--------------------------|----------------------------|--------------------------------------|
| `REPETIER_MODE`          | `serial`                   | Set to `server`                      |
| `REPETIER_SERVER_URL`    | `http://localhost:3344`    | Full URL of Repetier-Server          |
| `REPETIER_SERVER_APIKEY`  | *(empty)*                  | API key from Repetier-Server         |
| `REPETIER_PRINTER_SLUG`  | *(empty)*                  | Printer slug/name in server          |
| `PRINTER_MODEL`          | `sidewinder_x1`            | Printer model for diagnostics        |

### Direct USB / serial mode

| Variable          | Default        | Description                                      |
|-------------------|----------------|--------------------------------------------------|
| `REPETIER_MODE`   | `serial`       | Connection mode: `serial` or `server`            |
| `REPETIER_PORT`   | *(auto)*       | Serial port, e.g. `/dev/ttyUSB0` or `COM3`      |
| `REPETIER_BAUD`   | `115200`       | Baud rate -- **use `250000` for Sidewinder X1**  |
| `PRINTER_MODEL`   | `sidewinder_x1`| Printer model for targeted diagnostics           |

> **Auto-detection:** If `REPETIER_SERVER_URL` is set and `REPETIER_MODE` is not,
> the server mode is auto-selected.

---

## Claude Desktop Setup

### Windows

#### Step 1 -- Find your printer's COM port (serial mode only)

1. Connect the printer via USB
2. Open **Device Manager** (`Win + X` > Device Manager)
3. Expand **Ports (COM & LPT)**
4. Look for `USB-SERIAL CH340 (COM3)` or similar
5. Note your port number

> **Sidewinder X1:** uses the CH340 chip. If nothing appears, install the driver from
> [wch-ic.com/downloads/CH341SER_EXE.html](http://www.wch-ic.com/downloads/CH341SER_EXE.html)

#### Step 2 -- Configure Claude Desktop

Open (or create) the config file at:
```
C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json
```

**Server mode (recommended):**

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":          "server",
        "REPETIER_SERVER_URL":    "http://localhost:3344",
        "REPETIER_SERVER_APIKEY": "YOUR_API_KEY_HERE",
        "REPETIER_PRINTER_SLUG":  "SidewinderX1",
        "PRINTER_MODEL":          "sidewinder_x1"
      }
    }
  }
}
```

**Serial mode:**

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":  "serial",
        "REPETIER_PORT":  "COM3",
        "REPETIER_BAUD":  "250000",
        "PRINTER_MODEL":  "sidewinder_x1"
      }
    }
  }
}
```

Restart Claude Desktop.

---

### Linux

```bash
pip install "git+https://github.com/Nstalej/repetier-mcp.git"
# For serial mode:
# pip install "repetier-mcp[serial] @ git+https://github.com/Nstalej/repetier-mcp.git"
# sudo usermod -a -G dialout $USER  # then log out and back in
```

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python3",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":          "server",
        "REPETIER_SERVER_URL":    "http://localhost:3344",
        "REPETIER_SERVER_APIKEY": "YOUR_API_KEY_HERE",
        "REPETIER_PRINTER_SLUG":  "SidewinderX1",
        "PRINTER_MODEL":          "sidewinder_x1"
      }
    }
  }
}
```

---

### macOS

```bash
pip install "git+https://github.com/Nstalej/repetier-mcp.git"
```

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python3",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":          "server",
        "REPETIER_SERVER_URL":    "http://localhost:3344",
        "REPETIER_SERVER_APIKEY": "YOUR_API_KEY_HERE",
        "REPETIER_PRINTER_SLUG":  "SidewinderX1",
        "PRINTER_MODEL":          "sidewinder_x1"
      }
    }
  }
}
```

---

## Troubleshooting (Windows)

| Problem | Solution |
|---|---|
| Printer not in Device Manager | Try a different USB cable -- many cables are charge-only |
| CH340 driver missing | Install from [wch-ic.com](http://www.wch-ic.com/downloads/CH341SER_EXE.html) |
| Port busy / access denied | Close Repetier-Host first -- it and this MCP can't share the port |
| Random disconnects during print | Disable USB power management in Device Manager > USB Hubs |
| Cannot connect to server | Verify Repetier-Server is running and the URL/port are correct |
| API key error | Check REPETIER_SERVER_APIKEY matches the key in Repetier-Server settings |
| Printer slug not found | Check REPETIER_PRINTER_SLUG matches the printer name in Repetier-Server |

---

## Available tools

| Tool                     | Mode   | Description                                             |
|--------------------------|--------|---------------------------------------------------------|
| `printer_status`         | Both   | Get temperatures, job progress and position             |
| `send_gcode`             | Both   | Send any G-code / M-code command                        |
| `temperature_check`      | Both   | Multi-sample temperature stability analysis             |
| `set_temperature`        | Both   | Set hotend or bed temperature                           |
| `list_jobs`              | Server | List print queue                                        |
| `upload_and_print`       | Server | Upload .gcode file and start printing                   |
| `pause_print`            | Server | Pause the current print job                             |
| `resume_print`           | Server | Resume a paused print job                               |
| `cancel_print`           | Server | Cancel/stop the current print                           |
| `diagnose_error`         | Both   | AI-powered error diagnosis with repair steps            |
| `knowledge_base_summary` | Both   | Show all known error types and their symptoms           |
| `list_serial_ports`      | Both   | Scan serial ports or show server connection info        |
| `emergency_stop`         | Both   | Send M112 emergency stop                                |

---

## Repetier-Server REST API Reference

The server mode uses the Repetier-Server REST API:

```
GET  /printer/api/{slug}?a=stateList&apikey={key}           # Full printer state
GET  /printer/api/{slug}?a=send&data={"cmd":"G28"}&apikey={key}  # Send G-code
GET  /printer/api/{slug}?a=listJobs&apikey={key}             # List jobs
GET  /printer/api/{slug}?a=pause&apikey={key}                # Pause print
GET  /printer/api/{slug}?a=continueJob&apikey={key}          # Resume print
GET  /printer/api/{slug}?a=stopJob&apikey={key}              # Cancel print
GET  /printer/api/{slug}?a=setExtruderTemperature&data={...} # Set hotend temp
GET  /printer/api/{slug}?a=setBedTemperature&data={...}      # Set bed temp
POST /printer/job/{slug}?a=upload&name=file.gcode&apikey={key}   # Upload gcode
```

---

## Diagnostic knowledge base

Built-in error database for the Artillery Sidewinder X1 -- **11 error types**:

| Error type                 | Key symptoms                                         |
|----------------------------|------------------------------------------------------|
| `thermal_runaway`          | THERMAL RUNAWAY, Heating failed, temp sensor         |
| `layer_shifting`           | Layer shift, skipped steps, position lost            |
| `z_offset_drift`           | First layer issues, bed leveling problems            |
| `extruder_clicking`        | Clicking, grinding, under extrusion                  |
| `communication_error`      | Printer offline, no response, timeout                |
| `bed_adhesion`             | Warping, not sticking, lifting corners               |
| `bltouch_probe_error`      | BLTouch alarm, probe deploy/stow failed              |
| `tmc_driver_noise`         | Motor noise, TMC2208 whining, stepper vibration      |
| `hotend_ptfe_degradation`  | Burning smell, PTFE fumes, heat creep, repeat clogs  |
| `tft_display_error`        | Screen frozen, white screen, TFT not responding      |
| `psu_failure`              | Random shutdown, printer dies, 24V rail drop         |

Plus **4 generic errors** (mintemp, maxtemp, filament_runout, sd_card_error).

Each diagnosis includes **probable causes**, **numbered repair steps**, and
**exact G-code commands** to run during troubleshooting.

---

## Roadmap

- [ ] OctoPrint compatibility layer
- [ ] Klipper / Moonraker support
- [ ] Webcam snapshot integration
- [ ] Print time prediction analysis
- [ ] Filament usage tracking
- [ ] Sidewinder X1 EEPROM tuning wizard

---

## Contributing

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

## License

MIT -- See [LICENSE](LICENSE)
