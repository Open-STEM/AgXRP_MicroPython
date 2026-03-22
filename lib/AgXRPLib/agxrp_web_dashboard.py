#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_web_dashboard.py
#
# Web dashboard for displaying sensor data and controlling pumps on Raspberry Pi Pico W.
# Provides modular sensor registration and access point mode.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import json
import random
import time
from phew import server, access_point, dns, logging
from lib.AgXRPLib.agxrp_water_pump import AgXRPWaterPump

class AgXRPWebDashboard:
    """!
    Web dashboard for displaying sensor data and controlling plant systems.

    This class provides a web interface to display sensor readings
    from AgXRPSensorKit. Sensors are registered modularly, and the server
    runs in access point mode.
    """

    def __init__(self, config_path="config.json"):
        """!
        Constructor

        @param config_path: Path to config.json for persisting settings
        """
        self._config_path = config_path

        # Sensor registration flags
        self._temperature_registered = False
        self._humidity_registered = False
        self._co2_registered = False
        self._blue_light_registered = False
        self._green_light_registered = False
        self._red_light_registered = False
        self._nir_light_registered = False
        self._light_intensity_registered = False
        self._soil_moisture_1_registered = False
        self._soil_moisture_2_registered = False
        self._soil_moisture_1_unit = "%"   # "%" for resistive, "pF" for capacitive
        self._soil_moisture_2_unit = "%"

        # Sensor data storage
        self._sensor_data = {}

        # Water pump storage: dictionary mapping pump index to AgXRPWaterPump instance
        # (kept for backward compatibility when controller is not used)
        self._water_pumps = {}

        # Controller instance (optional)
        self._controller = None

        # Access point configuration
        self._wlan = None
        self._ip_address = None
        self._use_random_data = False

        # Server state
        self._server_running = False

    def register_temperature(self):
        """!
        Register temperature sensor for display.

        @return **bool** True if registration was successful
        """
        self._temperature_registered = True
        if "temperature" not in self._sensor_data:
            self._sensor_data["temperature"] = None
        return True

    def register_humidity(self):
        """!
        Register humidity sensor for display.

        @return **bool** True if registration was successful
        """
        self._humidity_registered = True
        if "humidity" not in self._sensor_data:
            self._sensor_data["humidity"] = None
        return True

    def register_co2(self):
        """!
        Register CO2 sensor for display.

        @return **bool** True if registration was successful
        """
        self._co2_registered = True
        if "co2" not in self._sensor_data:
            self._sensor_data["co2"] = None
        return True

    def register_blue_light(self):
        """!
        Register blue light sensor for display.

        @return **bool** True if registration was successful
        """
        self._blue_light_registered = True
        if "blue_light" not in self._sensor_data:
            self._sensor_data["blue_light"] = None
        return True

    def register_green_light(self):
        """!
        Register green light sensor for display.

        @return **bool** True if registration was successful
        """
        self._green_light_registered = True
        if "green_light" not in self._sensor_data:
            self._sensor_data["green_light"] = None
        return True

    def register_red_light(self):
        """!
        Register red light sensor for display.

        @return **bool** True if registration was successful
        """
        self._red_light_registered = True
        if "red_light" not in self._sensor_data:
            self._sensor_data["red_light"] = None
        return True

    def register_nir_light(self):
        """!
        Register NIR (Near-Infrared) light sensor for display.

        @return **bool** True if registration was successful
        """
        self._nir_light_registered = True
        if "nir_light" not in self._sensor_data:
            self._sensor_data["nir_light"] = None
        return True

    def register_light_intensity(self):
        """!
        Register light intensity sensor for display.

        @return **bool** True if registration was successful
        """
        self._light_intensity_registered = True
        if "light_intensity" not in self._sensor_data:
            self._sensor_data["light_intensity"] = None
        return True

    def register_soil_moisture_sensor_1(self, sensor_type="resistive"):
        """!
        Register first soil moisture sensor for display.

        @param sensor_type: "capacitive" (returns pF) or "resistive" (returns %)
        @return **bool** True if registration was successful
        """
        self._soil_moisture_1_registered = True
        self._soil_moisture_1_unit = "pF" if sensor_type == "capacitive" else "%"
        if "soil_moisture_1" not in self._sensor_data:
            self._sensor_data["soil_moisture_1"] = None
        return True

    def register_soil_moisture_sensor_2(self, sensor_type="resistive"):
        """!
        Register second soil moisture sensor for display.

        @param sensor_type: "capacitive" (returns pF) or "resistive" (returns %)
        @return **bool** True if registration was successful
        """
        self._soil_moisture_2_registered = True
        self._soil_moisture_2_unit = "pF" if sensor_type == "capacitive" else "%"
        if "soil_moisture_2" not in self._sensor_data:
            self._sensor_data["soil_moisture_2"] = None
        return True

    def register_soil_moisture(self, sensor_type="resistive"):
        """!
        Register soil moisture sensor for display (backward compatibility).

        @return **bool** True if registration was successful
        """
        return self.register_soil_moisture_sensor_1(sensor_type=sensor_type)

    def register_controller(self, controller):
        """!
        Register an AgXRPController instance.

        @param controller: AgXRPController instance
        @type controller: AgXRPController
        @return **bool** True if registration was successful
        """
        self._controller = controller
        print("Controller registered with dashboard")
        return True

    def register_water_pump(self, pump_index: int, csv_filename: str = None):
        """!
        Register a water pump for web control.

        If a controller is registered, this delegates to the controller.
        Otherwise, it registers the pump directly (backward compatibility).

        @param pump_index: The motor index for the pump (1, 2, 3, or 4)
        @param csv_filename: Optional CSV filename for logging
        @return **bool** True if registration was successful, False otherwise
        """
        if self._controller:
            return self._controller.register_water_pump(pump_index, csv_filename)
        else:
            if pump_index in self._water_pumps:
                print(f"WARNING: Pump {pump_index} is already registered. Overwriting...")

            try:
                if csv_filename is None:
                    csv_filename = f"water_pump_log_{pump_index}.csv"

                pump = AgXRPWaterPump(index=pump_index, csv_filename=csv_filename)
                self._water_pumps[pump_index] = pump
                print(f"Water pump {pump_index} registered successfully")
                return True
            except Exception as e:
                print(f"ERROR: Failed to register water pump {pump_index}: {e}")
                return False

    def start_access_point(self, ssid="AgXRP_SensorKit", password="sensor123", use_random_data=False):
        """!
        Start the access point and web server.

        @param ssid: SSID for the access point
        @param password: Password for the access point
        @param use_random_data: If True, generate random data for testing
        @return **bool** True if access point started successfully
        """
        try:
            self._wlan = access_point(ssid, password)
            self._ip_address = self._wlan.ifconfig()[0]
            self._use_random_data = use_random_data

            print(f"Access point '{ssid}' started")
            print(f"IP address: {self._ip_address}")

            dns.run_catchall(self._ip_address)
            self._register_routes()

            return True
        except Exception as e:
            print(f"Error starting access point: {e}")
            return False

    def _soil_unit_for_sensor(self, sensor_index):
        """Return the display unit for a given soil sensor index."""
        if sensor_index == 1:
            return self._soil_moisture_1_unit
        if sensor_index == 2:
            return self._soil_moisture_2_unit
        return "%"

    def _save_plant_system_to_config(self, sensor_index, pump_index, update_data):
        """!
        Save updated plant system settings to config.json.

        @param sensor_index: Soil sensor index
        @param pump_index: Pump index
        @param update_data: Dictionary of updated fields
        """
        try:
            with open(self._config_path, "r") as f:
                cfg = json.load(f)

            for ps in cfg.get("controller", {}).get("plant_systems", []):
                if ps.get("sensor_index") == sensor_index and ps.get("pump_index") == pump_index:
                    for key, value in update_data.items():
                        ps[key] = value
                    break

            import os
            tmp_path = self._config_path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(cfg, f)
            os.rename(tmp_path, self._config_path)

            print(f"Config saved for plant system: Sensor {sensor_index} -> Pump {pump_index}")
        except Exception as e:
            print(f"ERROR: Failed to save config: {e}")

    def _register_routes(self):
        """!
        Register web server routes.
        """
        def index_handler(request):
            try:
                return self._generate_html()
            except Exception as e:
                print(f"Error in index_handler: {e}")
                return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", 500

        def update_handler(request):
            try:
                if self._use_random_data:
                    self._generate_random_data()
                return self._generate_html()
            except Exception as e:
                print(f"Error in update_handler: {e}")
                return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", 500

        def api_sensors_handler(request):
            try:
                if self._use_random_data:
                    self._generate_random_data()
                json_data = json.dumps(self._sensor_data)
                return (json_data, 200, "application/json")
            except Exception as e:
                print(f"Error in api_sensors_handler: {e}")
                error_data = json.dumps({"error": str(e)})
                return (error_data, 500, "application/json")

        def pump_start_handler(request, pump_index):
            try:
                pump_index = int(pump_index)

                effort = 1.0
                if hasattr(request, 'query') and request.query and "effort" in request.query:
                    effort = float(request.query["effort"])
                elif hasattr(request, 'form') and request.form and "effort" in request.form:
                    effort = float(request.form["effort"])
                elif hasattr(request, 'data') and request.data and "effort" in request.data:
                    effort = float(request.data["effort"])

                effort = max(-1.0, min(1.0, effort))

                pump = None
                if self._controller:
                    pump = self._controller.get_pump(pump_index)
                elif pump_index in self._water_pumps:
                    pump = self._water_pumps[pump_index]

                if pump:
                    pump.set_pump_effort(effort, time_ms=0)
                    print(f"Pump {pump_index} started with effort {effort}")
                    if self._controller:
                        self._turn_on_soil_sensor_led(pump_index)
                    return (json.dumps({"status": "success", "message": f"Pump {pump_index} started with effort {effort}"}), 200, "application/json")
                else:
                    return (json.dumps({"status": "error", "message": f"Pump {pump_index} not registered"}), 404, "application/json")
            except ValueError as e:
                print(f"Error in pump_start_handler: Invalid parameter: {e}")
                return (json.dumps({"status": "error", "message": "Invalid pump index or effort value"}), 400, "application/json")
            except Exception as e:
                print(f"Error in pump_start_handler: {e}")
                return (json.dumps({"status": "error", "message": str(e)}), 500, "application/json")

        def pump_stop_handler(request, pump_index):
            try:
                pump_index = int(pump_index)

                pump = None
                if self._controller:
                    pump = self._controller.get_pump(pump_index)
                elif pump_index in self._water_pumps:
                    pump = self._water_pumps[pump_index]

                if pump:
                    pump.stop_pump()
                    print(f"Pump {pump_index} stopped")
                    if self._controller:
                        self._turn_off_soil_sensor_led(pump_index)
                    return (json.dumps({"status": "success", "message": f"Pump {pump_index} stopped"}), 200, "application/json")
                else:
                    return (json.dumps({"status": "error", "message": f"Pump {pump_index} not registered"}), 404, "application/json")
            except ValueError as e:
                print(f"Error in pump_stop_handler: Invalid pump index: {e}")
                return (json.dumps({"status": "error", "message": "Invalid pump index"}), 400, "application/json")
            except Exception as e:
                print(f"Error in pump_stop_handler: {e}")
                return (json.dumps({"status": "error", "message": str(e)}), 500, "application/json")

        def api_controller_plant_systems_handler(request):
            try:
                if not self._controller:
                    return (json.dumps({"error": "Controller not registered"}), 404, "application/json")

                plant_systems = self._controller.get_plant_systems()
                systems_list = []
                for (sensor_index, pump_index), system_data in plant_systems.items():
                    systems_list.append({
                        "sensor_index": sensor_index,
                        "pump_index": pump_index,
                        "interval_hours": system_data["interval_hours"],
                        "threshold": system_data["threshold"],
                        "duration_seconds": system_data["duration_seconds"],
                        "pump_effort": system_data.get("pump_effort", 1.0),
                        "enabled": system_data["enabled"]
                    })

                return (json.dumps({"plant_systems": systems_list}), 200, "application/json")
            except Exception as e:
                print(f"Error in api_controller_plant_systems_handler: {e}")
                error_data = json.dumps({"error": str(e)})
                return (error_data, 500, "application/json")

        def api_controller_plant_system_update_handler(request, sensor_index, pump_index):
            try:
                sensor_index = int(sensor_index)
                pump_index = int(pump_index)

                if not self._controller:
                    return (json.dumps({"status": "error", "message": "Controller not registered"}), 404, "application/json")

                update_data = {}

                if hasattr(request, 'form') and request.form:
                    if "interval_hours" in request.form:
                        update_data["interval_hours"] = float(request.form["interval_hours"])
                    if "threshold" in request.form:
                        update_data["threshold"] = float(request.form["threshold"])
                    if "duration_seconds" in request.form:
                        update_data["duration_seconds"] = float(request.form["duration_seconds"])
                    if "pump_effort" in request.form:
                        update_data["pump_effort"] = float(request.form["pump_effort"])
                    if "enabled" in request.form:
                        enabled_val = request.form["enabled"]
                        update_data["enabled"] = enabled_val.lower() in ["true", "1", "on", "yes"]

                elif hasattr(request, 'data') and request.data:
                    if "interval_hours" in request.data:
                        update_data["interval_hours"] = float(request.data["interval_hours"])
                    if "threshold" in request.data:
                        update_data["threshold"] = float(request.data["threshold"])
                    if "duration_seconds" in request.data:
                        update_data["duration_seconds"] = float(request.data["duration_seconds"])
                    if "pump_effort" in request.data:
                        update_data["pump_effort"] = float(request.data["pump_effort"])
                    if "enabled" in request.data:
                        enabled_val = request.data["enabled"]
                        if isinstance(enabled_val, bool):
                            update_data["enabled"] = enabled_val
                        else:
                            update_data["enabled"] = str(enabled_val).lower() in ["true", "1", "on", "yes"]

                elif hasattr(request, 'query') and request.query:
                    if "interval_hours" in request.query:
                        update_data["interval_hours"] = float(request.query["interval_hours"])
                    if "threshold" in request.query:
                        update_data["threshold"] = float(request.query["threshold"])
                    if "duration_seconds" in request.query:
                        update_data["duration_seconds"] = float(request.query["duration_seconds"])
                    if "pump_effort" in request.query:
                        update_data["pump_effort"] = float(request.query["pump_effort"])
                    if "enabled" in request.query:
                        enabled_val = request.query["enabled"]
                        update_data["enabled"] = enabled_val.lower() in ["true", "1", "on", "yes"]
                else:
                    return (json.dumps({"status": "error", "message": "No data provided"}), 400, "application/json")

                # Validate bounds
                if "interval_hours" in update_data and update_data["interval_hours"] < 0.01:
                    return (json.dumps({"status": "error", "message": "interval_hours must be >= 0.01"}), 400, "application/json")
                if "threshold" in update_data and update_data["threshold"] < 0:
                    return (json.dumps({"status": "error", "message": "threshold must be >= 0"}), 400, "application/json")
                if "duration_seconds" in update_data and not (0.1 <= update_data["duration_seconds"] <= 300):
                    return (json.dumps({"status": "error", "message": "duration_seconds must be between 0.1 and 300"}), 400, "application/json")

                if self._controller.update_plant_system(sensor_index, pump_index, **update_data):
                    self._save_plant_system_to_config(sensor_index, pump_index, update_data)
                    return (json.dumps({"status": "success", "message": "Plant system updated"}), 200, "application/json")
                else:
                    return (json.dumps({"status": "error", "message": "Failed to update plant system"}), 400, "application/json")

            except ValueError as e:
                print(f"Error in api_controller_plant_system_update_handler: Invalid parameters: {e}")
                return (json.dumps({"status": "error", "message": "Invalid sensor or pump index"}), 400, "application/json")
            except Exception as e:
                print(f"Error in api_controller_plant_system_update_handler: {e}")
                return (json.dumps({"status": "error", "message": str(e)}), 500, "application/json")

        def catchall_handler(request):
            try:
                return self._generate_html()
            except Exception as e:
                print(f"Error in catchall_handler: {e}")
                return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", 500

        server.add_route("/", index_handler, methods=["GET"])
        server.add_route("/update", update_handler, methods=["GET", "POST"])
        server.add_route("/api/sensors", api_sensors_handler, methods=["GET"])
        server.add_route("/pump/start/<pump_index>", pump_start_handler, methods=["GET", "POST"])
        server.add_route("/pump/stop/<pump_index>", pump_stop_handler, methods=["GET", "POST"])
        server.add_route("/api/controller/plant_systems", api_controller_plant_systems_handler, methods=["GET"])
        server.add_route("/api/controller/plant_system/<sensor_index>/<pump_index>", api_controller_plant_system_update_handler, methods=["POST"])

        server.set_callback(catchall_handler)

    def _turn_on_soil_sensor_led(self, pump_index):
        """!
        Turn on LED for soil sensor(s) associated with the given pump.

        @param pump_index: Pump index
        """
        try:
            if not self._controller:
                return

            sensor_kit = self._controller.get_sensor_kit()
            if not sensor_kit:
                return

            plant_systems = self._controller.get_plant_systems()
            for (sensor_index, pump_idx), system_data in plant_systems.items():
                if pump_idx == pump_index:
                    soil_sensor = sensor_kit.soil_sensors.get(sensor_index)
                    if soil_sensor and soil_sensor.is_connected():
                        soil_sensor.set_led(True)
                        print(f"LED turned on for soil sensor {sensor_index} (pump {pump_index})")
        except Exception as e:
            print(f"Error turning on soil sensor LED: {e}")

    def _turn_off_soil_sensor_led(self, pump_index):
        """!
        Turn off LED for soil sensor(s) associated with the given pump.

        @param pump_index: Pump index
        """
        try:
            if not self._controller:
                return

            sensor_kit = self._controller.get_sensor_kit()
            if not sensor_kit:
                return

            plant_systems = self._controller.get_plant_systems()
            for (sensor_index, pump_idx), system_data in plant_systems.items():
                if pump_idx == pump_index:
                    soil_sensor = sensor_kit.soil_sensors.get(sensor_index)
                    if soil_sensor and soil_sensor.is_connected():
                        soil_sensor.set_led(False)
                        print(f"LED turned off for soil sensor {sensor_index} (pump {pump_index})")
        except Exception as e:
            print(f"Error turning off soil sensor LED: {e}")

    def update_sensor_data(self, data_dict):
        """!
        Update sensor data from AgXRPSensorKit.

        @param data_dict: Dictionary containing sensor readings
        """
        if "temperature" in data_dict and self._temperature_registered:
            self._sensor_data["temperature"] = data_dict["temperature"]

        if "humidity" in data_dict and self._humidity_registered:
            self._sensor_data["humidity"] = data_dict["humidity"]

        if "co2" in data_dict and self._co2_registered:
            self._sensor_data["co2"] = data_dict["co2"]

        if "blue_light" in data_dict and self._blue_light_registered:
            self._sensor_data["blue_light"] = data_dict["blue_light"]
        elif "blue" in data_dict and self._blue_light_registered:
            self._sensor_data["blue_light"] = data_dict["blue"]

        if "green_light" in data_dict and self._green_light_registered:
            self._sensor_data["green_light"] = data_dict["green_light"]
        elif "green" in data_dict and self._green_light_registered:
            self._sensor_data["green_light"] = data_dict["green"]

        if "red_light" in data_dict and self._red_light_registered:
            self._sensor_data["red_light"] = data_dict["red_light"]
        elif "red" in data_dict and self._red_light_registered:
            self._sensor_data["red_light"] = data_dict["red"]

        if "nir_light" in data_dict and self._nir_light_registered:
            self._sensor_data["nir_light"] = data_dict["nir_light"]
        elif "nir" in data_dict and self._nir_light_registered:
            self._sensor_data["nir_light"] = data_dict["nir"]

        if "light_intensity" in data_dict and self._light_intensity_registered:
            self._sensor_data["light_intensity"] = data_dict["light_intensity"]
        elif "ambient_light" in data_dict and self._light_intensity_registered:
            self._sensor_data["light_intensity"] = data_dict["ambient_light"]

        if "soil_moisture_1" in data_dict and self._soil_moisture_1_registered:
            self._sensor_data["soil_moisture_1"] = data_dict["soil_moisture_1"]
        elif "soil_moisture" in data_dict and self._soil_moisture_1_registered:
            self._sensor_data["soil_moisture_1"] = data_dict["soil_moisture"]

        if "soil_moisture_2" in data_dict and self._soil_moisture_2_registered:
            self._sensor_data["soil_moisture_2"] = data_dict["soil_moisture_2"]

        import time
        self._sensor_data["_last_updated"] = time.ticks_ms()

    def _generate_random_data(self):
        """!
        Generate random sensor data for testing.
        """
        if self._temperature_registered:
            self._sensor_data["temperature"] = round(random.uniform(15.0, 30.0), 1)
        if self._humidity_registered:
            self._sensor_data["humidity"] = round(random.uniform(20.0, 80.0), 1)
        if self._co2_registered:
            self._sensor_data["co2"] = random.randint(400, 1000)
        if self._blue_light_registered:
            self._sensor_data["blue_light"] = random.randint(0, 999)
        if self._green_light_registered:
            self._sensor_data["green_light"] = random.randint(0, 999)
        if self._red_light_registered:
            self._sensor_data["red_light"] = random.randint(0, 999)
        if self._nir_light_registered:
            self._sensor_data["nir_light"] = random.randint(0, 999)
        if self._light_intensity_registered:
            self._sensor_data["light_intensity"] = round(random.uniform(0.0, 1000.0), 1)
        if self._soil_moisture_1_registered:
            self._sensor_data["soil_moisture_1"] = round(random.uniform(0.0, 100.0), 1)
        if self._soil_moisture_2_registered:
            self._sensor_data["soil_moisture_2"] = round(random.uniform(0.0, 100.0), 1)

    def _generate_html(self):
        """!
        Generate the HTML page displaying sensor data.

        @return **str** HTML content
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AgXRP Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        h1 {
            color: #333;
            margin: 0;
        }
        .nav-links { display: flex; gap: 8px; }
        .nav-link {
            background-color: #607D8B;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 14px;
            font-weight: bold;
        }
        .nav-link:hover {
            background-color: #455A64;
        }
        .sensor-container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sensor-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .sensor-item:last-child {
            border-bottom: none;
        }
        .sensor-label {
            font-weight: bold;
            color: #555;
        }
        .sensor-value {
            color: #2196F3;
            font-size: 1.1em;
        }
        .no-data {
            color: #999;
            font-style: italic;
        }
        .pump-container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .pump-controls {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        .pump-button {
            flex: 1;
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 4px;
            cursor: pointer;
            border: none;
            font-weight: bold;
        }
        .pump-start-button {
            background-color: #2196F3;
            color: white;
        }
        .pump-start-button:hover {
            background-color: #1976D2;
        }
        .pump-stop-button {
            background-color: #f44336;
            color: white;
        }
        .pump-stop-button:hover {
            background-color: #d32f2f;
        }
        .controller-container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .controller-form {
            margin-bottom: 20px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fafafa;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
            color: #555;
        }
        .form-input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .form-radio-group {
            display: flex;
            gap: 15px;
            margin-top: 5px;
        }
        .form-radio {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .form-submit-button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 14px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 10px;
        }
        .form-submit-button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>AgXRP Dashboard</h1>
        <div class="nav-links">
            <a href="/data" class="nav-link">Data</a>
            <a href="/configure" class="nav-link">Configure</a>
        </div>
    </div>
    <div class="sensor-container">
"""

        # Add registered sensor data
        sensor_count = 0

        if self._temperature_registered:
            value = self._sensor_data.get("temperature")
            display_value = f"{value:.1f}&deg;C" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Temperature:</span><span class="sensor-value" data-sensor="temperature">{display_value}</span></div>\n'
            sensor_count += 1

        if self._humidity_registered:
            value = self._sensor_data.get("humidity")
            display_value = f"{value:.1f}%" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Humidity:</span><span class="sensor-value" data-sensor="humidity">{display_value}</span></div>\n'
            sensor_count += 1

        if self._co2_registered:
            value = self._sensor_data.get("co2")
            display_value = f"{value} ppm" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">CO2 PPM:</span><span class="sensor-value" data-sensor="co2">{display_value}</span></div>\n'
            sensor_count += 1

        if self._blue_light_registered:
            value = self._sensor_data.get("blue_light")
            display_value = f"{int(value)}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Blue Light:</span><span class="sensor-value" data-sensor="blue_light">{display_value}</span></div>\n'
            sensor_count += 1

        if self._green_light_registered:
            value = self._sensor_data.get("green_light")
            display_value = f"{int(value)}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Green Light:</span><span class="sensor-value" data-sensor="green_light">{display_value}</span></div>\n'
            sensor_count += 1

        if self._red_light_registered:
            value = self._sensor_data.get("red_light")
            display_value = f"{int(value)}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Red Light:</span><span class="sensor-value" data-sensor="red_light">{display_value}</span></div>\n'
            sensor_count += 1

        if self._nir_light_registered:
            value = self._sensor_data.get("nir_light")
            display_value = f"{int(value)}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">NIR Light:</span><span class="sensor-value" data-sensor="nir_light">{display_value}</span></div>\n'
            sensor_count += 1

        if self._light_intensity_registered:
            value = self._sensor_data.get("light_intensity")
            display_value = f"{value:.1f} lux" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Light Intensity:</span><span class="sensor-value" data-sensor="light_intensity">{display_value}</span></div>\n'
            sensor_count += 1

        if self._soil_moisture_1_registered:
            value = self._sensor_data.get("soil_moisture_1")
            unit = self._soil_moisture_1_unit
            display_value = f"{value:.1f} {unit}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Soil Moisture 1:</span><span class="sensor-value" data-sensor="soil_moisture_1">{display_value}</span></div>\n'
            sensor_count += 1

        if self._soil_moisture_2_registered:
            value = self._sensor_data.get("soil_moisture_2")
            unit = self._soil_moisture_2_unit
            display_value = f"{value:.1f} {unit}" if value is not None else "<span class='no-data'>No data</span>"
            html += f'        <div class="sensor-item"><span class="sensor-label">Soil Moisture 2:</span><span class="sensor-value" data-sensor="soil_moisture_2">{display_value}</span></div>\n'
            sensor_count += 1

        if sensor_count == 0:
            html += '        <div class="sensor-item"><span class="no-data">No sensors registered</span></div>\n'

        html += '        <div class="sensor-item" style="border-top:1px solid #eee;margin-top:4px;padding-top:6px;">'
        html += '<span class="sensor-label" style="color:#999;font-size:0.85em;">Last updated:</span>'
        html += '<span class="sensor-value" id="last-updated-label" style="color:#999;font-size:0.85em;">-</span></div>\n'

        html += """    </div>
"""

        # Add water pump controls if any pumps are registered
        pumps_to_display = []
        if self._controller:
            controller_pumps = {}
            for (sensor_idx, pump_idx), system in self._controller.get_plant_systems().items():
                if pump_idx not in controller_pumps:
                    controller_pumps[pump_idx] = []
                controller_pumps[pump_idx].append(sensor_idx)
            pumps_to_display = sorted(controller_pumps.keys())
        elif len(self._water_pumps) > 0:
            pumps_to_display = sorted(self._water_pumps.keys())

        if pumps_to_display:
            html += """    <div class="pump-container">
        <h2 style="margin-top: 0; color: #333;">Water Pump Controls</h2>
"""
            for pump_index in pumps_to_display:
                html += f"""        <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 4px; background-color: #fafafa;">
            <div style="font-weight: bold; margin-bottom: 10px; color: #555;">Pump {pump_index}</div>
            <div class="form-group" style="margin-bottom: 10px;">
                <label class="form-label" for="pump-effort-{pump_index}" style="font-size: 14px;">Pump Effort (-1.0 to 1.0):</label>
                <input type="number" class="form-input" id="pump-effort-{pump_index}"
                       step="0.1" min="-1.0" max="1.0" value="1.0"
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
            </div>
            <div class="pump-controls">
                <button type="button" class="pump-button pump-start-button" onclick="startPump({pump_index})" style="flex: 1;">Start Pump {pump_index}</button>
                <button type="button" class="pump-button pump-stop-button" onclick="stopPump({pump_index})" style="flex: 1;">Stop Pump {pump_index}</button>
            </div>
        </div>
"""
            html += """    </div>
"""

        # Add controller configuration UI if controller is registered
        if self._controller:
            plant_systems = self._controller.get_plant_systems()
            if len(plant_systems) > 0:
                html += """    <div class="controller-container">
        <h2 style="margin-top: 0; color: #333;">Automatic Watering Controller</h2>
"""
                for (sensor_index, pump_index), system_data in sorted(plant_systems.items()):
                    html += f"""        <div class="controller-form">
            <h3 style="margin-top: 0; color: #555;">Plant System: Sensor {sensor_index} + Pump {pump_index}</h3>
            <form id="controller-form-{sensor_index}-{pump_index}" onsubmit="updateControllerSettings({sensor_index}, {pump_index}, event); return false;">
                <div class="form-group">
                    <label class="form-label" for="interval-{sensor_index}-{pump_index}">Check Interval (hours):</label>
                    <input type="number" class="form-input" id="interval-{sensor_index}-{pump_index}"
                           name="interval_hours" step="0.01" min="0.01"
                           value="{system_data['interval_hours']:.2f}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="threshold-{sensor_index}-{pump_index}">Soil Moisture Threshold ({self._soil_unit_for_sensor(sensor_index)}):</label>
                    <input type="number" class="form-input" id="threshold-{sensor_index}-{pump_index}"
                           name="threshold" step="0.1" min="0"
                           value="{system_data['threshold']:.1f}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="duration-{sensor_index}-{pump_index}">Pump Duration (seconds):</label>
                    <input type="number" class="form-input" id="duration-{sensor_index}-{pump_index}"
                           name="duration_seconds" step="0.1" min="0.1"
                           value="{system_data['duration_seconds']:.1f}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="pump_effort-{sensor_index}-{pump_index}">Pump Effort (-1.0 to 1.0):</label>
                    <input type="number" class="form-input" id="pump_effort-{sensor_index}-{pump_index}"
                           name="pump_effort" step="0.1" min="-1.0" max="1.0"
                           value="{system_data.get('pump_effort', 1.0):.1f}" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Enable Controller:</label>
                    <div class="form-radio-group">
                        <div class="form-radio">
                            <input type="radio" id="enabled-yes-{sensor_index}-{pump_index}"
                                   name="enabled" value="true" {"checked" if system_data['enabled'] else ""}>
                            <label for="enabled-yes-{sensor_index}-{pump_index}">Enabled</label>
                        </div>
                        <div class="form-radio">
                            <input type="radio" id="enabled-no-{sensor_index}-{pump_index}"
                                   name="enabled" value="false" {"checked" if not system_data['enabled'] else ""}>
                            <label for="enabled-no-{sensor_index}-{pump_index}">Disabled</label>
                        </div>
                    </div>
                </div>
                <button type="submit" class="form-submit-button">Update Settings</button>
            </form>
        </div>
"""
                html += """    </div>
"""

        # Embed soil moisture units as a JS variable so formatSensorValue can use them
        html += f"""
    <script>
        const SOIL_UNITS = {{
            'soil_moisture_1': '{self._soil_moisture_1_unit}',
            'soil_moisture_2': '{self._soil_moisture_2_unit}'
        }};

        function formatSensorValue(sensorKey, value) {{
            if (value === null || value === undefined) {{
                return '<span class="no-data">No data</span>';
            }}

            switch(sensorKey) {{
                case 'temperature':
                    return value.toFixed(1) + '&deg;C';
                case 'humidity':
                    return value.toFixed(1) + '%';
                case 'soil_moisture_1':
                case 'soil_moisture_2':
                    return value.toFixed(1) + ' ' + (SOIL_UNITS[sensorKey] || '%');
                case 'co2':
                    return value + ' ppm';
                case 'light_intensity':
                    return value.toFixed(1) + ' lux';
                case 'blue_light':
                case 'green_light':
                case 'red_light':
                case 'nir_light':
                    return Math.floor(value).toString();
                default:
                    return value.toString();
            }}
        }}

        function updateSensorValues(data) {
            for (const [key, value] of Object.entries(data)) {
                const element = document.querySelector('[data-sensor="' + key + '"]');
                if (element) {
                    element.innerHTML = formatSensorValue(key, value);
                }
            }
        }

        let _lastUpdatedMs = null;

        async function fetchSensorData() {
            try {
                const response = await fetch('/api/sensors');
                if (response.ok) {
                    const data = await response.json();
                    if (data._last_updated !== undefined) {
                        _lastUpdatedMs = Date.now();
                        delete data._last_updated;
                    }
                    updateSensorValues(data);
                }
            } catch (error) {
                console.error('Error fetching sensor data:', error);
            }
        }

        function updateLastUpdatedLabel() {
            const el = document.getElementById('last-updated-label');
            if (!el) return;
            if (_lastUpdatedMs === null) { el.textContent = '-'; return; }
            const sec = Math.round((Date.now() - _lastUpdatedMs) / 1000);
            el.textContent = sec < 5 ? 'just now' : sec + 's ago';
        }

        setInterval(updateLastUpdatedLabel, 1000);

        setInterval(fetchSensorData, 2000);
        fetchSensorData();

        async function startPump(pumpIndex) {
            try {
                const effortInput = document.getElementById(`pump-effort-${pumpIndex}`);
                const effort = effortInput ? parseFloat(effortInput.value) : 1.0;
                const clampedEffort = Math.max(-1.0, Math.min(1.0, effort));

                const response = await fetch(`/pump/start/${pumpIndex}?effort=${clampedEffort}`);
                const data = await response.json();
                if (data.status !== 'success') {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error starting pump: ' + error);
            }
        }

        async function stopPump(pumpIndex) {
            try {
                const response = await fetch(`/pump/stop/${pumpIndex}`);
                const data = await response.json();
                if (data.status !== 'success') {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error stopping pump: ' + error);
            }
        }

        async function updateControllerSettings(sensorIndex, pumpIndex, event) {
            event.preventDefault();

            try {
                const form = event.target;
                const formData = new FormData(form);

                const params = new URLSearchParams();
                for (const [key, value] of formData.entries()) {
                    params.append(key, value);
                }

                const response = await fetch(`/api/controller/plant_system/${sensorIndex}/${pumpIndex}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: params.toString()
                });

                const data = await response.json();
                if (data.status === 'success') {
                    alert('Settings updated and saved to config!');
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error updating settings: ' + error);
            }
        }
    </script>
</body>
</html>"""

        return html

    def run(self):
        """!
        Start the web server (blocking call).
        """
        if self._wlan is None:
            print("ERROR: Access point not started. Call start_access_point() first.")
            return

        print(f"Starting web server on {self._ip_address}")
        self._server_running = True

        if self._use_random_data:
            self._generate_random_data()

        server.run(host="0.0.0.0", port=80)

    def get_ip_address(self):
        """!
        Get the IP address of the access point.

        @return **str** IP address, or None if not started
        """
        return self._ip_address
