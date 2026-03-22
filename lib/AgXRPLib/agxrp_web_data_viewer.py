#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_web_data_viewer.py
#
# Web-based data viewer for AgXRP Sensor Kit.
# Displays CSV log data as a table and provides a download button.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import json
import os
from phew import server


class AgXRPWebDataViewer:
    """!
    Web data viewer page that displays CSV log file contents as a table
    and provides a download button for each file.
    """

    def __init__(self, config_path="config.json"):
        """!
        Constructor.

        @param config_path  Path to the JSON configuration file (used to
                            discover CSV filenames).
        """
        self._config_path = config_path

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def register_routes(self):
        """!
        Register routes with the phew server.
        """
        server.add_route("/data", self._handle_data, methods=["GET"])
        server.add_route("/data/download", self._handle_download, methods=["GET"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_config(self):
        with open(self._config_path, "r") as f:
            return json.load(f)

    def _get_csv_files(self):
        """Return list of CSV filenames referenced in config."""
        cfg = self._load_config()
        files = []

        # Sensor logger
        csv_cfg = cfg.get("sensors", {}).get("csv_logger", {})
        if csv_cfg.get("enabled", False):
            fn = csv_cfg.get("filename", "sensor_log.csv")
            files.append(("Sensor Log", fn))

        # Pump logs
        for pump_cfg in cfg.get("controller", {}).get("pumps", []):
            if pump_cfg.get("enabled", False) and pump_cfg.get("csv_filename"):
                idx = pump_cfg.get("pump_index", "?")
                files.append((f"Water Pump {idx} Log", pump_cfg["csv_filename"]))

        return files

    @staticmethod
    def _file_exists(filename):
        try:
            return (os.stat(filename)[0] & 0x4000) == 0
        except OSError:
            return False

    def _read_csv(self, filename, max_rows=500):
        """Read a CSV file and return (headers, rows). Limits to last max_rows."""
        headers = []
        rows = []
        try:
            with open(filename, "r") as f:
                first_line = f.readline().strip()
                if first_line:
                    headers = first_line.split(",")
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(line.split(","))
        except OSError:
            return headers, rows

        # Keep only the last max_rows (most recent data)
        if len(rows) > max_rows:
            rows = rows[-max_rows:]

        return headers, rows

    # ------------------------------------------------------------------
    # Request handlers
    # ------------------------------------------------------------------

    def _handle_data(self, request):
        """Serve the data viewer page."""
        # Check if a specific file is requested
        selected_file = request.query.get("file", "")
        html = self._generate_html(selected_file)
        return html, 200, "text/html"

    def _handle_download(self, request):
        """Serve a CSV file for download."""
        filename = request.query.get("file", "")
        # Validate against the known list of CSV files to prevent path traversal
        allowed = [fn for _, fn in self._get_csv_files()]
        if not filename or filename not in allowed:
            return "File not found", 404, "text/plain"

        return server.FileResponse(filename)

    # ------------------------------------------------------------------
    # HTML generation
    # ------------------------------------------------------------------

    def _generate_html(self, selected_file=""):
        csv_files = self._get_csv_files()

        html = self._html_head()
        html += '<body>\n'
        html += '<div class="header">\n'
        html += '  <h1>AgXRP Data Viewer</h1>\n'
        html += '  <div class="nav-links">\n'
        html += '    <a href="/" class="nav-link">Dashboard</a>\n'
        html += '    <a href="/configure" class="nav-link">Configure</a>\n'
        html += '  </div>\n'
        html += '</div>\n'

        if not csv_files:
            html += '<div class="card"><p>No CSV log files are configured. '
            html += 'Enable the CSV logger or pump logging in the '
            html += '<a href="/configure">configuration page</a>.</p></div>\n'
            html += '</body></html>'
            return html

        # File selector
        html += '<div class="card">\n'
        html += '  <h2>Select Log File</h2>\n'
        for label, fn in csv_files:
            exists = self._file_exists(fn)
            active = ' active' if fn == selected_file else ''
            if exists:
                html += f'  <a href="/data?file={fn}" class="file-btn{active}">{label}</a>\n'
            else:
                html += f'  <span class="file-btn disabled">{label} (no data yet)</span>\n'
        html += '</div>\n'

        # Auto-select first available file if none selected
        if not selected_file:
            for _, fn in csv_files:
                if self._file_exists(fn):
                    selected_file = fn
                    break

        # Display selected file
        if selected_file and self._file_exists(selected_file):
            # Find label
            label = selected_file
            for l, fn in csv_files:
                if fn == selected_file:
                    label = l
                    break

            headers, rows = self._read_csv(selected_file)

            html += '<div class="card">\n'
            html += f'  <h2>{label}</h2>\n'
            html += f'  <p class="file-info">{selected_file} &mdash; {len(rows)} rows</p>\n'
            html += f'  <a href="/data/download?file={selected_file}" '
            html += 'class="btn btn-download">Download CSV</a>\n'

            if headers:
                html += '  <div class="table-wrap">\n'
                html += '  <table>\n'
                html += '    <thead><tr>\n'
                for h in headers:
                    html += f'      <th>{h.strip()}</th>\n'
                html += '    </tr></thead>\n'
                html += '    <tbody>\n'

                # Show rows in reverse chronological order (newest first)
                for row in reversed(rows):
                    html += '      <tr>\n'
                    for cell in row:
                        html += f'        <td>{cell.strip()}</td>\n'
                    html += '      </tr>\n'

                html += '    </tbody>\n'
                html += '  </table>\n'
                html += '  </div>\n'
            else:
                html += '  <p>File is empty.</p>\n'

            html += '</div>\n'

        html += '</body></html>'
        return html

    @staticmethod
    def _html_head():
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AgXRP Data Viewer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
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
        .file-btn {
            display: inline-block;
            padding: 8px 16px;
            margin: 4px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 14px;
            background-color: #e0e0e0;
            color: #333;
        }
        .file-btn:hover { background-color: #bdbdbd; }
        .file-btn.active {
            background-color: #2196F3;
            color: white;
        }
        .file-btn.disabled {
            background-color: #eee;
            color: #999;
        }
        .file-info {
            color: #777;
            font-size: 13px;
            margin: 4px 0 12px 0;
        }
        .btn-download {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .btn-download:hover { background-color: #45a049; }
        .table-wrap {
            overflow-x: auto;
            margin-top: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td {
            padding: 6px 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
            white-space: nowrap;
        }
        th {
            background-color: #f5f5f5;
            color: #555;
            font-weight: bold;
            position: sticky;
            top: 0;
        }
        tr:hover { background-color: #f9f9f9; }
    </style>
</head>
"""
