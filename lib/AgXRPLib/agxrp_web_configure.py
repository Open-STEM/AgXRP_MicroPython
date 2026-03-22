#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_web_configure.py
#
# Web-based configuration editor for AgXRP Sensor Kit.
# Renders an HTML form for all settings in config.json and handles saving.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import json
from phew import server


class AgXRPWebConfigure:
    """!
    Web configuration page that lets users edit all settings in config.json.

    Registers routes for viewing and saving the configuration, and for
    triggering a device reboot so that changes take effect.
    """

    # Maximum number of array entries supported for soil, pumps, plant systems
    MAX_SOIL = 4
    MAX_PUMPS = 4
    MAX_PLANT_SYSTEMS = 4

    def __init__(self, config_path="config.json"):
        """!
        Constructor.

        @param config_path  Path to the JSON configuration file.
        """
        self._config_path = config_path

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def register_routes(self):
        """!
        Register the GET /configure, POST /configure/save, and
        POST /configure/reboot routes with the phew server.
        """
        server.add_route("/configure", self._handle_configure, methods=["GET"])
        server.add_route("/configure/save", self._handle_save, methods=["POST"])
        server.add_route("/configure/reboot", self._handle_reboot, methods=["POST"])

    # ------------------------------------------------------------------
    # Config I/O
    # ------------------------------------------------------------------

    def _load_config(self):
        """!
        Read and return config.json as a Python dict.

        @return **dict** Parsed configuration dictionary.
        """
        with open(self._config_path, "r") as f:
            return json.load(f)

    def _save_config(self, cfg):
        """!
        Write a Python dict to config.json.

        @param cfg  The configuration dictionary to persist.
        """
        with open(self._config_path, "w") as f:
            json.dump(cfg, f)

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    def _handle_configure(self, request):
        """GET /configure — serve the configuration form."""
        html = self._generate_html()
        return (html, 200, "text/html")

    def _handle_save(self, request):
        """POST /configure/save — parse form data, save config, show result."""
        form = request.form
        cfg = self._parse_form(form)
        self._save_config(cfg)
        html = self._generate_success_html()
        return (html, 200, "text/html")

    def _handle_reboot(self, request):
        """POST /configure/reboot — reboot the device."""
        import machine
        machine.reset()

    # ------------------------------------------------------------------
    # Form parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _form_bool(form, key, default=False):
        """Return True/False from a form radio value ('true'/'false')."""
        val = form.get(key, None)
        if val is None:
            return default
        return val.strip().lower() == "true"

    @staticmethod
    def _form_int(form, key, default=0):
        """Return an int from a form value."""
        val = form.get(key, None)
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _form_float(form, key, default=0.0):
        """Return a float from a form value."""
        val = form.get(key, None)
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _form_str(form, key, default=""):
        """Return a string from a form value."""
        return form.get(key, default)

    def _parse_form(self, form):
        """Reconstruct the full config dict from submitted form data."""
        # Load existing config to preserve fields not shown in the form
        existing = self._load_config()
        cfg = {}

        # Preserve use_random_data from existing config (not editable in UI)
        cfg["use_random_data"] = existing.get("use_random_data", False)

        # Sensor kit / I2C — preserve i2c_freq from existing config
        cfg["sensor_kit"] = {
            "bus0_enabled": self._form_bool(form, "bus0_enabled"),
            "bus1_enabled": self._form_bool(form, "bus1_enabled"),
            "i2c_freq": existing.get("sensor_kit", {}).get("i2c_freq", 100000),
        }

        # Sensors
        sensors = {}

        sensors["co2"] = {
            "enabled": self._form_bool(form, "co2_enabled"),
            "bus": self._form_int(form, "co2_bus"),
        }

        sensors["spectral"] = {
            "enabled": self._form_bool(form, "spectral_enabled"),
            "bus": self._form_int(form, "spectral_bus"),
        }

        sensors["light"] = {
            "enabled": self._form_bool(form, "light_enabled"),
            "bus": self._form_int(form, "light_bus"),
        }

        # Soil — variable-length array
        soil_list = []
        for i in range(self.MAX_SOIL):
            key = "soil_{}_enabled".format(i)
            if form.get(key, None) is None:
                break
            soil_list.append({
                "enabled": self._form_bool(form, key),
                "type": self._form_str(form, "soil_{}_type".format(i), "capacitive"),
                "sensor_index": self._form_int(form, "soil_{}_sensor_index".format(i), i + 1),
                "bus": self._form_int(form, "soil_{}_bus".format(i)),
                "address": self._form_str(form, "soil_{}_address".format(i), "0x37"),
            })
        sensors["soil"] = soil_list

        # Screen
        sensors["screen"] = {
            "enabled": self._form_bool(form, "screen_enabled"),
            "bus": self._form_int(form, "screen_bus"),
        }

        # CSV Logger
        sensors["csv_logger"] = {
            "enabled": self._form_bool(form, "csv_enabled"),
            "filename": self._form_str(form, "csv_filename", "sensor_log.csv"),
            "period_ms": self._form_int(form, "csv_period_ms", 5000),
        }

        cfg["sensors"] = sensors

        # Controller
        controller = {
            "enabled": self._form_bool(form, "controller_enabled"),
        }

        # Pumps
        pumps_list = []
        for i in range(self.MAX_PUMPS):
            key = "pump_{}_enabled".format(i)
            if form.get(key, None) is None:
                break
            pumps_list.append({
                "enabled": self._form_bool(form, key),
                "pump_index": self._form_int(form, "pump_{}_pump_index".format(i), i + 1),
                "csv_filename": self._form_str(form, "pump_{}_csv_filename".format(i)),
            })
        controller["pumps"] = pumps_list

        # Plant systems
        ps_list = []
        for i in range(self.MAX_PLANT_SYSTEMS):
            key = "ps_{}_enabled".format(i)
            if form.get(key, None) is None:
                break
            ps_list.append({
                "enabled": self._form_bool(form, key),
                "sensor_index": self._form_int(form, "ps_{}_sensor_index".format(i), 1),
                "pump_index": self._form_int(form, "ps_{}_pump_index".format(i), 1),
                "interval_hours": self._form_float(form, "ps_{}_interval_hours".format(i), 0.5),
                "threshold": self._form_float(form, "ps_{}_threshold".format(i), 300.0),
                "duration_seconds": self._form_float(form, "ps_{}_duration_seconds".format(i), 3.0),
            })
        controller["plant_systems"] = ps_list

        cfg["controller"] = controller

        # Webserver / Access Point
        cfg["webserver"] = {
            "access_point": {
                "ssid": self._form_str(form, "ap_ssid", "AgXRP_SensorKit"),
                "password": self._form_str(form, "ap_password", "sensor123"),
            }
        }

        # Sensor update interval
        cfg["sensor_update_interval_seconds"] = self._form_int(
            form, "sensor_update_interval_seconds", 2
        )

        return cfg

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def _generate_html(self):
        """!
        Build the full HTML configuration form based on current config.json.

        @return **str** Complete HTML page as a string.
        """
        cfg = self._load_config()

        html = self._html_head()
        html += '<body>\n'
        html += '<div class="header">\n'
        html += '  <h1>AgXRP Configuration</h1>\n'
        html += '  <div class="nav-links">\n'
        html += '    <a href="/" class="nav-link">Dashboard</a>\n'
        html += '    <a href="/data" class="nav-link">Data</a>\n'
        html += '  </div>\n'
        html += '</div>\n'
        html += '<form method="POST" action="/configure/save">\n'

        html += self._section_general(cfg)
        html += self._section_i2c(cfg)
        html += self._section_co2(cfg)
        html += self._section_spectral(cfg)
        html += self._section_light(cfg)
        html += self._section_soil(cfg)
        html += self._section_screen(cfg)
        html += self._section_csv_logger(cfg)
        html += self._section_controller(cfg)
        html += self._section_pumps(cfg)
        html += self._section_plant_systems(cfg)
        html += self._section_access_point(cfg)
        html += self._section_sensor_interval(cfg)

        html += '<div class="card">\n'
        html += '  <button type="submit" class="btn btn-save">Save Configuration</button>\n'
        html += '</div>\n'

        html += '</form>\n'
        html += '</body></html>'
        return html

    # ------------------------------------------------------------------
    # HTML fragments
    # ------------------------------------------------------------------

    @staticmethod
    def _html_head():
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AgXRP Configuration</title>
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
            margin-bottom: 15px;
        }
        h1 { color: #333; margin: 0; }
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
        .nav-link:hover { background-color: #455A64; }
        .card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h2 {
            margin-top: 0;
            color: #333;
            font-size: 18px;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        .card h3 {
            margin-top: 12px;
            color: #555;
            font-size: 15px;
        }
        .field {
            margin-bottom: 12px;
        }
        .field label {
            display: block;
            font-size: 14px;
            color: #555;
            margin-bottom: 4px;
            font-weight: bold;
        }
        .field input[type="text"],
        .field input[type="number"],
        .field select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .radio-group {
            display: flex;
            gap: 16px;
            padding: 4px 0;
        }
        .radio-group label {
            display: inline;
            font-weight: normal;
            font-size: 14px;
            cursor: pointer;
        }
        .radio-group input[type="radio"] {
            margin-right: 4px;
        }
        .sub-section {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 10px;
            background-color: #fafafa;
        }
        .btn {
            display: block;
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            text-align: center;
        }
        .btn-save {
            background-color: #4CAF50;
            color: white;
        }
        .btn-save:hover {
            background-color: #45a049;
        }
    </style>
</head>
"""

    # --- individual section builders ---

    def _section_general(self, cfg):
        return ''

    def _section_i2c(self, cfg):
        sk = cfg.get("sensor_kit", {})
        h = '<div class="card"><h2>I2C Bus Configuration</h2>\n'
        h += self._radio_field("bus0_enabled", "Bus 0", sk.get("bus0_enabled", True),
                               true_label="Enabled", false_label="Disabled")
        h += self._radio_field("bus1_enabled", "Bus 1", sk.get("bus1_enabled", True),
                               true_label="Enabled", false_label="Disabled")
        h += '</div>\n'
        return h

    def _section_co2(self, cfg):
        s = cfg.get("sensors", {}).get("co2", {})
        h = '<div class="card"><h2>CO2 Sensor (SCD4x)</h2>\n'
        h += self._radio_field("co2_enabled", "Enabled", s.get("enabled", False))
        h += self._bus_select("co2_bus", s.get("bus", 0))
        h += '</div>\n'
        return h

    def _section_spectral(self, cfg):
        s = cfg.get("sensors", {}).get("spectral", {})
        h = '<div class="card"><h2>Spectral Sensor (AS7343)</h2>\n'
        h += self._radio_field("spectral_enabled", "Enabled", s.get("enabled", False))
        h += self._bus_select("spectral_bus", s.get("bus", 0))
        h += '</div>\n'
        return h

    def _section_light(self, cfg):
        s = cfg.get("sensors", {}).get("light", {})
        h = '<div class="card"><h2>Light Sensor (VEML)</h2>\n'
        h += self._radio_field("light_enabled", "Enabled", s.get("enabled", False))
        h += self._bus_select("light_bus", s.get("bus", 0))
        h += '</div>\n'
        return h

    def _section_soil(self, cfg):
        soil_list = cfg.get("sensors", {}).get("soil", [])
        h = '<div class="card"><h2>Soil Sensors</h2>\n'
        for i in range(max(len(soil_list), 1)):
            entry = soil_list[i] if i < len(soil_list) else {
                "enabled": False, "type": "capacitive",
                "sensor_index": i + 1, "bus": 0, "address": "0x37"
            }
            prefix = "soil_{}".format(i)
            h += '<div class="sub-section"><h3>Soil Sensor {}</h3>\n'.format(i + 1)
            h += self._radio_field("{}_enabled".format(prefix), "Enabled",
                                   entry.get("enabled", False))
            h += self._select_field("{}_type".format(prefix), "Type",
                                    entry.get("type", "capacitive"),
                                    [("capacitive", "Capacitive"),
                                     ("resistive", "Resistive")])
            h += self._select_field("{}_sensor_index".format(prefix), "Sensor Index",
                                    str(entry.get("sensor_index", i + 1)),
                                    [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")])
            h += self._bus_select("{}_bus".format(prefix), entry.get("bus", 0))
            h += self._select_field("{}_address".format(prefix), "Address",
                                    entry.get("address", "0x37"),
                                    [("0x28", "0x28"), ("0x37", "0x37")])
            h += '</div>\n'
        h += '</div>\n'
        return h

    def _section_screen(self, cfg):
        s = cfg.get("sensors", {}).get("screen", {})
        h = '<div class="card"><h2>OLED Screen</h2>\n'
        h += self._radio_field("screen_enabled", "Enabled", s.get("enabled", False))
        h += self._bus_select("screen_bus", s.get("bus", 0))
        h += '</div>\n'
        return h

    def _section_csv_logger(self, cfg):
        s = cfg.get("sensors", {}).get("csv_logger", {})
        h = '<div class="card"><h2>CSV Logger</h2>\n'
        h += self._radio_field("csv_enabled", "Enabled", s.get("enabled", False))
        h += self._text_field("csv_filename", "Filename",
                              s.get("filename", "sensor_log.csv"))
        h += self._number_field("csv_period_ms", "Period (ms)",
                                s.get("period_ms", 5000))
        h += '</div>\n'
        return h

    def _section_controller(self, cfg):
        c = cfg.get("controller", {})
        h = '<div class="card"><h2>Controller</h2>\n'
        h += self._radio_field("controller_enabled", "Enabled",
                               c.get("enabled", False))
        h += '</div>\n'
        return h

    def _section_pumps(self, cfg):
        pumps = cfg.get("controller", {}).get("pumps", [])
        h = '<div class="card"><h2>Pumps</h2>\n'
        for i in range(max(len(pumps), 1)):
            entry = pumps[i] if i < len(pumps) else {
                "enabled": False, "pump_index": i + 1,
                "csv_filename": "water_pump_{}_log.csv".format(i + 1)
            }
            prefix = "pump_{}".format(i)
            h += '<div class="sub-section"><h3>Pump {}</h3>\n'.format(i + 1)
            h += self._radio_field("{}_enabled".format(prefix), "Enabled",
                                   entry.get("enabled", False))
            h += self._select_field("{}_pump_index".format(prefix), "Pump Index",
                                    str(entry.get("pump_index", i + 1)),
                                    [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")])
            h += self._text_field("{}_csv_filename".format(prefix), "CSV Filename",
                                  entry.get("csv_filename", ""))
            h += '</div>\n'
        h += '</div>\n'
        return h

    def _section_plant_systems(self, cfg):
        ps = cfg.get("controller", {}).get("plant_systems", [])
        h = '<div class="card"><h2>Plant Systems</h2>\n'
        for i in range(max(len(ps), 1)):
            entry = ps[i] if i < len(ps) else {
                "enabled": False, "sensor_index": 1, "pump_index": 1,
                "interval_hours": 0.5, "threshold": 300.0, "duration_seconds": 3.0
            }
            prefix = "ps_{}".format(i)
            h += '<div class="sub-section"><h3>Plant System {}</h3>\n'.format(i + 1)
            h += self._radio_field("{}_enabled".format(prefix), "Enabled",
                                   entry.get("enabled", False))
            h += self._select_field("{}_sensor_index".format(prefix), "Sensor Index",
                                    str(entry.get("sensor_index", 1)),
                                    [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")])
            h += self._select_field("{}_pump_index".format(prefix), "Pump Index",
                                    str(entry.get("pump_index", 1)),
                                    [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")])
            h += self._number_field("{}_interval_hours".format(prefix),
                                    "Interval (hours)",
                                    entry.get("interval_hours", 0.5),
                                    step="0.01", min_val="0.01")
            h += self._number_field("{}_threshold".format(prefix), "Threshold",
                                    entry.get("threshold", 300.0))
            h += self._number_field("{}_duration_seconds".format(prefix),
                                    "Duration (seconds)",
                                    entry.get("duration_seconds", 3.0))
            h += '</div>\n'
        h += '</div>\n'
        return h

    def _section_access_point(self, cfg):
        ap = cfg.get("webserver", {}).get("access_point", {})
        h = '<div class="card"><h2>Access Point</h2>\n'
        h += self._text_field("ap_ssid", "SSID",
                              ap.get("ssid", "AgXRP_SensorKit"))
        h += self._text_field("ap_password", "Password",
                              ap.get("password", "sensor123"))
        h += '</div>\n'
        return h

    def _section_sensor_interval(self, cfg):
        val = cfg.get("sensor_update_interval_seconds", 2)
        h = '<div class="card"><h2>Sensor Update Interval</h2>\n'
        h += self._number_field("sensor_update_interval_seconds",
                                "Interval (seconds)", val)
        h += '</div>\n'
        return h

    # ------------------------------------------------------------------
    # Reusable HTML field builders
    # ------------------------------------------------------------------

    @staticmethod
    def _radio_field(name, label, current_value,
                     true_label="Enabled", false_label="Disabled"):
        """Render a pair of radio buttons for a boolean field."""
        checked_t = ' checked' if current_value else ''
        checked_f = ' checked' if not current_value else ''
        return (
            '<div class="field">'
            '<label>{label}</label>'
            '<div class="radio-group">'
            '<label><input type="radio" name="{name}" value="true"{ct}> {tl}</label>'
            '<label><input type="radio" name="{name}" value="false"{cf}> {fl}</label>'
            '</div></div>\n'
        ).format(
            label=label, name=name,
            ct=checked_t, cf=checked_f,
            tl=true_label, fl=false_label,
        )

    @staticmethod
    def _select_field(name, label, current_value, options):
        """Render a <select> dropdown.

        @param options  List of (value, display_text) tuples.
        """
        h = '<div class="field"><label>{}</label>'.format(label)
        h += '<select name="{}">'.format(name)
        for val, text in options:
            sel = ' selected' if str(current_value) == str(val) else ''
            h += '<option value="{}"{}>{}</option>'.format(val, sel, text)
        h += '</select></div>\n'
        return h

    def _bus_select(self, name, current_value):
        """Shortcut for a bus dropdown (0 or 1)."""
        return self._select_field(name, "Bus", str(current_value),
                                  [("0", "0"), ("1", "1")])

    @staticmethod
    def _text_field(name, label, current_value):
        """Render a text input."""
        return (
            '<div class="field"><label>{label}</label>'
            '<input type="text" name="{name}" value="{val}"></div>\n'
        ).format(label=label, name=name, val=current_value)

    @staticmethod
    def _number_field(name, label, current_value, step=None, min_val=None):
        """Render a number input."""
        attrs = ''
        if step is not None:
            attrs += ' step="{}"'.format(step)
        if min_val is not None:
            attrs += ' min="{}"'.format(min_val)
        return (
            '<div class="field"><label>{label}</label>'
            '<input type="number" name="{name}" value="{val}"{attrs}></div>\n'
        ).format(label=label, name=name, val=current_value, attrs=attrs)

    # ------------------------------------------------------------------
    # Success / reboot page
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_success_html():
        """Return a confirmation page shown after saving."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Configuration Saved</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 { color: #333; text-align: center; }
        .card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .msg { color: #4CAF50; font-size: 18px; margin-bottom: 20px; }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            color: white;
            margin: 6px;
        }
        .btn-reboot { background-color: #f44336; }
        .btn-reboot:hover { background-color: #d32f2f; }
        .btn-back { background-color: #2196F3; }
        .btn-back:hover { background-color: #1976D2; }
    </style>
</head>
<body>
    <h1>AgXRP Configuration</h1>
    <div class="card">
        <p class="msg">Configuration saved successfully.</p>
        <form method="POST" action="/configure/reboot" style="display:inline;"
              onsubmit="return confirm('Are you sure you want to reboot the device?');">
            <button type="submit" class="btn btn-reboot">Reboot to Apply Changes</button>
        </form>
        <a href="/configure" class="btn btn-back">Back to Settings</a>
    </div>
</body>
</html>"""
