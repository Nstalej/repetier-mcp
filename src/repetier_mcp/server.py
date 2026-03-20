"""
repetier-mcp: MCP Server for Repetier-Host / Repetier-Server 3D printer control.

Connects Claude (and other MCP clients) to a 3D printer running through
Repetier-Host (USB/serial) or Repetier-Server (network API).

Capabilities:
- Real-time printer status: temperatures, job progress, layer info
- Job control: start, pause, cancel, list queued jobs
- G-code: send raw commands, query EEPROM settings
- Diagnostics: intelligent error analysis with Sidewinder X1 knowledge base
- Temperature history: track hotend/bed readings over time
"""

import os
import json
import time
import serial          # pyserial
import serial.tools.list_ports
from typing import Optional
from dataclasses import dataclass, asdict

import requests
from mcp.server.fastmcp import FastMCP

# ── Server init ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "repetier-mcp",
    instructions=(
        "You are connected to a 3D printer running Repetier firmware. "
        "Use the tools to monitor printer status, temperatures, and print jobs. "
        "When errors or anomalies are detected, use diagnose_error to get "
        "actionable repair advice. Always check printer status before sending "
        "G-code commands."
    ),
)

# ── Configuration ──────────────────────────────────────────────────────────────
# Connection mode: "serial" (Repetier-Host direct USB) or "server" (Repetier-Server API)
CONNECTION_MODE   = os.environ.get("REPETIER_MODE",   "serial")   # serial | server

# Serial (Repetier-Host direct)
SERIAL_PORT       = os.environ.get("REPETIER_PORT",   "")         # e.g. COM3 or /dev/ttyUSB0
SERIAL_BAUD       = int(os.environ.get("REPETIER_BAUD", "115200"))
SERIAL_TIMEOUT    = float(os.environ.get("REPETIER_TIMEOUT", "3.0"))

# Repetier-Server (network)
SERVER_HOST       = os.environ.get("REPETIER_HOST",   "localhost")
SERVER_HTTP_PORT  = int(os.environ.get("REPETIER_HTTP_PORT", "3344"))
SERVER_API_KEY    = os.environ.get("REPETIER_API_KEY", "")
PRINTER_SLUG      = os.environ.get("REPETIER_PRINTER", "")        # slug/name in server

# Printer model for targeted diagnostics
PRINTER_MODEL     = os.environ.get("PRINTER_MODEL",   "sidewinder_x1")


# ── Serial connection helpers ──────────────────────────────────────────────────

def _open_serial() -> serial.Serial:
    """Open a serial connection to the printer."""
    port = SERIAL_PORT or _auto_detect_port()
    if not port:
        raise ConnectionError(
            "No serial port configured and auto-detection failed. "
            "Set REPETIER_PORT env var (e.g. /dev/ttyUSB0 or COM3)."
        )
    return serial.Serial(port, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)


def _auto_detect_port() -> str:
    """Try to auto-detect a connected 3D printer via USB serial."""
    known_descriptions = ["USB Serial", "CH340", "CP210", "FTDI", "Arduino"]
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "") + (p.manufacturer or "")
        if any(k.lower() in desc.lower() for k in known_descriptions):
            return p.device
    # Fallback: return first available port
    return ports[0].device if ports else ""


def _send_gcode_serial(gcode: str, wait_lines: int = 5) -> list[str]:
    """
    Send a G-code command over serial and collect response lines.
    Returns list of response lines from the printer.
    """
    responses = []
    try:
        with _open_serial() as ser:
            cmd = gcode.strip().upper() + "\n"
            ser.write(cmd.encode("ascii"))
            deadline = time.time() + SERIAL_TIMEOUT * 2
            while time.time() < deadline:
                line = ser.readline().decode("ascii", errors="replace").strip()
                if line:
                    responses.append(line)
                if line == "ok" or len(responses) >= wait_lines:
                    break
    except serial.SerialException as e:
        responses.append(f"SERIAL ERROR: {e}")
    return responses


# ── Repetier-Server API helpers ───────────────────────────────────────────────

def _server_url(path: str) -> str:
    return f"http://{SERVER_HOST}:{SERVER_HTTP_PORT}{path}"


def _server_get(path: str, params: Optional[dict] = None) -> dict:
    """GET from Repetier-Server API, returns parsed JSON."""
    p = params or {}
    if SERVER_API_KEY:
        p["apikey"] = SERVER_API_KEY
    try:
        r = requests.get(_server_url(path), params=p, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def _server_post(path: str, data: dict) -> dict:
    if SERVER_API_KEY:
        data["apikey"] = SERVER_API_KEY
    try:
        r = requests.post(_server_url(path), json=data, timeout=5)
        r.raise_for_status()
        return r.json() if r.text else {"ok": True}
    except requests.RequestException as e:
        return {"error": str(e)}


# ── Sidewinder X1 diagnostic knowledge base ───────────────────────────────────

SIDEWINDER_X1_ERRORS = {
    "thermal_runaway": {
        "symptoms": ["THERMAL RUNAWAY", "Heating failed", "temp sensor"],
        "causes": [
            "Loose thermistor connector on hotend or heated bed",
            "Damaged thermistor wire (common after many print hours)",
            "Faulty MOSFET on the mainboard (especially bed MOSFET)",
            "PID tuning needed — stock firmware PID can drift",
        ],
        "fixes": [
            "1. Check all thermistor connectors at the mainboard (E0 and BED headers)",
            "2. Inspect thermistor wires for cuts or pinches near the hotend",
            "3. Run PID autotune: M303 E0 S200 C8 (hotend) then M303 E-1 S60 C8 (bed)",
            "4. Save new PID with M500",
            "5. If bed MOSFET smells burnt: replace mainboard or add external MOSFET",
        ],
    },
    "layer_shifting": {
        "symptoms": ["layer shift", "shifted", "skipped steps", "position lost"],
        "causes": [
            "X/Y belt tension too loose (very common on Sidewinder X1)",
            "Print speed too high for mass of X-axis gantry (heavy dual-Z)",
            "X-axis motor current too low in firmware",
            "Loose set screws on X/Y motor pulleys",
        ],
        "fixes": [
            "1. Tension X belt: should feel like a guitar string, ~50Hz when plucked",
            "2. Tension Y belt: same target. Use printed tensioners if needed",
            "3. Check all 4 set screws on X motor pulley and Y motor pulley",
            "4. Reduce print speed to 60 mm/s max for first diagnosis",
            "5. In Marlin: increase X_CURRENT and Y_CURRENT by 50–100mA",
        ],
    },
    "z_offset_drift": {
        "symptoms": ["first layer", "nozzle too far", "nozzle too close", "bed leveling"],
        "causes": [
            "BLTouch probe (if installed) needs re-deploy/stow calibration",
            "Z-axis lead screw backlash",
            "Thermal expansion shifting Z-offset between cold and hot",
        ],
        "fixes": [
            "1. Always run bed leveling hot (target print temps)",
            "2. Run G29 after printer reaches temperature",
            "3. Use M851 to adjust Z-offset in 0.05mm steps",
            "4. Save with M500 after each adjustment",
        ],
    },
    "extruder_clicking": {
        "symptoms": ["clicking", "grinding", "extruder skip", "under extrusion"],
        "causes": [
            "Clog or partial clog in hotend (most common cause)",
            "Print temperature too low for filament",
            "Extruder tension arm spring weak or broken",
            "Bowden tube gap at hotend end (PTFE retraction gap)",
        ],
        "fixes": [
            "1. Cold pull: heat to 200°C, push filament manually, cool to 90°C, pull firmly",
            "2. Increase hotend temp by 5°C increments until clicking stops",
            "3. Check/tighten Bowden clip at hotend coupling",
            "4. Inspect extruder arm spring — replace if flattened",
            "5. Consider Micro-Swiss all-metal hotend to eliminate PTFE degradation",
        ],
    },
    "communication_error": {
        "symptoms": ["communication error", "printer offline", "no response", "timeout"],
        "causes": [
            "USB cable quality issue (very common — use a data cable, not charge-only)",
            "Wrong baud rate configured (Sidewinder X1 stock: 250000)",
            "USB port power management putting port to sleep",
            "Receive cache size mismatch",
        ],
        "fixes": [
            "1. Try a different USB cable — specifically a shielded data cable",
            "2. Set baud rate to 250000 in Repetier-Host connection settings",
            "3. Set receive cache to 63 (not 127) if errors persist during printing",
            "4. Windows: disable USB power management for that port in Device Manager",
            "5. Linux: add user to 'dialout' group: sudo usermod -a -G dialout $USER",
        ],
    },
    "bed_adhesion": {
        "symptoms": ["warping", "not sticking", "lifting corners", "first layer peeling"],
        "causes": [
            "Bed surface contamination (fingerprints, oils)",
            "First layer too high",
            "Bed temperature too low for filament",
            "No brim/raft for large prints",
        ],
        "fixes": [
            "1. Clean PEI/glass with IPA 90%+ before every print",
            "2. Lower Z-offset by 0.05mm increments until first layer squishes",
            "3. PLA: 60°C bed | PETG: 80°C | ABS: 100°C + enclosure",
            "4. Add 5–8mm brim for large flat parts",
        ],
    },

    # ── NEW: BLTouch / CR Touch probe errors ─────────────────────────────────
    "bltouch_probe_error": {
        "symptoms": [
            "BLTouch", "probe failed", "deploy failed", "stow failed",
            "probe triggered", "alarm state", "CR Touch", "bed probe",
        ],
        "causes": [
            "BLTouch pin stuck in deployed position (most common — happens after a crash)",
            "Probe wiring reversed or loose at the mainboard connector (5-wire connector)",
            "Probe Z-offset not calibrated after installation or firmware update",
            "BLTouch in alarm state — needs manual reset cycle",
            "Probe mount too high or too low — nozzle hits bed before probe triggers",
            "Stock Artillery mainboard needs firmware compiled with BLTouch support (not stock)",
        ],
        "fixes": [
            "1. Reset BLTouch alarm: send M280 P0 S160 (reset) then M280 P0 S10 (deploy test)",
            "2. If pin stays down: send M280 P0 S90 to force stow, then power-cycle",
            "3. Check 5-pin JST connector polarity: GND-GND-5V-SIG-SIG (Artillery pinout)",
            "4. Run Z-offset wizard after any probe reset: G28 then M851 Z-X.XX",
            "5. Verify probe trigger height: probe should click ~2mm above nozzle tip",
            "6. If using stock firmware: flash Artillery Sidewinder X1 BLTouch build from GitHub",
            "7. Community resource: Artillery Genius / Sidewinder X1 BLTouch guide on Reddit",
        ],
        "gcode_helpers": [
            "M280 P0 S160  ; Reset BLTouch alarm",
            "M280 P0 S10   ; Deploy probe pin (test)",
            "M280 P0 S90   ; Stow probe pin",
            "M851          ; Query current Z-offset",
            "M851 Z-2.35   ; Set Z-offset (adjust value to your printer)",
            "M500          ; Save to EEPROM",
        ],
    },

    # ── NEW: TMC stepper driver noise / configuration issues ──────────────────
    "tmc_driver_noise": {
        "symptoms": [
            "motor noise", "stepper noise", "loud motors", "whining", "screaming motors",
            "TMC", "TMC2208", "TMC2209", "stepper driver", "motor vibration",
            "grinding noise", "high pitched", "motor sound",
        ],
        "causes": [
            "Stock A4988 drivers replaced with TMC2208/2209 but UART mode not configured",
            "TMC drivers in standalone mode with wrong Vref voltage (too high = noise + heat)",
            "Microstepping mismatch between driver jumpers and firmware configuration",
            "TMC SpreadCycle mode active — normal noise; switch to StealthChop for silence",
            "Driver current (RMS) set too high causing resonance at certain speeds",
            "Loose motor cable connector vibrating against frame",
        ],
        "fixes": [
            "1. Measure Vref on TMC2208: target 0.9V for ~0.9A RMS (Sidewinder X1 motors)",
            "2. Formula: Vref = (motor_current_A × 2.5) / 2.0  — for TMC2208 in standalone",
            "3. Enable StealthChop in Marlin: set STEALTHCHOP_XY and STEALTHCHOP_Z to true",
            "4. If UART mode: set driver current via M906 X800 Y800 Z800 E650 (mA values)",
            "5. Check all motor cable connectors — reseat connectors at both motor and board",
            "6. Add thermal pads + heatsinks to TMC drivers — they run hot",
            "7. Reduce acceleration: M201 X500 Y500 Z100 E5000 — saves on noise + layer shift",
        ],
        "gcode_helpers": [
            "M906 X800 Y800 Z800 E650  ; Set motor currents (mA) — requires UART mode",
            "M201 X500 Y500 Z100       ; Set max acceleration (mm/s²)",
            "M203 X200 Y200 Z10        ; Set max feedrate (mm/s)",
            "M500                      ; Save to EEPROM",
        ],
    },

    # ── NEW: Volcano hotend / PTFE degradation issues ─────────────────────────
    "hotend_ptfe_degradation": {
        "symptoms": [
            "PTFE", "burning smell", "white smoke", "clogging repeatedly",
            "filament smells", "toxic fumes", "repeated clogs", "jamming",
            "volcano", "hotend jam", "heat creep", "cold zone",
        ],
        "causes": [
            "Stock Sidewinder X1 Volcano hotend has PTFE tube that reaches the heat break",
            "PTFE liner degrades above 240°C releasing fumes — do NOT print ABS with stock hotend",
            "Heat creep: hotend cooling fan too slow or blocked, heat migrates up into cold zone",
            "PTFE tube end cut at angle instead of flat — creates gap where filament curls",
            "Bowden tube inner diameter worn out — 1.75mm filament needs tight ID tolerance",
            "Nozzle partially blocked from printing low-quality or abrasive filaments",
        ],
        "fixes": [
            "1. IMMEDIATE: Do NOT print above 240°C with stock PTFE-lined hotend",
            "2. Check hotend cooling fan — must spin at full speed during the entire print",
            "3. Cut Bowden tube end perfectly flat using a tube cutter (not scissors)",
            "4. Upgrade path: Micro-Swiss all-metal hotend eliminates PTFE from heat zone",
            "5. After upgrade to all-metal: increase retraction to 6–7mm and temp by 5–10°C",
            "6. Clean nozzle: atomic/cold pull with nylon filament at 250°C",
            "7. Replace Bowden tube with Capricorn XS (tighter ID = better filament control)",
        ],
        "gcode_helpers": [
            "M106 S255  ; Fan at 100% — verify hotend fan responds",
            "M104 S200  ; Set hotend to 200°C for cold pull",
            "M104 S0    ; Turn off hotend after maintenance",
        ],
    },

    # ── NEW: TFT touchscreen display errors ───────────────────────────────────
    "tft_display_error": {
        "symptoms": [
            "screen frozen", "display blank", "touchscreen not responding",
            "TFT", "screen glitch", "display error", "LCD", "frozen screen",
            "white screen", "black screen", "touch not working", "screen flicker",
        ],
        "causes": [
            "TFT firmware version mismatch with mainboard firmware (very common after updates)",
            "Flat ribbon cable between TFT and mainboard loose or damaged",
            "TFT config file (BIGTREE_TFT35.cfg or similar) has wrong printer settings",
            "Corrupted SD card on TFT side — TFT has its own internal SD storage",
            "Power supply ripple causing display resets during heavy print moves",
            "Stock TFT firmware has known bugs — community firmware (BigTreeTech) is recommended",
        ],
        "fixes": [
            "1. Check and reseat the ribbon cable behind the display panel",
            "2. Reflash TFT firmware: download matching version from Artillery GitHub",
            "3. Update config.ini on TFT SD card — set correct baud rate (250000 for X1)",
            "4. If screen goes blank during print: suspect PSU — measure 24V rail under load",
            "5. Community TFT firmware: github.com/bigtreetech/BIGTREETECH-TouchScreenFirmware",
            "6. Hard reset: hold reset button on back of display for 5 seconds",
        ],
        "gcode_helpers": [
            "; No direct G-code fixes — this is a firmware/hardware issue",
            "; Use M503 to verify mainboard is alive if display is unresponsive",
            "M503  ; Read EEPROM — if this responds, mainboard is OK, issue is TFT only",
        ],
    },

    # ── NEW: Power supply unit failures ──────────────────────────────────────
    "psu_failure": {
        "symptoms": [
            "power supply", "PSU", "printer turns off", "random shutdown",
            "voltage drop", "print stops randomly", "reboots during print",
            "clicking from power supply", "burning smell from back", "24v rail", "power issue",
            "printer dies", "mid-print shutdown", "restarts randomly",
        ],
        "causes": [
            "Stock PSU in some Sidewinder X1 batches (2019–2021) is undersized for bed + hotend load",
            "PSU fan clogged with dust — thermal shutdown during long prints",
            "Loose AC input connector inside PSU causing intermittent power loss",
            "Heated bed draws ~200W peak — combined with hotend hits PSU limit",
            "PSU capacitors degrading after 1–2 years of heavy use",
            "Mains voltage fluctuations in some regions destabilizing PSU output",
        ],
        "fixes": [
            "1. Clean PSU fan vents with compressed air — check monthly",
            "2. Measure 24V rail with multimeter under load: should stay above 23.5V",
            "3. Check all wiring connections inside PSU cover (AC input terminal block)",
            "4. Reduce bed temperature by 5°C to lower PSU load during diagnosis",
            "5. Upgrade: replace with Meanwell LRS-350-24 (350W, proven reliable, ~$25)",
            "6. Add external MOSFET for heated bed to reduce load on mainboard/PSU wiring",
            "7. If PSU clicks when bed heats: failing capacitor — replace PSU immediately",
        ],
        "gcode_helpers": [
            "M140 S55    ; Reduce bed to 55°C to lower PSU load during diagnosis",
            "M303 E-1 S60 C8  ; Re-tune bed PID after PSU replacement",
            "M500        ; Save PID values",
        ],
    },
}

GENERIC_ERRORS = {
    "mintemp": {
        "symptoms": ["MINTEMP", "thermistor open"],
        "causes": [
            "Thermistor disconnected or broken wire",
            "Thermistor connector not fully seated at mainboard",
        ],
        "fixes": [
            "1. Check thermistor connector at mainboard (E0_TEMP and BED_TEMP headers)",
            "2. Test thermistor resistance: should read ~100kΩ at room temp (NTC 100k)",
            "3. Inspect wire for breaks near the hotend where it flexes most",
            "4. Replace thermistor cartridge if resistance reads open (∞) or shorted (0)",
        ],
        "gcode_helpers": [
            "M105  ; Read current temps — if MINTEMP persists, thermistor is open",
        ],
    },
    "maxtemp": {
        "symptoms": ["MAXTEMP", "temperature too high"],
        "causes": [
            "Short circuit in thermistor wires",
            "Thermistor wire touching hot metal (heater block)",
            "Wrong thermistor type selected in firmware",
        ],
        "fixes": [
            "1. Inspect thermistor wires for shorts or contact with heater block",
            "2. Verify firmware thermistor type matches hardware (NTC 100k = type 1 in Marlin)",
            "3. Replace thermistor if wires are damaged",
            "4. Use kapton tape to insulate thermistor wires from heater block",
        ],
        "gcode_helpers": [
            "M105  ; Read temps — MAXTEMP at room temp = thermistor shorted",
        ],
    },
    "filament_runout": {
        "symptoms": ["filament runout", "filament sensor", "out of filament", "runout sensor"],
        "causes": [
            "Filament spool actually empty",
            "Filament runout sensor falsely triggering (dirty sensor or loose wire)",
            "Filament sensor enabled in firmware but no sensor installed",
        ],
        "fixes": [
            "1. Check filament spool — load new spool if empty",
            "2. Clean runout sensor with compressed air",
            "3. Check sensor wiring connector at mainboard",
            "4. To disable sensor temporarily: M412 S0 (then M500 to save)",
        ],
        "gcode_helpers": [
            "M412 S0  ; Disable filament runout sensor",
            "M412 S1  ; Re-enable filament runout sensor",
            "M412     ; Query runout sensor status",
            "M500     ; Save setting to EEPROM",
        ],
    },
    "sd_card_error": {
        "symptoms": ["SD card", "SD init", "card error", "no card", "SD read error"],
        "causes": [
            "SD card not fully seated in slot",
            "SD card formatted incorrectly (must be FAT32, ≤32GB)",
            "Corrupted files on SD card",
            "SD card slot pins bent or dirty",
        ],
        "fixes": [
            "1. Remove and reinsert SD card firmly",
            "2. Format SD card as FAT32 with 4096 byte allocation unit",
            "3. Use SD card ≤32GB — larger cards may not be recognized",
            "4. Test with a known-good SD card",
            "5. Clean SD card pins with IPA and a soft brush",
        ],
        "gcode_helpers": [
            "M21  ; Initialize SD card",
            "M22  ; Release SD card",
            "M20  ; List files on SD card",
        ],
    },
}


def _diagnose(error_text: str, model: str) -> dict:
    """
    Match error text against knowledge base and return the best diagnosis.

    Scoring: counts how many symptom phrases from each error type appear in the
    error_text. Returns the error type with the highest score (most matches).
    Falls back to first single-match if no multi-match found.
    """
    error_lower = error_text.lower()

    # Build combined KB: model-specific first so they take priority over generic
    kb: dict = {}
    if "sidewinder" in model.lower() or "artillery" in model.lower():
        kb.update(SIDEWINDER_X1_ERRORS)
    kb.update(GENERIC_ERRORS)

    scores: dict[str, tuple[int, dict]] = {}
    for error_id, data in kb.items():
        count = sum(1 for sym in data["symptoms"] if sym.lower() in error_lower)
        if count > 0:
            scores[error_id] = (count, data)

    if not scores:
        return {
            "error_type": "unknown",
            "causes": ["Error pattern not found in knowledge base"],
            "fixes": [
                "1. Copy the full error message from Repetier-Host log window",
                "2. Search: Artillery Sidewinder X1 + your error on Reddit r/3Dprinting",
                "3. Artillery Facebook group: 'Artillery 3D Printer Users'",
                "4. Run temperature_check() to rule out thermal instability",
                "5. Share full error text with the community or open an issue on this repo",
            ],
            "gcode_helpers": [
                "M503  ; Print all EEPROM settings — useful context for community help",
                "M105  ; Current temperatures",
                "M114  ; Current position",
            ],
        }

    # Return the error type with the most symptom matches
    best_id = max(scores, key=lambda k: scores[k][0])
    return {"error_type": best_id, **scores[best_id][1]}


# ═════════════════════════════════════════════════════════════════════════════
# MCP TOOLS
# ═════════════════════════════════════════════════════════════════════════════

# ── Tool: printer_status ───────────────────────────────────────────────────────

@mcp.tool()
def printer_status() -> str:
    """
    Get the current status of the 3D printer.

    Returns temperatures (hotend, bed), print job progress, current layer,
    print speed, fan speed, and online/offline status.

    Works with both direct USB/serial (Repetier-Host) and
    Repetier-Server network connections.
    """
    if CONNECTION_MODE == "server":
        slug = PRINTER_SLUG or "default"
        data = _server_get(f"/printer/info/{slug}")
        if "error" in data:
            return f"ERROR connecting to Repetier-Server: {data['error']}"
        return json.dumps(data, indent=2)

    # Serial mode — query via M105 (temperatures) + M27 (SD progress)
    results = {}

    temp_lines = _send_gcode_serial("M105", wait_lines=3)
    results["raw_temp"] = temp_lines

    progress_lines = _send_gcode_serial("M27", wait_lines=3)
    results["raw_progress"] = progress_lines

    position_lines = _send_gcode_serial("M114", wait_lines=3)
    results["raw_position"] = position_lines

    # Parse temperature from "ok T:205.3 /200.0 B:59.8 /60.0" format
    parsed = {"hotend": {}, "bed": {}, "position": "", "job": {}}
    for line in temp_lines:
        if "T:" in line:
            try:
                parts = line.split()
                for part in parts:
                    if part.startswith("T:"):
                        vals = part[2:].split("/")
                        parsed["hotend"] = {
                            "actual_C": float(vals[0]),
                            "target_C": float(vals[1]) if len(vals) > 1 else 0,
                        }
                    elif part.startswith("B:"):
                        vals = part[2:].split("/")
                        parsed["bed"] = {
                            "actual_C": float(vals[0]),
                            "target_C": float(vals[1]) if len(vals) > 1 else 0,
                        }
            except (ValueError, IndexError):
                pass

    for line in progress_lines:
        if "SD printing byte" in line or "%" in line:
            parsed["job"]["progress_raw"] = line

    for line in position_lines:
        if line.startswith("X:") or "X:" in line:
            parsed["position"] = line
            break

    return json.dumps({"parsed": parsed, "raw": results}, indent=2)


# ── Tool: send_gcode ──────────────────────────────────────────────────────────

@mcp.tool()
def send_gcode(command: str, description: str = "") -> str:
    """
    Send a single G-code or M-code command to the printer.

    SAFETY: Only use well-known commands. Never send movement commands
    (G0, G1, G28) without confirming the printer is in a safe state.

    Common safe commands:
      M105  — Read temperatures
      M114  — Get current position
      M503  — Read EEPROM settings
      M500  — Save settings to EEPROM
      M106 S128 — Set fan to 50%
      M104 S0   — Turn off hotend
      M140 S0   — Turn off heated bed

    Args:
        command:     G-code string, e.g. "M105" or "G28 X Y".
        description: Optional note for logging purposes.

    Returns:
        Printer response lines.
    """
    cmd = command.strip().upper()

    # Safety: block potentially destructive commands without confirmation
    blocked = ["M112", "M0"]  # Emergency stop / unconditional stop
    if any(cmd.startswith(b) for b in blocked):
        return (
            f"Command '{cmd}' requires explicit confirmation.\n"
            "If you really mean to emergency-stop, call emergency_stop() instead."
        )

    if CONNECTION_MODE == "server":
        slug = PRINTER_SLUG or "default"
        result = _server_get(f"/printer/send/{slug}", {"cmd": command})
        return json.dumps(result)

    lines = _send_gcode_serial(cmd, wait_lines=10)
    note = f"[{description}] " if description else ""
    return f"{note}Sent: {cmd}\nResponse:\n" + "\n".join(lines)


# ── Tool: list_jobs ────────────────────────────────────────────────────────────

@mcp.tool()
def list_jobs() -> str:
    """
    List all print jobs in the Repetier-Server queue.

    Returns job names, status (none/printing/paused/waitstart) and file sizes.
    Note: Only available when CONNECTION_MODE=server.
    """
    if CONNECTION_MODE != "server":
        return (
            "Job listing requires Repetier-Server (CONNECTION_MODE=server).\n"
            "In direct USB mode, use send_gcode('M27') to check SD card progress."
        )

    slug = PRINTER_SLUG or "default"
    data = _server_get(f"/printer/jobs/{slug}")
    if "error" in data:
        return f"ERROR: {data['error']}"
    return json.dumps(data, indent=2)


# ── Tool: diagnose_error ───────────────────────────────────────────────────────

@mcp.tool()
def diagnose_error(error_text: str, printer_model: Optional[str] = None) -> str:
    """
    Diagnose a 3D printer error and provide actionable repair guidance.

    Uses a knowledge base of known issues for the Sidewinder X1 and
    common Repetier/Marlin firmware errors.

    Args:
        error_text:    The error message or description of the problem.
                       Can be copied from Repetier-Host log window.
                       Examples: "THERMAL RUNAWAY", "layer shifting",
                       "extruder clicking", "communication error".
        printer_model: Override printer model for diagnosis.
                       Default: value of PRINTER_MODEL env var (sidewinder_x1).

    Returns:
        Structured diagnosis with probable causes and step-by-step fixes.
    """
    model = printer_model or PRINTER_MODEL
    diagnosis = _diagnose(error_text, model)

    lines = [
        f"🔍 Diagnosis for: '{error_text}'",
        f"   Printer: {model}",
        f"   Error type: {diagnosis['error_type']}",
        "",
        "📋 Probable causes:",
    ]
    for i, cause in enumerate(diagnosis.get("causes", []), 1):
        lines.append(f"   {i}. {cause}")

    lines += ["", "🔧 Recommended fixes (in order):"]
    for fix in diagnosis.get("fixes", []):
        lines.append(f"   {fix}")

    gcode_helpers = diagnosis.get("gcode_helpers", [])
    if gcode_helpers:
        lines += ["", "📟 Useful G-code commands for this issue:"]
        for gc in gcode_helpers:
            lines.append(f"   {gc}")

    lines += [
        "",
        "💡 Tip: Run printer_status() before and after each fix to",
        "   confirm the issue is resolved.",
    ]
    return "\n".join(lines)


# ── Tool: temperature_check ────────────────────────────────────────────────────

@mcp.tool()
def temperature_check(samples: int = 5, interval_seconds: float = 2.0) -> str:
    """
    Take multiple temperature readings to check for stability.

    Useful for detecting intermittent thermal issues — a stable temperature
    should vary less than ±2°C between readings.

    Args:
        samples:          Number of temperature readings to take (1–20).
        interval_seconds: Seconds between readings (0.5–10).

    Returns:
        Table of hotend and bed temperatures with stability analysis.
    """
    samples = max(1, min(20, samples))
    interval_seconds = max(0.5, min(10.0, interval_seconds))

    readings = []
    for i in range(samples):
        lines = _send_gcode_serial("M105", wait_lines=3)
        timestamp = time.strftime("%H:%M:%S")
        hotend, bed = None, None
        for line in lines:
            if "T:" in line:
                try:
                    parts = line.split()
                    for part in parts:
                        if part.startswith("T:"):
                            hotend = float(part[2:].split("/")[0])
                        elif part.startswith("B:"):
                            bed = float(part[2:].split("/")[0])
                except (ValueError, IndexError):
                    pass
        readings.append({"t": timestamp, "hotend": hotend, "bed": bed})
        if i < samples - 1:
            time.sleep(interval_seconds)

    # Analysis
    hotend_vals = [r["hotend"] for r in readings if r["hotend"] is not None]
    bed_vals    = [r["bed"]    for r in readings if r["bed"]    is not None]

    lines = [f"Temperature check — {samples} samples at {interval_seconds}s intervals", ""]
    lines.append(f"{'Time':<10} {'Hotend (°C)':>12} {'Bed (°C)':>10}")
    lines.append("-" * 36)
    for r in readings:
        h = f"{r['hotend']:.1f}" if r["hotend"] is not None else "err"
        b = f"{r['bed']:.1f}"    if r["bed"]    is not None else "err"
        lines.append(f"{r['t']:<10} {h:>12} {b:>10}")

    lines.append("-" * 36)
    if hotend_vals:
        spread = max(hotend_vals) - min(hotend_vals)
        status = "✅ Stable" if spread < 2 else "⚠️  UNSTABLE"
        lines.append(f"Hotend spread: {spread:.1f}°C  {status}")
    if bed_vals:
        spread = max(bed_vals) - min(bed_vals)
        status = "✅ Stable" if spread < 1 else "⚠️  UNSTABLE"
        lines.append(f"Bed spread   : {spread:.1f}°C  {status}")

    if not hotend_vals:
        lines.append("\n⚠️  Could not read temperatures. Check serial connection.")
        lines.append("Run diagnose_error('communication error') for troubleshooting.")

    return "\n".join(lines)


# ── Tool: list_serial_ports ────────────────────────────────────────────────────

@mcp.tool()
def list_serial_ports() -> str:
    """
    Scan and list all available serial ports on this computer.

    Useful for finding the correct port when setting up the printer connection.
    The Sidewinder X1 typically appears as /dev/ttyUSB0 (Linux),
    /dev/cu.usbserial-* (macOS), or COM3–COM9 (Windows).

    Returns:
        List of ports with device path, description and hardware ID.
    """
    ports = serial.tools.list_ports.comports()
    if not ports:
        return "No serial ports found. Is the printer connected via USB?"

    lines = [f"{'Port':<20} {'Description':<35} {'Hardware ID'}"]
    lines.append("-" * 80)
    for p in sorted(ports, key=lambda x: x.device):
        lines.append(f"{p.device:<20} {(p.description or 'n/a'):<35} {p.hwid or ''}")

    detected = _auto_detect_port()
    if detected:
        lines.append(f"\n🖨️  Auto-detected printer port: {detected}")
        lines.append(f"   Set: REPETIER_PORT={detected}")
    return "\n".join(lines)


# ── Tool: emergency_stop ───────────────────────────────────────────────────────

@mcp.tool()
def emergency_stop() -> str:
    """
    Send M112 emergency stop to the printer.

    ⚠️  WARNING: This immediately halts all motion and turns off heaters.
    Use only if there is a real safety risk (fire, crash, uncontrolled movement).
    The printer will need to be power-cycled and re-homed after an emergency stop.

    Returns:
        Confirmation that M112 was sent.
    """
    if CONNECTION_MODE == "server":
        slug = PRINTER_SLUG or "default"
        result = _server_get(f"/printer/send/{slug}", {"cmd": "M112"})
        return f"⛔ Emergency stop sent to Repetier-Server.\n{json.dumps(result)}"

    lines = _send_gcode_serial("M112", wait_lines=2)
    return "⛔ Emergency stop (M112) sent.\nPower-cycle the printer before resuming.\nResponse: " + " | ".join(lines)


# ── Tool: knowledge_base_summary ──────────────────────────────────────────────

@mcp.tool()
def knowledge_base_summary() -> str:
    """
    List all known error types in the diagnostic knowledge base.

    Returns the error categories and their symptom keywords,
    so you know what to look for in Repetier-Host log messages.
    """
    lines = [
        "📚 Diagnostic Knowledge Base",
        f"   Printer model: {PRINTER_MODEL}",
        "",
    ]
    all_errors = {**SIDEWINDER_X1_ERRORS, **GENERIC_ERRORS}
    for error_id, data in all_errors.items():
        lines.append(f"🔴 {error_id}")
        lines.append(f"   Symptoms: {', '.join(data['symptoms'])}")
        lines.append(f"   {len(data['causes'])} known cause(s) | {len(data['fixes'])} fix step(s)")
        lines.append("")
    lines.append("Use diagnose_error(error_text) with any symptom phrase.")
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
