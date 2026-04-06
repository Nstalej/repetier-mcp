# repetier-mcp

**Servidor MCP para Repetier-Host / Repetier-Server -- monitorea, controla y diagnostica tu impresora 3D con IA.**

Conecta Claude (o cualquier IA compatible con MCP) directamente a tu impresora 3D.
Obtiene lecturas de temperatura en tiempo real, progreso de impresion, diagnostico
inteligente de errores y guias de reparacion especificas para tu modelo -- incluyendo
una base de datos integrada para la **Artillery Sidewinder X1**.

> [English](../README.md) | Espanol

---

## Que puedes hacer

| Dile a Claude...                                    | Que sucede                                              |
|-----------------------------------------------------|---------------------------------------------------------|
| "Cual es la temperatura de la impresora?"           | Devuelve temps del hotend y cama en tiempo real         |
| "Mi impresora tiene problemas de layer shifting"    | Diagnostica causas y da guia de reparacion paso a paso  |
| "Envia M503 para leer la configuracion actual"      | Envia G-code y devuelve los valores del EEPROM          |
| "Sube e imprime benchy.gcode"                       | Sube archivo al servidor e inicia la impresion          |
| "Pausa la impresion"                                | Pausa el trabajo actual via Repetier-Server             |
| "Pon la cama a 60 grados"                           | Configura la cama caliente a 60C                        |
| "En que puerto esta mi impresora?"                  | Escanea puertos serie y auto-detecta la impresora       |

---

## Instalacion rapida

### Instalar desde GitHub

```bash
pip install git+https://github.com/Nstalej/repetier-mcp.git
```

O con `uv` (recomendado -- mas rapido y sin conflictos):

```bash
pip install uv
uv pip install git+https://github.com/Nstalej/repetier-mcp.git
```

Para **modo serial** (USB directo), tambien instalar pyserial:

```bash
pip install "repetier-mcp[serial] @ git+https://github.com/Nstalej/repetier-mcp.git"
```

Para desarrollo:

```bash
git clone https://github.com/Nstalej/repetier-mcp.git
cd repetier-mcp
pip install -e ".[dev]"
pytest
```

---

## Modos de Conexion

repetier-mcp soporta dos modos de conexion:

### Modo 1: Repetier-Server (recomendado)

Se conecta via HTTP REST API a Repetier-Server corriendo en tu red local.
Soporta todas las funciones incluyendo subida de archivos, pausa/reanudar y gestion de trabajos.

### Modo 2: Serial directo (USB)

Se conecta directamente a la impresora via puerto USB/serie (pyserial).
Modo clasico para usuarios de Repetier-Host. Requiere el extra `serial`.

---

## Configuracion

### Modo Repetier-Server

| Variable                 | Default                    | Descripcion                            |
|--------------------------|----------------------------|----------------------------------------|
| `REPETIER_MODE`          | `serial`                   | Cambiar a `server`                     |
| `REPETIER_SERVER_URL`    | `http://localhost:3344`    | URL completa de Repetier-Server        |
| `REPETIER_SERVER_APIKEY` | *(vacio)*                  | API key de Repetier-Server             |
| `REPETIER_PRINTER_SLUG`  | *(vacio)*                  | Slug/nombre de la impresora en server  |
| `PRINTER_MODEL`          | `sidewinder_x1`            | Modelo para diagnosticos               |

### Modo USB directo / serie

| Variable          | Default          | Descripcion                                            |
|-------------------|------------------|--------------------------------------------------------|
| `REPETIER_MODE`   | `serial`         | Modo de conexion: `serial` o `server`                  |
| `REPETIER_PORT`   | *(auto)*         | Puerto serie, ej. `COM3` o `/dev/ttyUSB0`             |
| `REPETIER_BAUD`   | `115200`         | Velocidad -- **usar `250000` para Sidewinder X1**      |
| `PRINTER_MODEL`   | `sidewinder_x1`  | Modelo de impresora para diagnosticos                  |

> **Auto-deteccion:** Si `REPETIER_SERVER_URL` esta definida y `REPETIER_MODE` no,
> el modo server se selecciona automaticamente.

---

## Configurar Claude Desktop

### Windows

Abre el archivo de configuracion en:
```
C:\Users\TU_USUARIO\AppData\Roaming\Claude\claude_desktop_config.json
```

**Modo servidor (recomendado):**

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":          "server",
        "REPETIER_SERVER_URL":    "http://localhost:3344",
        "REPETIER_SERVER_APIKEY": "TU_API_KEY_AQUI",
        "REPETIER_PRINTER_SLUG":  "SidewinderX1",
        "PRINTER_MODEL":          "sidewinder_x1"
      }
    }
  }
}
```

**Modo serial:**

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

Reinicia Claude Desktop.

---

### Linux

```bash
pip install "git+https://github.com/Nstalej/repetier-mcp.git"
# Para modo serial:
# pip install "repetier-mcp[serial] @ git+https://github.com/Nstalej/repetier-mcp.git"
# sudo usermod -a -G dialout $USER  # luego cierra sesion y vuelve a entrar
```

Edita `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "repetier": {
      "command": "python3",
      "args": ["-m", "repetier_mcp.server"],
      "env": {
        "REPETIER_MODE":          "server",
        "REPETIER_SERVER_URL":    "http://localhost:3344",
        "REPETIER_SERVER_APIKEY": "TU_API_KEY_AQUI",
        "REPETIER_PRINTER_SLUG":  "SidewinderX1",
        "PRINTER_MODEL":          "sidewinder_x1"
      }
    }
  }
}
```

---

## Solucion de problemas (Windows)

| Problema | Solucion |
|---|---|
| Impresora no aparece en Admin. de dispositivos | Prueba otro cable USB -- muchos cables solo cargan |
| Driver CH340 faltante | Instalar desde [wch-ic.com](http://www.wch-ic.com/downloads/CH341SER_EXE.html) |
| Puerto ocupado / acceso denegado | Cierra Repetier-Host -- no pueden usar el mismo puerto |
| No conecta al servidor | Verifica que Repetier-Server esta corriendo y la URL/puerto son correctos |
| Error de API key | Verifica que REPETIER_SERVER_APIKEY coincide con la clave en Repetier-Server |
| Slug de impresora no encontrado | Verifica que REPETIER_PRINTER_SLUG coincide con el nombre en Repetier-Server |

---

## Herramientas disponibles

| Herramienta              | Modo   | Descripcion                                                |
|--------------------------|--------|------------------------------------------------------------|
| `printer_status`         | Ambos  | Temperaturas, progreso de impresion y posicion             |
| `send_gcode`             | Ambos  | Envia cualquier comando G-code / M-code                   |
| `temperature_check`      | Ambos  | Analisis de estabilidad termica con multiples muestras     |
| `set_temperature`        | Ambos  | Configura temperatura del hotend o cama                    |
| `list_jobs`              | Server | Lista la cola de impresion                                 |
| `upload_and_print`       | Server | Sube archivo .gcode e inicia impresion                     |
| `pause_print`            | Server | Pausa el trabajo de impresion actual                       |
| `resume_print`           | Server | Reanuda un trabajo pausado                                 |
| `cancel_print`           | Server | Cancela/detiene la impresion actual                        |
| `diagnose_error`         | Ambos  | Diagnostico con IA y guia de reparacion paso a paso        |
| `knowledge_base_summary` | Ambos  | Muestra todos los tipos de error conocidos                 |
| `list_serial_ports`      | Ambos  | Escanea puertos serie o muestra info del servidor          |
| `emergency_stop`         | Ambos  | Envia parada de emergencia M112                            |

---

## Base de diagnostico -- Artillery Sidewinder X1

Base de datos integrada con **11 tipos de error** especificos del modelo:

| Error                    | Sintomas clave                                          |
|--------------------------|---------------------------------------------------------|
| `thermal_runaway`        | THERMAL RUNAWAY, Heating failed, sensor de temperatura  |
| `layer_shifting`         | Capas desplazadas, pasos perdidos                       |
| `z_offset_drift`         | Primera capa, nivelacion de cama                        |
| `extruder_clicking`      | Click, grinding, sub-extrusion                          |
| `communication_error`    | Impresora offline, sin respuesta, timeout               |
| `bed_adhesion`           | Warping, no pega, esquinas levantadas                   |
| `bltouch_probe_error`    | BLTouch alarm, probe deploy fallido                     |
| `tmc_driver_noise`       | Ruido en motores, TMC2208 silbido                       |
| `hotend_ptfe_degradation`| Olor a quemado, PTFE, heat creep, atascos repetidos     |
| `tft_display_error`      | Pantalla congelada, pantalla blanca, TFT                |
| `psu_failure`            | Apagado aleatorio, impresora muere, fuente de poder     |

Mas **4 errores genericos** (mintemp, maxtemp, filament_runout, sd_card_error).

---

## Referencia API REST de Repetier-Server

El modo servidor usa la API REST de Repetier-Server:

```
GET  /printer/api/{slug}?a=stateList&apikey={key}           # Estado completo
GET  /printer/api/{slug}?a=send&data={"cmd":"G28"}&apikey={key}  # Enviar G-code
GET  /printer/api/{slug}?a=listJobs&apikey={key}             # Listar trabajos
GET  /printer/api/{slug}?a=pause&apikey={key}                # Pausar impresion
GET  /printer/api/{slug}?a=continueJob&apikey={key}          # Reanudar impresion
GET  /printer/api/{slug}?a=stopJob&apikey={key}              # Cancelar impresion
POST /printer/job/{slug}?a=upload&name=file.gcode&apikey={key}   # Subir gcode
```

---

## Roadmap

- [ ] Compatibilidad con OctoPrint
- [ ] Soporte para Klipper / Moonraker
- [ ] Integracion con camara webcam
- [ ] Prediccion de tiempo de impresion
- [ ] Seguimiento de uso de filamento
- [ ] Asistente de calibracion EEPROM para Sidewinder X1

---

## Contribuir

Issues y PRs son bienvenidos. Especialmente:
- Nuevos modelos de impresora para la base de diagnostico
- Adaptador para Klipper / Moonraker

```bash
git clone https://github.com/Nstalej/repetier-mcp
cd repetier-mcp
pip install -e ".[dev]"
pytest
```

---

## Licencia

MIT -- Ver [LICENSE](../LICENSE)
