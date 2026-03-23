# AgXRP Sensor Kit Firmware

MicroPython firmware for the AgXRP — an automated plant monitoring and watering system built on the XRP (eXtensible Robot Platform) board. It monitors soil moisture and environmental conditions, logs data to CSV, and automatically controls peristaltic water pumps, all accessible through a local web dashboard.

---

## Features

- **Real-time sensor monitoring** — CO2, temperature, humidity, ambient light, spectral light, soil moisture
- **Automatic watering** — configurable thresholds, hysteresis, and intervals per plant/pump pair
- **Web dashboard** — live sensor readings and manual pump control at `http://192.168.4.1`
- **Web configuration** — edit all settings in the browser without touching code
- **Data logging** — periodic CSV sensor logs with automatic rotation; per-pump activity logs
- **RTC synchronization** — clock set from log file at boot, then synced precisely from the browser's local time when the dashboard is opened
- **OLED display** — rotating pages of sensor readings on an attached screen

---

## Hardware

- **Board:** XRP (RP2350-based)
- **I2C Bus 0:** SDA=GPIO4, SCL=GPIO5
- **I2C Bus 1:** SDA=GPIO38, SCL=GPIO39

### Supported Sensors

| Sensor | Type | Interface |
|--------|------|-----------|
| SCD4x | CO2, temperature, humidity | I2C (Qwiic) |
| AS7343 | 16-channel spectral (blue/green/red/NIR) | I2C (Qwiic) |
| VEML | Ambient light intensity | I2C (Qwiic) |
| CY8CMBR3 | Capacitive soil moisture (up to 4) | I2C (Qwiic) |
| Resistive soil | Soil moisture % (up to 4) | I2C (Qwiic) |
| Qwiic OLED | Display (micro or large) | I2C (Qwiic) |

Water pumps connect to the XRP motor outputs (encoded motor channels 1–4).

---

## Getting Started

### 1. Flash MicroPython

Flash the RP2350 MicroPython firmware to the board. See the [MicroPython docs](https://micropython.org/download/) for instructions.

### 2. Deploy Files

Copy the firmware files to the board's filesystem using `mpremote`:

```bash
# Copy library and main script
mpremote fs cp -r lib :lib + fs cp config.json :config.json + fs cp web_server.py :web_server.py
```

To run automatically on boot, also copy as `main.py`:

```bash
mpremote fs cp web_server.py :main.py
```

### 3. Configure

Edit `config.json` to match your hardware before deploying, or use the web configuration page after the first boot (see below).

### 4. Run

```bash
mpremote exec "exec(open('web_server.py').read())"
```

Or simply reset the board if `main.py` is installed.

---

## Web Interface

Connect to the WiFi access point:

- **SSID:** `AgXRP_SensorKit` (default)
- **Password:** `sensor123` (default)

Then open a browser to **http://192.168.4.1**

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Live sensor readings, manual pump control, plant system status |
| Configuration | `/configure` | Edit all settings, reboot device |
| Data Viewer | `/data` | Browse and download CSV log files |

When the dashboard loads, it automatically syncs the device's RTC to your browser's local time, so all log timestamps are accurate.

---

## Configuration

All settings live in `config.json`. Key sections:

```jsonc
{
  "sensor_kit": {
    "bus0_enabled": true,       // I2C bus 0 (GPIO4/5)
    "bus1_enabled": true,       // I2C bus 1 (GPIO38/39)
    "i2c_freq": 100000
  },
  "sensors": {
    "co2":      { "enabled": true,  "bus": 0 },
    "spectral": { "enabled": false, "bus": 0 },
    "light":    { "enabled": true,  "bus": 0 },
    "screen":   { "enabled": true,  "bus": 0 },
    "soil": [
      { "enabled": true, "type": "capacitive", "sensor_index": 1, "bus": 1, "address": "0x37" }
    ],
    "csv_logger": { "enabled": false, "filename": "sensor_log.csv", "period_ms": 5000, "max_rows": 5000 }
  },
  "controller": {
    "enabled": true,
    "pumps": [
      { "enabled": true, "pump_index": 1, "csv_filename": "water_pump_1_log.csv", "max_duration_seconds": 60.0 }
    ],
    "plant_systems": [
      {
        "enabled": true,
        "sensor_index": 1,   // which soil sensor to watch
        "pump_index": 1,     // which pump to trigger
        "interval_hours": 0.5,
        "threshold": 300.0,  // water when reading exceeds this (pF for capacitive)
        "hysteresis": 20.0,  // don't re-trigger until reading drops this much below threshold
        "duration_seconds": 3.0,
        "pump_effort": 1.0   // 0.0–1.0
      }
    ]
  },
  "webserver": {
    "access_point": { "ssid": "AgXRP_SensorKit", "password": "sensor123" }
  },
  "sensor_update_interval_seconds": 2
}
```

All settings can also be edited live through the `/configure` web page — no file editing required.

---

## Project Structure

```
updated_firmware/
├── config.json                         # Hardware and control configuration
├── web_server.py                       # Main entry point
└── lib/
    ├── AgXRPLib/                       # AgXRP application library
    │   ├── agxrp_sensor_kit.py         # Sensor coordinator
    │   ├── agxrp_sensor_*.py           # Individual sensor wrappers
    │   ├── agxrp_water_pump.py         # Pump control and logging
    │   ├── agxrp_controller.py         # Automatic watering control loop
    │   ├── agxrp_csv_logger.py         # Periodic CSV data logging
    │   ├── agxrp_web_dashboard.py      # Web dashboard and API routes
    │   ├── agxrp_web_configure.py      # Web configuration page
    │   ├── agxrp_web_data_viewer.py    # CSV log viewer and download
    │   └── qwiic_*/                    # Hardware drivers (Qwiic sensors, OLED)
    ├── XRPLib/                         # XRP board drivers (motors, encoders, IMU, etc.)
    ├── phew/                           # MicroPython web framework (Pimoroni)
    ├── qwiic_i2c/                      # I2C abstraction layer
    └── ble/                            # Bluetooth UART / REPL (optional)
```

---

## Data Logging

When `csv_logger` is enabled, sensor readings are written to `sensor_log.csv` on the board filesystem at the configured interval. The file rotates to `sensor_log.csv.bak` when `max_rows` is reached.

Each pump writes a separate activity log (`water_pump_1_log.csv`, etc.) recording timestamp, revolutions, duration, and soil moisture at the time of watering.

Files can be downloaded from the `/data` page or retrieved directly with `mpremote`:

```bash
mpremote fs cp :sensor_log.csv ./sensor_log.csv
```

---

## Dependencies

All dependencies are bundled in `lib/` — no package manager or internet connection required on the device.

- **[phew](https://github.com/pimoroni/phew)** — MicroPython web framework by Pimoroni
- **XRPLib** — XRP board and motor control library
- **qwiic_i2c** — I2C abstraction layer for Qwiic sensors
