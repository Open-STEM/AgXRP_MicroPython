#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_water_pump.py
#
# AgXRPWaterPump class for controlling peristaltic pumps using encoded motors.
#-------------------------------------------------------------------------------

from lib.XRPLib.encoded_motor import EncodedMotor
from machine import Timer, RTC
import micropython
import time
import os

class AgXRPWaterPump:
    """!
    Class for controlling a peristaltic pump using an encoded motor.
    
    Each instance controls a single pump. Create separate instances for left and right pumps.
    """
    
    def __init__(self, index: int=1, csv_filename: str="water_pump_log.csv"):
        """!
        Initialize the water pump with a specific motor index.
        
        :param index: The motor index (1 for left, 2 for right, 3 for motor 3, 4 for motor 4)
        :type index: int
        :param csv_filename: Name of the CSV file to log watering events to
        :type csv_filename: str
        """
        self._motor = EncodedMotor.get_default_encoded_motor(index=index)
        self._timer = Timer(-1)  # Virtual timer for time-based control
        self._current_effort = 0.0
        self._csv_filename = csv_filename
        # MicroPython on RP2040 (such as RP2350) may not have os.path.exists.
        # Instead, try opening the file to see if it exists.
        self._header_written = False
        if csv_filename:
            try:
                with open(csv_filename, 'r') as f:
                    self._header_written = True
            except OSError:
                self._header_written = False
    
    def _get_datetime_string(self):
        """!
        Get current date/time as a formatted string using RTC.
        
        :return: Formatted datetime string (YYYY-MM-DD HH:MM:SS)
        :rtype: str
        """
        try:
            rtc = RTC()
            dt = rtc.datetime()
            # RTC.datetime() returns: (year, month, day, weekday, hours, minutes, seconds, subseconds)
            return f"{dt[0]:04d}-{dt[1]:02d}-{dt[2]:02d} {dt[4]:02d}:{dt[5]:02d}:{dt[6]:02d}"
        except Exception as e:
            print(f"Error getting RTC datetime: {e}")
            return "0000-00-00 00:00:00"
    
    def _write_csv_header(self):
        """!
        Write CSV header row if it doesn't exist.
        """
        if self._header_written or not self._csv_filename:
            return
        
        try:
            with open(self._csv_filename, 'w') as f:
                f.write('datetime,revolutions,duration_seconds, soil_moisture\n')
            self._header_written = True
        except Exception as e:
            print(f"Error writing CSV header: {e}")
    
    def _log_to_csv(self, revolutions: float, duration_seconds: float, soil_moisture: float=None):
        """!
        Log a watering event to the CSV file.
        
        :param revolutions: Number of pump revolutions (0 if time-based)
        :type revolutions: float
        :param duration_seconds: Duration the pump ran in seconds
        :type duration_seconds: float
        :param soil_moisture: Soil moisture as a percentage
        :type soil_moisture: float
        """
        if not self._csv_filename:
            return
        
        try:
            # Write header if needed
            self._write_csv_header()
            
            # Append data row
            with open(self._csv_filename, 'a') as f:
                datetime_str = self._get_datetime_string()
                if soil_moisture is not None:
                    f.write(f'{datetime_str},{revolutions},{duration_seconds},{soil_moisture}\n')
                else:
                    f.write(f'{datetime_str},{revolutions},{duration_seconds}\n')
        except Exception as e:
            print(f"Error writing to CSV: {e}")
        
    def set_pump_effort(self, effort: float, time_ms: float = 0, log: bool = False, soil_moisture: float = None):
        """!
        Set the effort (power) for the pump.
        
        :param effort: The effort to set the pump to, from -1 to 1
        :type effort: float
        :param time_ms: Time in milliseconds to run the pump. If 0, the pump runs indefinitely.
        :type time_ms: float
        :param log: Whether to log the watering event to the CSV file
        :type log: bool
        :param soil_moisture: Soil moisture as a percentage
        :type soil_moisture: float
        """
        # Stop any existing timer
        try:
            self._timer.deinit()
        except:
            pass
        
        self._current_effort = effort
        self._motor.set_effort(effort)
        
        # If time_ms is 0, run indefinitely (no timer)
        if time_ms > 0:
            # Record start time for logging
            start_time = time.time()
            
            # Use ONE_SHOT mode to stop after specified time
            def stop_callback(timer):
                self._motor.set_effort(0)
                self._current_effort = 0.0
                # Log to CSV (0 revolutions for time-based pumping)
                actual_duration = time.time() - start_time
                if log and soil_moisture is not None:
                    self._log_to_csv(0.0, actual_duration, soil_moisture)
                elif log:
                    self._log_to_csv(0.0, actual_duration)
                else:
                    pass
                timer.deinit()
            
            def scheduled_stop_callback(_):
                stop_callback(self._timer)

            self._timer.init(mode=Timer.ONE_SHOT,
                             period=int(time_ms),
                             callback=lambda t: micropython.schedule(scheduled_stop_callback, 0))
    
    def stop_pump(self):
        """!
        Stop the pump immediately.
        """
        # Stop the timer if running
        try:
            self._timer.deinit()
        except:
            pass
        
        self._motor.set_effort(0)
        self._current_effort = 0.0
    
    def pump_water(self, revolutions: float, effort: float = 0.5, log: bool = False, soil_moisture: float = None):
        """!
        Pump water for a specified number of pump revolutions.
        
        Accounts for the 26:3 gear ratio, so the motor must turn revolutions * (26/3) times
        to achieve the desired pump revolutions.
        
        :param revolutions: Number of pump revolutions to perform (positive for forward, negative for reverse)
        :type revolutions: float
        :param effort: The effort to use for pumping, from 0 to 1 (default: 0.5)
        :type effort: float
        :param log: Whether to log the watering event to the CSV file
        :type log: bool
        :param soil_moisture: Soil moisture as a percentage
        :type soil_moisture: float
        """
        # Stop any existing timer
        try:
            self._timer.deinit()
        except:
            pass
        
        # Record start time for logging
        start_time = time.time()
        
        # Determine direction based on sign of revolutions
        direction = 1 if revolutions >= 0 else -1
        target_revolutions = abs(revolutions)
        
        # Calculate target motor revolutions accounting for gear ratio (26:3)
        # Motor must turn 26/12 times for each pump revolution
        gear_ratio = 26.0 / 12.0
        target_motor_revolutions = target_revolutions * gear_ratio
        
        # Reset encoder position to start from zero
        self._motor.reset_encoder_position()
        
        # Set effort with appropriate direction
        pump_effort = effort * direction
        self._motor.set_effort(pump_effort)
        self._current_effort = pump_effort
        
        # Monitor position until target is reached
        while True:
            current_position = abs(self._motor.get_position())
            if current_position >= target_motor_revolutions:
                break
            time.sleep(0.01)  # Small delay to avoid busy waiting
        
        # Stop the motor once target is reached
        self._motor.set_effort(0)
        self._current_effort = 0.0
        
        # Calculate duration and log to CSV
        duration_seconds = time.time() - start_time
        if log and soil_moisture is not None:
            self._log_to_csv(revolutions, duration_seconds, soil_moisture)
        elif log:
            self._log_to_csv(revolutions, duration_seconds)
        else:
            pass