#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_kit.py
#
# Main AgXRPSensorKit class that coordinates all sensors, OLED display, and CSV logging.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import lib.qwiic_i2c as qwiic_i2c
import lib.AgXRPLib.qwiic_oled as qwiic_oled
import time
import sys

from lib.AgXRPLib.agxrp_sensor_scd4x import AgXRPSensorSCD4x
from lib.AgXRPLib.agxrp_sensor_as7343 import AgXRPSensorAS7343
from lib.AgXRPLib.agxrp_sensor_veml import AgXRPSensorVEML
from lib.AgXRPLib.agxrp_sensor_soil import AgXRPSensorSoil
from lib.AgXRPLib.agxrp_csv_logger import AgXRPCSVLogger

class AgXRPSensorKit:
    """!
    Main sensor kit class that coordinates all sensors, OLED display, and CSV logging.
    
    This class manages the registration and operation of sensors, OLED display,
    and CSV logging. Users register only the components they have available.
    """
    
    def __init__(self, sda_pin=4, scl_pin=5, i2c_freq=100000):
        """!
        Constructor
        
        @param sda_pin: SDA pin number for I2C (default: 4)
        @param scl_pin: SCL pin number for I2C (default: 5)
        @param i2c_freq: I2C frequency in Hz (default: 100000)
        """
        self._sda_pin = sda_pin
        self._scl_pin = scl_pin
        self._i2c_freq = i2c_freq
        
        # Initialize I2C driver
        print("Initializing I2C driver...")
        self._i2c_driver = qwiic_i2c.getI2CDriver(sda=sda_pin, scl=scl_pin, freq=i2c_freq)
        
        if self._i2c_driver is None or (hasattr(self._i2c_driver, '_i2cbus') and self._i2c_driver._i2cbus is None):
            print("ERROR: Unable to initialize I2C driver")
            print("Make sure SDA and SCL pins are correctly specified")
            self._i2c_driver = None
        
        # Registered components
        self._scd4x = None
        self._as7343 = None
        self._veml = None
        self._soil = None
        self._oled = None
        self._csv_logger = None
        self._oled_current_page = 0
        self._oled_last_page_switch = time.time()
        self._oled_page_interval = 2.0
    
    def register_scd4x(self):
        """!
        Register the SCD4x CO2 sensor.
        
        @return **bool** True if registration was successful, False otherwise
        """
        if self._i2c_driver is None:
            print("ERROR: I2C driver not initialized")
            return False
        
        print("Registering SCD4x sensor...")
        self._scd4x = AgXRPSensorSCD4x(i2c_driver=self._i2c_driver)
        
        if not self._scd4x.begin():
            print("ERROR: Failed to initialize SCD4x sensor")
            self._scd4x = None
            return False
        
        print("SCD4x sensor registered successfully")
        return True
    
    def register_as7343(self):
        """!
        Register the AS7343 spectral sensor.
        
        @return **bool** True if registration was successful, False otherwise
        """
        if self._i2c_driver is None:
            print("ERROR: I2C driver not initialized")
            return False
        
        print("Registering AS7343 sensor...")
        self._as7343 = AgXRPSensorAS7343(i2c_driver=self._i2c_driver)
        
        if not self._as7343.begin():
            print("ERROR: Failed to initialize AS7343 sensor")
            self._as7343 = None
            return False
        
        print("AS7343 sensor registered successfully")
        return True
    
    def register_veml(self):
        """!
        Register the VEML ambient light sensor.
        
        @return **bool** True if registration was successful, False otherwise
        """
        if self._i2c_driver is None:
            print("ERROR: I2C driver not initialized")
            return False
        
        print("Registering VEML sensor...")
        self._veml = AgXRPSensorVEML(i2c_driver=self._i2c_driver)
        
        if not self._veml.begin():
            print("ERROR: Failed to initialize VEML sensor")
            self._veml = None
            return False
        
        print("VEML sensor registered successfully")
        return True
    
    def register_soil(self, adc_pin=44):
        """!
        Register the soil moisture sensor.
        
        @param adc_pin: GPIO pin number for ADC (default: 44)
        @return **bool** True if registration was successful, False otherwise
        """
        print("Registering soil sensor...")
        self._soil = AgXRPSensorSoil(i2c_driver=None, adc_pin=adc_pin)
        
        if not self._soil.begin():
            print("ERROR: Failed to initialize soil sensor")
            self._soil = None
            return False
        
        print("Soil sensor registered successfully")
        return True
    
    def register_oled(self, oled_instance=None):
        """!
        Register the OLED display.
        
        @param oled_instance: Optional existing OLED instance, or None to create one
        @return **bool** True if registration was successful, False otherwise
        """
        if self._i2c_driver is None:
            print("ERROR: I2C driver not initialized")
            return False
        
        print("Registering OLED display...")
        
        if oled_instance is None:
            self._oled = qwiic_oled.QwiicLargeOled(i2c_driver=self._i2c_driver)
        else:
            self._oled = oled_instance
        
        if not self._oled.connected:
            print("ERROR: OLED Display isn't connected")
            self._oled = None
            return False
        
        self._oled.begin()
        self._oled.clear(self._oled.ALL)  # Clear the display's memory
        self._oled.display()
        self._oled_current_page = 0
        self._oled_last_page_switch = time.time()
        
        print("OLED display registered successfully")
        return True
    
    def register_csv_logger(self, filename, period_ms):
        """!
        Register the CSV logger.
        
        @param filename: Name of the CSV file to write to
        @param period_ms: Logging period in milliseconds
        @return **bool** True if registration was successful, False otherwise
        """
        print(f"Registering CSV logger (file: {filename}, period: {period_ms}ms)...")
        
        self._csv_logger = AgXRPCSVLogger(filename, period_ms)
        
        # Set callback to collect data from all sensors
        def collect_sensor_data():
            data = {}
            if self._scd4x and self._scd4x.is_connected():
                data.update(self._scd4x.get_csv_data())
            if self._as7343 and self._as7343.is_connected():
                data.update(self._as7343.get_csv_data())
            if self._veml and self._veml.is_connected():
                data.update(self._veml.get_csv_data())
            if self._soil and self._soil.is_connected():
                data.update(self._soil.get_csv_data())
            return data
        
        self._csv_logger.set_sensor_data_callback(collect_sensor_data)
        self._csv_logger.start()
        
        print("CSV logger registered successfully")
        return True
    
    def _update_oled_display(self):
        """!
        Update the OLED display with current sensor readings.
        
        Dynamically determines layout based on which sensors are registered.
        """
        if self._oled is None:
            return
        
        try:
            # Clear the display buffer
            self._oled.clear(self._oled.PAGE)
            
            # Set font to 0 for all text
            self._oled.set_font_type(0)
            
            # Collect display lines from all registered sensors
            all_lines = []
            
            if self._scd4x and self._scd4x.is_connected():
                all_lines.extend(self._scd4x.get_display_lines())
            
            if self._as7343 and self._as7343.is_connected():
                all_lines.extend(self._as7343.get_display_lines())
            
            if self._veml and self._veml.is_connected():
                all_lines.extend(self._veml.get_display_lines())
            
            if self._soil and self._soil.is_connected():
                all_lines.extend(self._soil.get_display_lines())
            
            # Display lines (max 8 lines for 128x64 display with 8px line height)
            y_positions = [0, 8, 16, 24, 32, 40, 48, 56]
            lines_per_page = len(y_positions)
            total_lines = len(all_lines)
            
            if total_lines <= lines_per_page:
                self._oled_current_page = 0
                self._oled_last_page_switch = time.time()
                start_index = 0
            else:
                total_pages = (total_lines + lines_per_page - 1) // lines_per_page
                
                if self._oled_current_page >= total_pages:
                    self._oled_current_page = 0
                
                current_time = time.time()
                if current_time - self._oled_last_page_switch >= self._oled_page_interval:
                    self._oled_current_page = (self._oled_current_page + 1) % total_pages
                    self._oled_last_page_switch = current_time
                
                start_index = self._oled_current_page * lines_per_page
            
            display_lines = all_lines[start_index:start_index + lines_per_page]
            
            for i, line in enumerate(display_lines):
                self._oled.set_cursor(0, y_positions[i])
                self._oled.print(line)
            
            # Update the display
            self._oled.display()
        except Exception as e:
            print(f"Error updating OLED display: {e}")
    
    def update(self):
        """!
        Update all registered sensors and refresh OLED/CSV if registered.
        
        This method should be called periodically in the main loop.
        It handles sensor read failures gracefully.
        
        @return **bool** True if at least one sensor was updated successfully
        """
        success = False
        
        # Update SCD4x
        if self._scd4x and self._scd4x.is_connected():
            try:
                if self._scd4x.update():
                    success = True
            except Exception as e:
                print(f"Error updating SCD4x: {e}")
        
        # Update AS7343
        if self._as7343 and self._as7343.is_connected():
            try:
                if self._as7343.update():
                    success = True
            except Exception as e:
                print(f"Error updating AS7343: {e}")
        
        # Update VEML
        if self._veml and self._veml.is_connected():
            try:
                if self._veml.update():
                    success = True
            except Exception as e:
                print(f"Error updating VEML: {e}")
        
        # Update Soil
        if self._soil and self._soil.is_connected():
            try:
                if self._soil.update():
                    success = True
            except Exception as e:
                print(f"Error updating soil sensor: {e}")
        
        # Update OLED display
        if self._oled:
            self._update_oled_display()
        
        # CSV logging is handled by the timer callback automatically
        
        return success
    
    def run(self):
        """!
        Main loop that continuously updates sensors and displays data.
        
        This method runs indefinitely until interrupted (Ctrl+C).
        """
        print("\nStarting AgXRPSensorKit main loop...")
        print("(Press Ctrl+C to exit)\n")
        
        try:
            while True:
                self.update()
                
                # Print to console for debugging
                sensor_readings = []
                if self._scd4x and self._scd4x.is_connected():
                    sensor_readings.append(f"CO2: {self._scd4x.get_co2()} ppm, "
                                         f"Temp: {self._scd4x.get_temperature():.1f} C, "
                                         f"Humidity: {self._scd4x.get_humidity():.1f} %")
                if self._as7343 and self._as7343.is_connected():
                    sensor_readings.append(f"B: {int(self._as7343.get_blue())}, "
                                         f"G: {int(self._as7343.get_green())}, "
                                         f"R: {int(self._as7343.get_red())}, "
                                         f"N: {int(self._as7343.get_nir())}")
                if self._veml and self._veml.is_connected():
                    sensor_readings.append(f"Light: {self._veml.get_ambient_light():.1f} lux")
                if self._soil and self._soil.is_connected():
                    sensor_readings.append(f"Soil: {self._soil.get_moisture():.1f}%")
                
                if sensor_readings:
                    print(" | ".join(sensor_readings))
                
                # SCD4x has data ready every 5 seconds, so check frequently
                # AS7343 and VEML can be read more frequently
                time.sleep(0.5)
        
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down AgXRPSensorKit...")
            if self._csv_logger:
                self._csv_logger.stop()
            print("AgXRPSensorKit stopped")
            sys.exit(0)

