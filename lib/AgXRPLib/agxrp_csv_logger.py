#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_csv_logger.py
#
# CSV logger class for periodic logging of sensor data.
# Uses Micropython Timer for periodic logging.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import time

try:
    from machine import Timer, RTC
    MICROPYTHON = True
except ImportError:
    # Fallback for non-Micropython environments (for testing)
    MICROPYTHON = False
    import threading
    from datetime import datetime

class AgXRPCSVLogger:
    """!
    CSV logger for periodic logging of sensor data.
    
    This class manages periodic CSV file logging using a Micropython Timer.
    It collects data from all registered sensors and writes it to a CSV file
    at specified intervals.
    """
    
    def __init__(self, filename, period_ms, max_rows=0):
        """!
        Constructor

        @param filename: Name of the CSV file to write to
        @param period_ms: Logging period in milliseconds
        @param max_rows: Maximum number of data rows before rotating (0 = unlimited)
        """
        self._filename = filename
        self._period_ms = period_ms
        self._max_rows = max_rows
        self._row_count = self._count_existing_rows()
        self._timer = None
        self._header_written = False
        self._sensor_data_callback = None
        self._running = False
    
    def _count_existing_rows(self):
        """Count data rows in an existing CSV file (excluding header)."""
        try:
            count = 0
            with open(self._filename, 'r') as f:
                for _ in f:
                    count += 1
            return max(0, count - 1)  # subtract header row
        except OSError:
            return 0

    def _rotate(self):
        """Rename current log to .bak and start a fresh file."""
        import os
        try:
            bak = self._filename + ".bak"
            # Remove old backup if it exists
            try:
                os.remove(bak)
            except OSError:
                pass
            os.rename(self._filename, bak)
            print(f"CSV log rotated: {self._filename} -> {bak}")
        except Exception as e:
            print(f"Error rotating CSV log: {e}")
        self._header_written = False
        self._row_count = 0

    def set_sensor_data_callback(self, callback):
        """!
        Set the callback function to collect sensor data.
        
        The callback should return a dictionary with all sensor data.
        
        @param callback: Function that returns a dict of sensor data
        """
        self._sensor_data_callback = callback
    
    def _get_datetime_string(self):
        """!
        Get current date/time as a formatted string.
        
        Uses RTC in Micropython, or datetime in standard Python.
        
        @return **str** Formatted datetime string (YYYY-MM-DD HH:MM:SS)
        """
        if MICROPYTHON:
            try:
                rtc = RTC()
                dt = rtc.datetime()
                # RTC.datetime() returns: (year, month, day, weekday, hours, minutes, seconds, subseconds)
                return f"{dt[0]:04d}-{dt[1]:02d}-{dt[2]:02d} {dt[4]:02d}:{dt[5]:02d}:{dt[6]:02d}"
            except Exception as e:
                print(f"Error getting RTC datetime: {e}")
                return "0000-00-00 00:00:00"
        else:
            # Fallback for non-Micropython
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _write_header(self, fieldnames):
        """!
        Write CSV header row.
        
        @param fieldnames: List of column names
        """
        try:
            with open(self._filename, 'w') as f:
                f.write(','.join(fieldnames) + '\n')
            self._header_written = True
        except Exception as e:
            print(f"Error writing CSV header: {e}")
    
    def _write_row(self, data_dict):
        """!
        Write a data row to the CSV file.
        
        @param data_dict: Dictionary of sensor data
        """
        try:
            # Append mode - header should already be written
            with open(self._filename, 'a') as f:
                # Always start with datetime string from RTC
                row = [self._get_datetime_string()]
                
                # Add sensor values in consistent order
                for key in sorted(data_dict.keys()):
                    row.append(str(data_dict[key]))
                
                f.write(','.join(row) + '\n')
        except Exception as e:
            print(f"Error writing CSV row: {e}")
    
    def _timer_callback(self, timer=None):
        """!
        Timer callback function that collects and logs data.
        
        @param timer: Timer object (for Micropython)
        """
        if not self._running or self._sensor_data_callback is None:
            return
        
        try:
            # Collect data from all sensors
            data_dict = self._sensor_data_callback()
            
            if data_dict:
                # Rotate if max_rows limit reached
                if self._max_rows > 0 and self._row_count >= self._max_rows:
                    self._rotate()

                # Write header if not already written
                if not self._header_written:
                    # Create fieldnames list: datetime + sorted sensor keys
                    fieldnames = ['datetime'] + sorted(data_dict.keys())
                    self._write_header(fieldnames)

                # Write data row
                self._write_row(data_dict)
                self._row_count += 1
        except Exception as e:
            print(f"Error in CSV logger callback: {e}")
    
    def start(self):
        """!
        Start the periodic logging timer.
        """
        if self._running:
            return
        
        self._running = True
        
        if MICROPYTHON:
            # Micropython Timer
            self._timer = Timer(-1)  # Virtual timer
            self._timer.init(
                period=self._period_ms,
                mode=Timer.PERIODIC,
                callback=self._timer_callback
            )
        else:
            # Fallback for non-Micropython (for testing)
            def periodic_log():
                while self._running:
                    self._timer_callback()
                    time.sleep(self._period_ms / 1000.0)
            
            self._timer = threading.Thread(target=periodic_log, daemon=True)
            self._timer.start()
    
    def stop(self):
        """!
        Stop the periodic logging timer.
        """
        self._running = False
        
        if self._timer:
            if MICROPYTHON:
                self._timer.deinit()
            self._timer = None

