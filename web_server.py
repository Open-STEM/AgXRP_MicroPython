#!/usr/bin/env python
#-------------------------------------------------------------------------------
# web_server.py
#
# Config-driven AgXRP sensor kit, web dashboard, and configuration page.
# All hardware configuration is read from config.json.
#-------------------------------------------------------------------------------

import json
import time
import uasyncio
try:
    from machine import RTC as _MachineRTC
    _HAS_RTC = True
except ImportError:
    _HAS_RTC = False
from AgXRPLib.agxrp_sensor_kit import AgXRPSensorKit
from AgXRPLib.agxrp_web_dashboard import AgXRPWebDashboard
from AgXRPLib.agxrp_web_configure import AgXRPWebConfigure
from AgXRPLib.agxrp_web_data_viewer import AgXRPWebDataViewer
from AgXRPLib.agxrp_controller import AgXRPController


CONFIG_VERSION = 2

def load_config(path="config.json"):
    """Load configuration from JSON file."""
    with open(path, "r") as f:
        cfg = json.load(f)
    version = cfg.get("config_version", 1)
    if version < CONFIG_VERSION:
        print(f"WARNING: config.json version {version} is older than expected {CONFIG_VERSION}. Some settings may use defaults.")
    return cfg


def setup_sensors(agxrp, cfg):
    """Register sensors based on config."""
    sensors_cfg = cfg["sensors"]

    # Soil sensors first (order matters — they need a clean bus)
    for soil_cfg in sensors_cfg.get("soil", []):
        if not soil_cfg.get("enabled", False):
            continue
        address = int(soil_cfg["address"], 16) if isinstance(soil_cfg["address"], str) else soil_cfg["address"]
        if soil_cfg.get("type", "capacitive") == "resistive":
            agxrp.register_resistive_soil_sensor(
                soil_cfg["sensor_index"],
                bus=soil_cfg.get("bus", 0),
                address=address
            )
        else:
            agxrp.register_soil_sensor(
                soil_cfg["sensor_index"],
                bus=soil_cfg.get("bus", 0),
                address=address
            )

    # CO2 sensor (SCD4x)
    if sensors_cfg.get("co2", {}).get("enabled", False):
        agxrp.register_co2_sensor(bus=sensors_cfg["co2"].get("bus", 0))

    # Spectral sensor (AS7343)
    if sensors_cfg.get("spectral", {}).get("enabled", False):
        agxrp.register_spectral_sensor(bus=sensors_cfg["spectral"].get("bus", 0))

    # Light sensor (VEML)
    if sensors_cfg.get("light", {}).get("enabled", False):
        agxrp.register_light_sensor(bus=sensors_cfg["light"].get("bus", 0))

    # OLED screen
    if sensors_cfg.get("screen", {}).get("enabled", False):
        agxrp.register_screen(bus=sensors_cfg["screen"].get("bus", 0))

    # CSV logger
    csv_cfg = sensors_cfg.get("csv_logger", {})
    if csv_cfg.get("enabled", False):
        period_ms = int(csv_cfg.get("period_hours", 1.0) * 3600000)
        agxrp.register_csv_logger(
            csv_cfg.get("filename", "sensor_log.csv"),
            period_ms,
            max_rows=csv_cfg.get("max_rows", 0)
        )


def setup_controller(agxrp, cfg):
    """Create and configure controller based on config. Returns controller or None."""
    ctrl_cfg = cfg.get("controller", {})
    if not ctrl_cfg.get("enabled", False):
        return None

    controller = AgXRPController(agxrp)

    # Register pumps — pump_index is fixed by array position (Motor L=1, Motor R=2, Motor 3=3, Motor 4=4)
    for i, pump_cfg in enumerate(ctrl_cfg.get("pumps", [])):
        if not pump_cfg.get("enabled", True):
            continue
        controller.register_water_pump(
            i + 1,
            csv_filename=pump_cfg.get("csv_filename"),
            max_duration_seconds=pump_cfg.get("max_duration_seconds", 60.0)
        )

    # Register plant systems — pump_index is fixed by array position
    for i, ps_cfg in enumerate(ctrl_cfg.get("plant_systems", [])):
        if not ps_cfg.get("enabled", False):
            continue
        controller.register_plant_system(
            sensor_index=ps_cfg["sensor_index"],
            pump_index=i + 1,
            interval_hours=ps_cfg.get("interval_hours", ps_cfg.get("interval_minutes", 30.0) / 60.0),
            threshold=ps_cfg["threshold"],
            duration_seconds=ps_cfg["duration_seconds"],
            enabled=ps_cfg.get("enabled", True),
            pump_effort=ps_cfg.get("pump_effort", 1.0),
            hysteresis=ps_cfg.get("hysteresis", 0.0)
        )

    controller.start_control_loop()
    print("Controller started with automatic watering enabled")
    return controller


def setup_webserver_display(dashboard, cfg):
    """Auto-register dashboard display elements based on enabled sensors."""
    sensors_cfg = cfg.get("sensors", {})

    # CO2 sensor provides temperature, humidity, and co2
    if sensors_cfg.get("co2", {}).get("enabled", False):
        dashboard.register_temperature()
        dashboard.register_humidity()
        dashboard.register_co2()

    # Spectral sensor provides blue, green, red, nir
    if sensors_cfg.get("spectral", {}).get("enabled", False):
        dashboard.register_blue_light()
        dashboard.register_green_light()
        dashboard.register_red_light()
        dashboard.register_nir_light()

    # Light sensor provides light intensity
    if sensors_cfg.get("light", {}).get("enabled", False):
        dashboard.register_light_intensity()

    # Soil sensors by index
    soil_register = {
        1: dashboard.register_soil_moisture_sensor_1,
        2: dashboard.register_soil_moisture_sensor_2,
    }
    for soil_cfg in sensors_cfg.get("soil", []):
        if soil_cfg.get("enabled", False):
            register_fn = soil_register.get(soil_cfg["sensor_index"])
            if register_fn:
                register_fn(sensor_type=soil_cfg.get("type", "capacitive"))


def init_rtc_from_log(cfg):
    """Set RTC to the most recent timestamp found in sensor log files."""
    if not _HAS_RTC:
        return
    filename = cfg.get("sensors", {}).get("csv_logger", {}).get("filename", "sensor_log.csv")
    candidates = [filename, filename + ".bak"]
    best_dt_str = None
    for path in candidates:
        try:
            last_line = None
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
            if last_line is None:
                continue
            first_col = last_line.split(",")[0]
            if len(first_col) != 19 or first_col == "datetime":
                continue
            if best_dt_str is None or first_col > best_dt_str:
                best_dt_str = first_col
        except OSError:
            pass
        except Exception as e:
            print(f"Warning: could not read log file {path}: {e}")
    if best_dt_str is None:
        print("RTC: No log file found — RTC not initialized from log")
        return
    try:
        year   = int(best_dt_str[0:4])
        month  = int(best_dt_str[5:7])
        day    = int(best_dt_str[8:10])
        hour   = int(best_dt_str[11:13])
        minute = int(best_dt_str[14:16])
        second = int(best_dt_str[17:19])
        if not (2020 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31):
            print(f"RTC: Invalid log datetime '{best_dt_str}' — skipping")
            return
        _MachineRTC().datetime((year, month, day, 0, hour, minute, second, 0))
        print(f"RTC: Initialized from log: {best_dt_str}")
    except Exception as e:
        print(f"RTC: Failed to set from log '{best_dt_str}': {e}")


def main():
    """Config-driven main entry point."""
    cfg = load_config()
    init_rtc_from_log(cfg)
    USE_RANDOM_DATA = cfg.get("use_random_data", False)

    print("Initializing AgXRP Sensor Kit, Controller, and Web Dashboard...")

    agxrp = None
    controller = None

    if not USE_RANDOM_DATA:
        # Initialize sensor kit
        sk_cfg = cfg.get("sensor_kit", {})
        agxrp = AgXRPSensorKit(
            bus0_enabled=sk_cfg.get("bus0_enabled", True),
            bus1_enabled=sk_cfg.get("bus1_enabled", False),
            i2c_freq=sk_cfg.get("i2c_freq", 100000)
        )

        # Register sensors
        setup_sensors(agxrp, cfg)

        # Initial update to stabilize sensors
        agxrp.update()
        time.sleep(2)
        agxrp.update()

        # Setup controller (pumps + plant systems)
        controller = setup_controller(agxrp, cfg)

    # Create and configure web dashboard
    dashboard = AgXRPWebDashboard(config_path="config.json")

    if controller:
        dashboard.register_controller(controller)

    setup_webserver_display(dashboard, cfg)

    # Register configuration and data viewer routes (must be before dashboard's catchall)
    configurator = AgXRPWebConfigure(config_path="config.json", controller=controller)
    configurator.register_routes()

    data_viewer = AgXRPWebDataViewer(config_path="config.json")
    data_viewer.register_routes()

    # Start access point
    ap_cfg = cfg.get("webserver", {}).get("access_point", {})
    ssid = ap_cfg.get("ssid", "AgXRP_SensorKit")
    password = ap_cfg.get("password", "sensor123")

    if not dashboard.start_access_point(ssid=ssid, password=password, use_random_data=USE_RANDOM_DATA):
        print("ERROR: Failed to start access point")
        return

    print(f"Access point started. Connect to '{ssid}' and visit http://{dashboard.get_ip_address()}")

    # Start web server
    print("Starting web server...")
    print("Press Ctrl+C to stop")

    update_interval = cfg.get("sensor_update_interval_seconds", 2)

    try:
        if USE_RANDOM_DATA:
            dashboard.run()
        else:
            async def update_sensors():
                while True:
                    agxrp.update()
                    data = {}
                    if agxrp.co2_sensor and agxrp.co2_sensor.is_connected():
                        data["temperature"] = agxrp.co2_sensor.get_temperature()
                        data["humidity"] = agxrp.co2_sensor.get_humidity()
                        data["co2"] = agxrp.co2_sensor.get_co2()
                    if agxrp.spectral_sensor and agxrp.spectral_sensor.is_connected():
                        data["blue_light"] = agxrp.spectral_sensor.get_blue()
                        data["green_light"] = agxrp.spectral_sensor.get_green()
                        data["red_light"] = agxrp.spectral_sensor.get_red()
                        data["nir_light"] = agxrp.spectral_sensor.get_nir()
                    if agxrp.light_sensor and agxrp.light_sensor.is_connected():
                        data["light_intensity"] = agxrp.light_sensor.get_ambient_light()
                    for idx in agxrp.soil_sensors:
                        sensor = agxrp.soil_sensors[idx]
                        if sensor and sensor.is_connected():
                            data[f"soil_moisture_{idx}"] = sensor.get_moisture()
                    dashboard.update_sensor_data(data)
                    await uasyncio.sleep(update_interval)

            loop = uasyncio.get_event_loop()
            loop.create_task(update_sensors())
            dashboard.run()

    except KeyboardInterrupt:
        print("\nShutting down...")
        if controller:
            controller.stop_control_loop()
            print("Controller stopped")
        if agxrp:
            print("Sensor kit stopped")
        print("Web server stopped")


if __name__ == "__main__":
    main()
