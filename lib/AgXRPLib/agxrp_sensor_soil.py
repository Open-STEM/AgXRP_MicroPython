#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_soil.py
#
# Wrapper class for the QwiicCY8CMBR3 capacitive soil moisture sensor.
# Provides a unified interface for the AgXRPSensorKit.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

from lib.AgXRPLib.agxrp_sensor import AgXRPSensor
from lib.AgXRPLib.qwiic_cy8cmbr3 import QwiicCY8CMBR3

class AgXRPSensorSoil(AgXRPSensor):
    """!
    Wrapper class for the QwiicCY8CMBR3 capacitive soil moisture sensor.
    
    This class provides a common interface for reading soil moisture values
    from a QwiicCY8CMBR3 capacitive sensor connected via I2C.
    """
    
    def __init__(self, i2c_driver=None, address=0x37):
        """!
        Constructor
        
        @param i2c_driver: I2C driver instance
        @param address: I2C address (default: 0x37, the default for QwiicCY8CMBR3)
        """
        super().__init__(i2c_driver)
        self._address = address
        self._sensor = None
        self._moisture = 0.0  # Capacitance in pF
        self._raw_value = 0.0  # Raw capacitance in pF
    
    def begin(self):
        """!
        Initialize the soil sensor.
        
        @return **bool** True if initialization was successful, False otherwise
        """
        try:
            # Create QwiicCY8CMBR3 instance
            self._sensor = QwiicCY8CMBR3(address=self._address, i2c_driver=self._i2c_driver)
            
            # Check if connected
            if not self._sensor.is_connected():
                print(f"ERROR: QwiicCY8CMBR3 sensor not connected at address 0x{self._address:02X}")
                self._connected = False
                return False
            
            # Initialize the sensor
            if not self._sensor.begin():
                print(f"ERROR: Failed to initialize QwiicCY8CMBR3 sensor at address 0x{self._address:02X}")
                self._connected = False
                return False
            
            self._connected = True
            return True
        except Exception as e:
            print(f"Error initializing soil sensor: {e}")
            self._connected = False
            return False
    
    def update(self):
        """!
        Read the latest sensor data.
        
        Reads the capacitance value from the sensor in picofarads (pF).
        
        @return **bool** True if data was read successfully, False otherwise
        """
        if not self._connected or self._sensor is None:
            return False
        
        try:
            # Read capacitance in pF
            self._raw_value = self._sensor.get_capacitance_pf()
            self._moisture = self._raw_value  # Store as pF for now
            
            return True
        except Exception as e:
            print(f"Error reading soil sensor: {e}")
            return False
    
    def get_display_lines(self):
        """!
        Get formatted strings for OLED display.
        
        @return **list** List of strings for display
        """
        return [
            f"Soil: {self._moisture:.1f} pF",
            #f"Addr: 0x{self._address:02X}"
        ]
    
    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.
        
        @return **dict** Dictionary with sensor values
        """
        return {
            "soil_moisture": self._moisture,
            "soil_raw": self._raw_value
        }
    
    def get_sensor_name(self):
        """!
        Get the sensor identifier name.
        
        @return **str** Sensor name
        """
        return "Soil"
    
    def get_moisture(self):
        """!
        Get the current soil moisture reading.
        
        @return **float** Capacitance in picofarads (pF)
        """
        return self._moisture
    
    def get_raw_value(self):
        """!
        Get the raw capacitance value.
        
        @return **float** Raw capacitance in picofarads (pF)
        """
        return self._raw_value
    
    def set_led(self, enable):
        """!
        Enable or disable the LED on the sensor.
        
        @param enable: If True, turn LED on; if False, turn LED off
        @return **bool** True if successful, False otherwise
        """
        if not self._connected or self._sensor is None:
            print("ERROR: Sensor not connected")
            return False
        
        try:
            if enable:
                return self._sensor.led_on(True)
            else:
                return self._sensor.led_off()
        except Exception as e:
            print(f"Error setting LED: {e}")
            return False
