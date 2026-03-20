"""Tests for repetier-mcp server tools (no printer hardware required)."""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from repetier_mcp.server import (
    diagnose_error,
    knowledge_base_summary,
    _diagnose,
    SIDEWINDER_X1_ERRORS,
    GENERIC_ERRORS,
)


# ── Tests: diagnose_error — errores originales ─────────────────────────────────

class TestDiagnoseError:

    def test_thermal_runaway_detected(self):
        result = diagnose_error("THERMAL RUNAWAY detected")
        assert "thermal_runaway" in result
        assert "thermistor" in result.lower() or "MOSFET" in result

    def test_layer_shifting_detected(self):
        result = diagnose_error("layer shift after 2 hours")
        assert "layer_shifting" in result
        assert "belt" in result.lower()

    def test_extruder_clicking(self):
        result = diagnose_error("extruder is clicking and grinding")
        assert "extruder_clicking" in result
        assert "clog" in result.lower() or "temperature" in result.lower()

    def test_communication_error(self):
        result = diagnose_error("printer offline communication error")
        assert "communication_error" in result
        assert "USB" in result or "baud" in result.lower()

    def test_bed_adhesion(self):
        result = diagnose_error("print is warping and not sticking")
        assert "bed_adhesion" in result
        assert "IPA" in result or "temperature" in result.lower()

    def test_unknown_error_returns_graceful_response(self):
        result = diagnose_error("the printer is making a weird whirring noise at 3am")
        assert "unknown" in result
        assert "knowledge base" in result.lower() or "community" in result.lower()

    def test_result_contains_fix_steps(self):
        result = diagnose_error("layer shifting")
        assert "fix" in result.lower() or "step" in result.lower() or "1." in result

    # ── Nuevos errores Sidewinder X1 ───────────────────────────────────────────

    def test_bltouch_probe_error(self):
        result = diagnose_error("BLTouch probe failed to deploy")
        assert "bltouch_probe_error" in result
        assert "M280" in result  # gcode helper presente

    def test_bltouch_alarm_state(self):
        result = diagnose_error("probe alarm state triggered")
        assert "bltouch_probe_error" in result

    def test_tmc_driver_noise(self):
        result = diagnose_error("stepper motors making loud whining noise")
        assert "tmc_driver_noise" in result
        assert "Vref" in result or "StealthChop" in result

    def test_tmc_driver_vibration(self):
        result = diagnose_error("motor vibration high pitched TMC2208")
        assert "tmc_driver_noise" in result

    def test_hotend_ptfe_degradation(self):
        result = diagnose_error("burning smell from PTFE and repeated clogs")
        assert "hotend_ptfe_degradation" in result
        assert "240" in result  # temperatura límite PTFE

    def test_hotend_heat_creep(self):
        result = diagnose_error("heat creep jamming filament")
        assert "hotend_ptfe_degradation" in result

    def test_tft_display_frozen(self):
        result = diagnose_error("screen frozen touchscreen not responding")
        assert "tft_display_error" in result
        assert "M503" in result  # gcode helper presente

    def test_tft_white_screen(self):
        result = diagnose_error("white screen on TFT display")
        assert "tft_display_error" in result

    def test_psu_random_shutdown(self):
        result = diagnose_error("printer turns off randomly mid-print shutdown")
        assert "psu_failure" in result
        assert "Meanwell" in result or "24V" in result or "24v" in result.lower()

    def test_psu_clicking(self):
        result = diagnose_error("clicking from power supply when bed heats up")
        assert "psu_failure" in result

    # ── Errores genéricos nuevos ───────────────────────────────────────────────

    def test_mintemp_generic_error(self):
        result = diagnose_error("MINTEMP triggered")
        assert "mintemp" in result
        assert "thermistor" in result.lower()

    def test_maxtemp_generic_error(self):
        result = diagnose_error("MAXTEMP error reported")
        assert "maxtemp" in result

    def test_filament_runout(self):
        result = diagnose_error("filament runout sensor triggered")
        assert "filament_runout" in result
        assert "M412" in result  # gcode helper

    def test_sd_card_error(self):
        result = diagnose_error("SD card init error")
        assert "sd_card_error" in result
        assert "FAT32" in result

    # ── gcode_helpers en el output ─────────────────────────────────────────────

    def test_gcode_helpers_shown_for_bltouch(self):
        result = diagnose_error("BLTouch deploy failed")
        assert "📟" in result or "G-code" in result
        assert "M280" in result

    def test_gcode_helpers_shown_for_psu(self):
        result = diagnose_error("PSU reboots during print")
        assert "M140" in result  # reduce bed temp helper

    def test_gcode_helpers_shown_for_unknown(self):
        result = diagnose_error("totally unknown printer error xyz")
        assert "M503" in result  # fallback helper siempre presente


class TestDiagnoseFunction:

    def test_returns_dict_with_required_keys(self):
        result = _diagnose("thermal runaway", "sidewinder_x1")
        assert "error_type" in result
        assert "causes" in result
        assert "fixes" in result

    def test_causes_and_fixes_are_nonempty_lists(self):
        result = _diagnose("layer shift", "sidewinder_x1")
        assert isinstance(result["causes"], list)
        assert len(result["causes"]) > 0
        assert isinstance(result["fixes"], list)
        assert len(result["fixes"]) > 0

    def test_case_insensitive_matching(self):
        r1 = _diagnose("THERMAL RUNAWAY", "sidewinder_x1")
        r2 = _diagnose("thermal runaway", "sidewinder_x1")
        assert r1["error_type"] == r2["error_type"]

    def test_artillery_alias_uses_sidewinder_kb(self):
        """'artillery' en el modelo debe activar la KB de Sidewinder X1."""
        r1 = _diagnose("BLTouch failed", "sidewinder_x1")
        r2 = _diagnose("BLTouch failed", "artillery_x1")
        assert r1["error_type"] == r2["error_type"]

    def test_unknown_model_uses_generic_kb_only(self):
        """Un modelo desconocido no debe crashear — usa solo GENERIC_ERRORS."""
        result = _diagnose("MINTEMP error", "ender_3_pro")
        assert result["error_type"] == "mintemp"

    def test_gcode_helpers_present_in_new_errors(self):
        for error_id in ["bltouch_probe_error", "tmc_driver_noise",
                         "hotend_ptfe_degradation", "tft_display_error", "psu_failure"]:
            data = SIDEWINDER_X1_ERRORS[error_id]
            assert "gcode_helpers" in data, f"{error_id} missing gcode_helpers"
            assert len(data["gcode_helpers"]) > 0


# ── Tests: knowledge base completeness ────────────────────────────────────────

class TestKnowledgeBase:

    def test_all_sidewinder_errors_have_symptoms(self):
        for name, data in SIDEWINDER_X1_ERRORS.items():
            assert "symptoms" in data, f"{name} missing 'symptoms'"
            assert len(data["symptoms"]) > 0

    def test_all_sidewinder_errors_have_causes(self):
        for name, data in SIDEWINDER_X1_ERRORS.items():
            assert "causes" in data, f"{name} missing 'causes'"
            assert len(data["causes"]) > 0

    def test_all_sidewinder_errors_have_fixes(self):
        for name, data in SIDEWINDER_X1_ERRORS.items():
            assert "fixes" in data, f"{name} missing 'fixes'"
            assert len(data["fixes"]) > 0

    def test_total_error_count(self):
        """Debe haber 11 errores en total: 6 originales + 5 nuevos."""
        assert len(SIDEWINDER_X1_ERRORS) == 11

    def test_generic_errors_expanded(self):
        """GENERIC_ERRORS debe tener 4 entradas ahora."""
        assert len(GENERIC_ERRORS) == 4
        assert "filament_runout" in GENERIC_ERRORS
        assert "sd_card_error" in GENERIC_ERRORS

    def test_new_errors_present_in_sidewinder_kb(self):
        expected_new = [
            "bltouch_probe_error",
            "tmc_driver_noise",
            "hotend_ptfe_degradation",
            "tft_display_error",
            "psu_failure",
        ]
        for err in expected_new:
            assert err in SIDEWINDER_X1_ERRORS, f"Missing: {err}"

    def test_knowledge_base_summary_lists_all_errors(self):
        result = knowledge_base_summary()
        for error_id in SIDEWINDER_X1_ERRORS:
            assert error_id in result

    def test_knowledge_base_summary_shows_printer_model(self):
        result = knowledge_base_summary()
        assert "sidewinder" in result.lower() or "printer" in result.lower()


# ── Tests: serial port listing (mocked) ──────────────────────────────────────

class TestSerialPorts:

    def test_list_serial_ports_mocked(self):
        """Test list_serial_ports with a mocked serial port list."""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "CH340 USB Serial"
        mock_port.manufacturer = "wch.cn"
        mock_port.hwid = "USB VID:PID=1A86:7523"

        with patch("serial.tools.list_ports.comports", return_value=[mock_port]):
            from repetier_mcp.server import list_serial_ports
            result = list_serial_ports()
            assert "/dev/ttyUSB0" in result
            assert "CH340" in result

    def test_list_serial_ports_empty(self):
        with patch("serial.tools.list_ports.comports", return_value=[]):
            from repetier_mcp.server import list_serial_ports
            result = list_serial_ports()
            assert "No serial ports" in result or "not found" in result.lower()


# ── Tests: temperature parsing helpers ───────────────────────────────────────

class TestTemperatureParsing:

    def test_parse_m105_response(self):
        """Verify temperature parsing logic from M105 response."""
        # Typical Marlin M105 response
        line = "ok T:205.3 /200.0 B:59.8 /60.0 T0:205.3 /200.0 @:0 B@:0"
        hotend, bed = None, None
        parts = line.split()
        for part in parts:
            if part.startswith("T:"):
                vals = part[2:].split("/")
                hotend = float(vals[0])
            elif part.startswith("B:"):
                vals = part[2:].split("/")
                bed = float(vals[0])
        assert hotend == pytest.approx(205.3)
        assert bed == pytest.approx(59.8)
