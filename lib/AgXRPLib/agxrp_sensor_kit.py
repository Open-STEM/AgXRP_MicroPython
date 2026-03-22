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
from lib.AgXRPLib.agxrp_sensor_resistive_soil import AgXRPResistiveSoilSensor
from lib.AgXRPLib.agxrp_csv_logger import AgXRPCSVLogger

class AgXRPSensorKit:
    """!
    Main sensor kit class that coordinates all sensors, OLED display, and CSV logging.
    
    This class manages the registration and operation of sensors, OLED display,
    and CSV logging. Users register only the components they have available.
    """
    
    def __init__(self, bus0_enabled=True, bus1_enabled=False, i2c_freq=100000):
        """!
        Constructor
        
        @param bus0_enabled: Enable bus 0 (sda=4, scl=5) (default: True)
        @param bus1_enabled: Enable bus 1 (sda=38, scl=39) (default: False)
        @param i2c_freq: I2C frequency in Hz (default: 100000)
        """
        self._i2c_freq = i2c_freq
        
        # Initialize I2C drivers for each bus
        self._i2c_driver_bus0 = None
        self._i2c_driver_bus1 = None
        
        # Bus 0: sda=4, scl=5
        if bus0_enabled:
            print("Initializing I2C bus 0 (sda=4, scl=5)...")
            self._i2c_driver_bus0 = qwiic_i2c.getI2CDriver(sda=4, scl=5, freq=i2c_freq)
            if self._i2c_driver_bus0 is None or (hasattr(self._i2c_driver_bus0, '_i2cbus') and self._i2c_driver_bus0._i2cbus is None):
                print("ERROR: Unable to initialize I2C bus 0")
                self._i2c_driver_bus0 = None
            else:
                print("I2C bus 0 initialized successfully")
        
        # Bus 1: sda=38, scl=39
        if bus1_enabled:
            print("Initializing I2C bus 1 (sda=38, scl=39)...")
            self._i2c_driver_bus1 = qwiic_i2c.getI2CDriver(sda=38, scl=39, freq=i2c_freq)
            if self._i2c_driver_bus1 is None or (hasattr(self._i2c_driver_bus1, '_i2cbus') and self._i2c_driver_bus1._i2cbus is None):
                print("ERROR: Unable to initialize I2C bus 1")
                self._i2c_driver_bus1 = None
            else:
                print("I2C bus 1 initialized successfully")
        
        # Store bus configuration
        self._bus0_enabled = bus0_enabled
        self._bus1_enabled = bus1_enabled
        
        # Registered components
        self.co2_sensor = None
        self.spectral_sensor = None
        self.light_sensor = None
        self.soil_sensors = {}  # Dictionary keyed by sensor_index (1-4)
        self.screen = None
        self._csv_logger = None
        self._oled_current_page = 0
        self._oled_last_page_switch = time.time()
        self._oled_page_interval = 2.0
    
    def _get_i2c_driver(self, bus):
        """!
        Get the I2C driver for the specified bus.
        
        @param bus: Bus number (0 or 1)
        @return I2C driver instance or None if bus is not enabled
        """
        if bus == 0:
            if not self._bus0_enabled:
                print(f"ERROR: Bus 0 is not enabled")
                return None
            return self._i2c_driver_bus0
        elif bus == 1:
            if not self._bus1_enabled:
                print(f"ERROR: Bus 1 is not enabled")
                return None
            return self._i2c_driver_bus1
        else:
            print(f"ERROR: Invalid bus number {bus}. Must be 0 or 1.")
            return None
    
    def register_co2_sensor(self, bus=0):
        """!
        Register the SCD4x CO2 sensor.
        
        @param bus: I2C bus number (0 or 1, default: 0)
        @return **bool** True if registration was successful, False otherwise
        """
        i2c_driver = self._get_i2c_driver(bus)
        if i2c_driver is None:
            print("ERROR: I2C driver not available for bus {}".format(bus))
            return False
        
        print("Registering SCD4x sensor on bus {}...".format(bus))
        self.co2_sensor = AgXRPSensorSCD4x(i2c_driver=i2c_driver)
        
        if not self.co2_sensor.begin():
            print("ERROR: Failed to initialize SCD4x sensor")
            self.co2_sensor = None
            return False
        
        print("SCD4x sensor registered successfully")
        return True
    
    def register_spectral_sensor(self, bus=0):
        """!
        Register the AS7343 spectral sensor.
        
        @param bus: I2C bus number (0 or 1, default: 0)
        @return **bool** True if registration was successful, False otherwise
        """
        i2c_driver = self._get_i2c_driver(bus)
        if i2c_driver is None:
            print("ERROR: I2C driver not available for bus {}".format(bus))
            return False
        
        print("Registering AS7343 sensor on bus {}...".format(bus))
        self.spectral_sensor = AgXRPSensorAS7343(i2c_driver=i2c_driver)
        
        if not self.spectral_sensor.begin():
            print("ERROR: Failed to initialize AS7343 sensor")
            self.spectral_sensor = None
            return False

        self.spectral_sensor.set_led_off()
        
        print("AS7343 sensor registered successfully")
        return True
    
    def register_light_sensor(self, bus=0):
        """!
        Register the VEML ambient light sensor.
        
        @param bus: I2C bus number (0 or 1, default: 0)
        @return **bool** True if registration was successful, False otherwise
        """
        i2c_driver = self._get_i2c_driver(bus)
        if i2c_driver is None:
            print("ERROR: I2C driver not available for bus {}".format(bus))
            return False
        
        print("Registering VEML sensor on bus {}...".format(bus))
        self.light_sensor = AgXRPSensorVEML(i2c_driver=i2c_driver)
        
        if not self.light_sensor.begin():
            print("ERROR: Failed to initialize VEML sensor")
            self.light_sensor = None
            return False
        
        print("VEML sensor registered successfully")
        return True
    
    def register_soil_sensor(self, sensor_index, bus, address=0x37):
        """!
        Register a soil moisture sensor.
        
        @param sensor_index: Sensor index (1-4)
        @param bus: I2C bus number (0 or 1)
        @param address: I2C address (default: 0x37, the default for QwiicCY8CMBR3)
        @return **bool** True if registration was successful, False otherwise
        """
        if sensor_index < 1 or sensor_index > 4:
            print(f"ERROR: Invalid sensor_index {sensor_index}. Must be 1-4.")
            return False
        
        if sensor_index in self.soil_sensors:
            print(f"WARNING: Soil sensor {sensor_index} is already registered. Overwriting...")
        
        i2c_driver = self._get_i2c_driver(bus)
        if i2c_driver is None:
            print(f"ERROR: I2C driver not available for bus {bus}")
            return False
        
        print(f"Registering soil sensor {sensor_index} on bus {bus}, address 0x{address:02X}...")
        self.soil_sensors[sensor_index] = AgXRPSensorSoil(i2c_driver=i2c_driver, address=address)
        
        if not self.soil_sensors[sensor_index].begin():
            print(f"ERROR: Failed to initialize soil sensor {sensor_index}")
            del self.soil_sensors[sensor_index]
            return False
        
        print(f"Soil sensor {sensor_index} registered successfully")
        return True
    
    def register_resistive_soil_sensor(self, sensor_index, bus=0, address=0x28):
        """!
        Register a resistive (Qwiic) soil moisture sensor.
        
        @param sensor_index: Sensor index (1-4)
        @param bus: I2C bus number (0 or 1, default: 0)
        @param address: I2C address (default: 0x28, the Qwiic soil moisture default)
        @return **bool** True if registration was successful, False otherwise
        """
        if sensor_index < 1 or sensor_index > 4:
            print(f"ERROR: Invalid sensor_index {sensor_index}. Must be 1-4.")
            return False
        
        if sensor_index in self.soil_sensors:
            print(f"WARNING: Soil sensor {sensor_index} is already registered. Overwriting...")
        
        i2c_driver = self._get_i2c_driver(bus)
        if i2c_driver is None:
            print(f"ERROR: I2C driver not available for bus {bus}")
            return False
        
        print(f"Registering resistive soil sensor {sensor_index} on bus {bus}, address 0x{address:02X}...")
        self.soil_sensors[sensor_index] = AgXRPResistiveSoilSensor(i2c_driver=i2c_driver, address=address)
        
        if not self.soil_sensors[sensor_index].begin():
            print(f"ERROR: Failed to initialize resistive soil sensor {sensor_index}")
            del self.soil_sensors[sensor_index]
            return False
        
        print(f"Resistive soil sensor {sensor_index} registered successfully")
        return True
    
    def register_screen(self, bus=0, oled_instance=None):
        """!
        Register the OLED display.
        
        @param bus: I2C bus number (0 or 1, default: 0)
        @param oled_instance: Optional existing OLED instance, or None to create one
        @return **bool** True if registration was successful, False otherwise
        """
        if oled_instance is None:
            i2c_driver = self._get_i2c_driver(bus)
            if i2c_driver is None:
                print("ERROR: I2C driver not available for bus {}".format(bus))
                return False
            print("Registering OLED display on bus {}...".format(bus))
            self.screen = qwiic_oled.QwiicLargeOled(i2c_driver=i2c_driver)
        else:
            print("Registering OLED display (using provided instance)...")
            self.screen = oled_instance
        
        if not self.screen.connected:
            print("ERROR: OLED Display isn't connected")
            self.screen = None
            return False
        
        self.screen.begin()
        self.screen.clear(self.screen.ALL)  # Clear the display's memory
        self.screen.display()
        self._oled_current_page = 0
        self._oled_last_page_switch = time.time()
        
        print("OLED display registered successfully")
        return True
    
    def register_csv_logger(self, filename, period_ms, max_rows=0):
        """!
        Register the CSV logger.

        @param filename: Name of the CSV file to write to
        @param period_ms: Logging period in milliseconds
        @param max_rows: Max data rows before rotating to a .bak file (0 = unlimited)
        @return **bool** True if registration was successful, False otherwise
        """
        print(f"Registering CSV logger (file: {filename}, period: {period_ms}ms)...")

        self._csv_logger = AgXRPCSVLogger(filename, period_ms, max_rows=max_rows)
        
        # Set callback to collect data from all sensors
        def collect_sensor_data():
            data = {}
            if self.co2_sensor and self.co2_sensor.is_connected():
                data.update(self.co2_sensor.get_csv_data())
            if self.spectral_sensor and self.spectral_sensor.is_connected():
                data.update(self.spectral_sensor.get_csv_data())
            if self.light_sensor and self.light_sensor.is_connected():
                data.update(self.light_sensor.get_csv_data())
            for sensor_index, sensor in self.soil_sensors.items():
                if sensor and sensor.is_connected():
                    # Prefix data keys with sensor index
                    sensor_data = sensor.get_csv_data()
                    for key, value in sensor_data.items():
                        data[f"{key}_{sensor_index}"] = value
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
        if self.screen is None:
            return
        
        try:
            # Clear the display buffer
            self.screen.clear(self.screen.PAGE)
            
            # Set font to 0 for all text
            self.screen.set_font_type(0)
            
            # Collect display lines from all registered sensors
            all_lines = []
            
            if self.co2_sensor and self.co2_sensor.is_connected():
                all_lines.extend(self.co2_sensor.get_display_lines())
            
            if self.spectral_sensor and self.spectral_sensor.is_connected():
                all_lines.extend(self.spectral_sensor.get_display_lines())
            
            if self.light_sensor and self.light_sensor.is_connected():
                all_lines.extend(self.light_sensor.get_display_lines())
            
            for sensor_index, sensor in sorted(self.soil_sensors.items()):
                if sensor and sensor.is_connected():
                    all_lines.extend(sensor.get_display_lines())
            
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
            
            if total_lines <= lines_per_page:
                total_pages_for_display = 1
            else:
                total_pages_for_display = (total_lines + lines_per_page - 1) // lines_per_page

            display_lines = all_lines[start_index:start_index + lines_per_page]

            # Reserve the last line for a page indicator when there are multiple pages
            if total_pages_for_display > 1:
                display_lines = display_lines[:lines_per_page - 1]
                display_lines.append("Pg {}/{}".format(self._oled_current_page + 1, total_pages_for_display))

            for i, line in enumerate(display_lines):
                self.screen.set_cursor(0, y_positions[i])
                self.screen.print(line)
            
            # Update the display
            self.screen.display()
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
        if self.co2_sensor and self.co2_sensor.is_connected():
            try:
                if self.co2_sensor.update():
                    success = True
            except Exception as e:
                print(f"Error updating SCD4x: {e}")
        
        # Update AS7343
        if self.spectral_sensor and self.spectral_sensor.is_connected():
            try:
                if self.spectral_sensor.update():
                    success = True
            except Exception as e:
                print(f"Error updating AS7343: {e}")
        
        # Update VEML
        if self.light_sensor and self.light_sensor.is_connected():
            try:
                if self.light_sensor.update():
                    success = True
            except Exception as e:
                print(f"Error updating VEML: {e}")
        
        # Update soil sensors
        for sensor_index, sensor in self.soil_sensors.items():
            if sensor and sensor.is_connected():
                try:
                    if sensor.update():
                        success = True
                except Exception as e:
                    print(f"Error updating soil sensor {sensor_index}: {e}")
        
        # Update OLED display
        if self.screen:
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
                if self.co2_sensor and self.co2_sensor.is_connected():
                    sensor_readings.append(f"CO2: {self.co2_sensor.get_co2()} ppm, "
                                         f"Temp: {self.co2_sensor.get_temperature():.1f} C, "
                                         f"Humidity: {self.co2_sensor.get_humidity():.1f} %")
                if self.spectral_sensor and self.spectral_sensor.is_connected():
                    sensor_readings.append(f"B: {int(self.spectral_sensor.get_blue())}, "
                                         f"G: {int(self.spectral_sensor.get_green())}, "
                                         f"R: {int(self.spectral_sensor.get_red())}, "
                                         f"N: {int(self.spectral_sensor.get_nir())}")
                if self.light_sensor and self.light_sensor.is_connected():
                    sensor_readings.append(f"Light: {self.light_sensor.get_ambient_light():.1f} lux")
                for sensor_index, sensor in sorted(self.soil_sensors.items()):
                    if sensor and sensor.is_connected():
                        if sensor.get_sensor_name() == "ResistiveSoil":
                            sensor_readings.append(f"Soil{sensor_index}: {sensor.get_moisture()}%")
                        else:
                            sensor_readings.append(f"Soil{sensor_index}: {sensor.get_moisture():.1f} pF")
                
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

