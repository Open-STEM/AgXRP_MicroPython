#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_veml.py
#
# Wrapper class for the VEML ambient light sensor.
# Provides a unified interface for the AgXRPSensorKit.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

from lib.AgXRPLib.qwiic_veml import QwiicVEML
from lib.AgXRPLib.agxrp_sensor import AgXRPSensor

class AgXRPSensorVEML(AgXRPSensor):
    """!
    Wrapper class for the Qwiic VEML ambient light sensor.
    
    This class wraps the QwiicVEML sensor and provides a common interface
    for reading ambient light values in lux.
    """
    
    def __init__(self, i2c_driver=None):
        """!
        Constructor
        
        @param i2c_driver: I2C driver instance to use
        """
        super().__init__(i2c_driver)
        self._ambient_light = 0.0
    
    def begin(self):
        """!
        Initialize the VEML sensor.
        
        @return **bool** True if initialization was successful, False otherwise
        """
        try:
            self._sensor = QwiicVEML(i2c_driver=self._i2c_driver)
            
            if not self._sensor.is_connected():
                return False
            
            if not self._sensor.begin():
                return False
            
            self._connected = True
            return True
        except Exception as e:
            print(f"Error initializing VEML: {e}")
            return False
    
    def update(self):
        """!
        Read the latest sensor data.
        
        @return **bool** True if data was read successfully, False otherwise
        """
        if not self._connected or self._sensor is None:
            return False
        
        try:
            self._ambient_light = self._sensor.read_light()
            return True
        except Exception as e:
            print(f"Error reading VEML: {e}")
            return False
    
    def get_display_lines(self):
        """!
        Get formatted strings for OLED display.
        
        @return **list** List of strings for display
        """
        return [f"Light: {self._ambient_light:.1f} lux"]
    
    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.
        
        @return **dict** Dictionary with sensor values
        """
        return {
            "ambient_light": self._ambient_light
        }
    
    def get_sensor_name(self):
        """!
        Get the sensor identifier name.
        
        @return **str** Sensor name
        """
        return "VEML"
    
    def get_ambient_light(self):
        """!
        Get the current ambient light reading.
        
        @return **float** Ambient light in lux
        """
        return self._ambient_light

