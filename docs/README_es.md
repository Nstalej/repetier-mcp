# repetier-mcp 🖨️

**Servidor MCP para Repetier-Host / Repetier-Server — monitorea, controla y diagnostica tu impresora 3D con IA.**

Conecta Claude (o cualquier IA compatible con MCP) directamente a tu impresora 3D.
Obtén lecturas de temperatura en tiempo real, progreso de impresión, diagnóstico
inteligente de errores y guías de reparación específicas para tu modelo — incluyendo
una base de datos integrada para la **Artillery Sidewinder X1**.

> [🇬🇧 English](../README.md) | 🇪🇸 Español

---

## ✨ Qué puedes hacer

| Dile a Claude...                                    | Qué sucede                                              |
|-----------------------------------------------------|---------------------------------------------------------|
| "¿Cuál es la temperatura de la impresora?"          | Devuelve temps del hotend y cama en tiempo real         |
| "Mi impresora tiene problemas de layer shifting"    | Diagnostica causas y da guía de reparación paso a paso  |
| "Envía M503 para leer la configuración actual"      | Envía G-code y devuelve los valores del EEPROM          |
| "Verifica si las temperaturas son estables"         | Toma 5 lecturas en 10s y detecta inestabilidad          |
| "¿En qué puerto está mi impresora?"                 | Escanea puertos serie y auto-detecta la impresora       |

---

## 🚀 Instalación rápida

### Windows

#### Paso 1 — Instalar Python

Descarga Python 3.10 o superior desde [python.org/downloads](https://www.python.org/downloads/).

> ⚠️ **Importante:** durante la instalación, marca la casilla **"Add Python to PATH"**.

Verifica en PowerShell o CMD:
```
python --version
```

#### Paso 2 — Instalar repetier-mcp

Abre PowerShell o CMD y ejecuta:

```powershell
pip install repetier-mcp
```

O con `uv` (recomendado — más rápido y sin conflictos de dependencias):

```powershell
pip install uv
uv tool install repetier-mcp
```

#### Paso 3 — Encontrar el puerto COM de tu impresora

1. Conecta la impresora por USB
2. Abre el **Administrador de dispositivos** (`Win + X` → Administrador de dispositivos)
3. Expande **Puertos (COM y LPT)**
4. Busca algo como `USB-SERIAL CH340 (COM3)` o `Silicon Labs CP210x (COM4)`
5. Anota el número de puerto, por ejemplo `COM3`

> **Tip Sidewinder X1:** El chip USB es CH340. Si no aparece, descarga el driver desde [wch-ic.com/downloads/CH341SER_EXE.html](http://www.wch-ic.com/downloads/CH341SER_EXE.html)

#### Paso 4 — Configurar Claude Desktop

Abre el archivo de configuración en:
```
C:\Users\TU_USUARIO\AppData\Roaming\Claude\claude_desktop_config.json
```

> Si no existe, créalo. Puedes abrirlo con el Bloc de notas o VS Code.

Agrega esta configuración (reemplaza `COM3` con tu puerto):

```json
{
  "mcpServers": {
    "repetier": {
      "command": "uvx",
      "args": ["repetier-mcp"],
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

> **Sidewinder X1:** usa siempre `"REPETIER_BAUD": "250000"`.  
> Si la conexión falla con 250000, prueba `"115200"` como segunda opción.

Reinicia Claude Desktop. ¡Listo! 🎉

---

### Linux

#### Paso 1 — Instalar repetier-mcp

```bash
pip install repetier-mcp
# o con uv:
pip install uv
uv tool install repetier-mcp
```

#### Paso 2 — Permisos del puerto serie

En Linux es necesario agregar tu usuario al grupo `dialout`:

```bash
sudo usermod -a -G dialout $USER
```

Luego **cierra sesión y vuelve a entrar** para que el cambio tenga efecto.

#### Paso 3 — Encontrar el puerto

```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Resultado típico: /dev/ttyUSB0
```

#### Paso 4 — Configurar Claude Desktop

Edita `~/.config/Claude/claude_desktop_config.json` (Linux) o
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

Reinicia Claude Desktop. 🎉

---

## 🛠️ Herramientas disponibles

| Herramienta              | Descripción                                                      |
|--------------------------|------------------------------------------------------------------|
| `printer_status`         | Temperaturas, progreso de impresión y posición actual            |
| `send_gcode`             | Envía cualquier comando G-code / M-code                         |
| `temperature_check`      | Análisis de estabilidad térmica con múltiples muestras           |
| `list_jobs`              | Lista la cola de impresión (modo Repetier-Server)               |
| `diagnose_error`         | Diagnóstico con IA y guía de reparación paso a paso             |
| `knowledge_base_summary` | Muestra todos los tipos de error conocidos y sus síntomas        |
| `list_serial_ports`      | Escanea y auto-detecta el puerto de la impresora                |
| `emergency_stop`         | Envía parada de emergencia M112                                  |

---

## ⚙️ Configuración

### USB directo / serie (Repetier-Host)

| Variable          | Valor por defecto | Descripción                                            |
|-------------------|-------------------|--------------------------------------------------------|
| `REPETIER_MODE`   | `serial`          | Modo de conexión: `serial` o `server`                  |
| `REPETIER_PORT`   | *(auto)*          | Puerto serie, ej. `COM3` (Windows) o `/dev/ttyUSB0`   |
| `REPETIER_BAUD`   | `115200`          | Velocidad — **usar `250000` para Sidewinder X1**       |
| `PRINTER_MODEL`   | `sidewinder_x1`   | Modelo de impresora para diagnósticos dirigidos         |

### Repetier-Server (red local)

| Variable              | Valor por defecto | Descripción                              |
|-----------------------|-------------------|------------------------------------------|
| `REPETIER_MODE`       | `server`          | Cambiar a `server`                       |
| `REPETIER_HOST`       | `localhost`       | IP o hostname del Repetier-Server        |
| `REPETIER_HTTP_PORT`  | `3344`            | Puerto del servidor (default 3344)       |
| `REPETIER_API_KEY`    | *(vacío)*         | API key si la autenticación está activa  |
| `REPETIER_PRINTER`    | *(vacío)*         | Slug/nombre de la impresora en el server |

---

## 🔍 Base de diagnóstico — Artillery Sidewinder X1

Base de datos integrada con 11 tipos de error específicos del modelo:

| Error                    | Síntomas clave                                          |
|--------------------------|---------------------------------------------------------|
| `thermal_runaway`        | THERMAL RUNAWAY, Heating failed, sensor de temperatura  |
| `layer_shifting`         | Capas desplazadas, pasos perdidos                       |
| `z_offset_drift`         | Primera capa, nivelación de cama                        |
| `extruder_clicking`      | Click, grinding, sub-extrusión                          |
| `communication_error`    | Impresora offline, sin respuesta, timeout               |
| `bed_adhesion`           | Warping, no pega, esquinas levantadas                   |
| `bltouch_probe_error`    | BLTouch alarm, probe deploy fallido                     |
| `tmc_driver_noise`       | Ruido en motores, TMC2208 silbido                       |
| `hotend_ptfe_degradation`| Olor a quemado, PTFE, heat creep, atascos repetidos     |
| `tft_display_error`      | Pantalla congelada, pantalla blanca, TFT                |
| `psu_failure`            | Apagado aleatorio, impresora muere, fuente de poder     |

**Ejemplo de uso:** dile a Claude *"Mi impresora tiene un clic en el extrusor"*
→ `diagnose_error("extruder clicking")` → análisis completo de causas y pasos de reparación con los G-codes exactos.

---

## 🐛 Solución de problemas comunes en Windows

### La impresora no aparece en el Administrador de dispositivos
- Prueba con un cable USB diferente — muchos cables solo cargan, no transmiten datos
- Instala el driver CH340: [wch-ic.com/downloads/CH341SER_EXE.html](http://www.wch-ic.com/downloads/CH341SER_EXE.html)
- Prueba otro puerto USB físico en tu PC

### Claude no puede conectar aunque el puerto es correcto
- Verifica que Repetier-Host esté **cerrado** — no pueden usar el mismo puerto a la vez
- Desactiva la administración de energía del puerto USB:
  `Administrador de dispositivos → Concentradores USB → Propiedades → Administración de energía → desmarcar "permitir suspensión"`
- Reduce el cache de recepción: agrega `"REPETIER_TIMEOUT": "5"` a las variables de entorno

### Error "command not found: uvx"
```powershell
pip install uv
# luego cierra y vuelve a abrir PowerShell
uvx --version
```

### El baud rate correcto para la Sidewinder X1
El firmware stock de Artillery usa **250000 baud**. Si con 250000 ves el error `1 Commands Waiting` en Repetier-Host, el baud está mal configurado. Prueba también `115200` si 250000 no funciona en tu configuración específica.

---

## 📦 Parte del ecosistema maker-mcp

Este servidor se combina con **[openscad-mcp](https://github.com/Nstalej/openscad-mcp)**
para un flujo completo diseño → impresión:

```
Claude  →  openscad-mcp  →  diseña .scad → exporta .stl
                                               ↓
        →  repetier-mcp  →  impresora → monitoreo → diagnóstico
```

O instala **[maker-mcp-suite](https://github.com/Nstalej/maker-mcp-suite)**
para tener todo en un solo servidor.

---

## 🗺️ Roadmap

- [ ] Compatibilidad con OctoPrint
- [ ] Soporte para Klipper / Moonraker
- [ ] Integración con cámara webcam
- [ ] Predicción de tiempo de impresión
- [ ] Seguimiento de uso de filamento
- [ ] Asistente de calibración EEPROM para Sidewinder X1

---

## 🤝 Contribuir

Issues y PRs son bienvenidos. Especialmente:
- Nuevos modelos de impresora para la base de diagnóstico
- Adaptador para Klipper / Moonraker

```bash
git clone https://github.com/Nstalej/repetier-mcp
cd repetier-mcp
pip install -e ".[dev]"
pytest
```

---

## 📄 Licencia

MIT © 2025 — Ver [LICENSE](../LICENSE)
