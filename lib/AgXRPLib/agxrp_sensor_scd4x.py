#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_scd4x.py
#
# Wrapper class for the SCD4x CO2 sensor.
# Provides a unified interface for the AgXRPSensorKit.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

from lib.AgXRPLib.qwiic_scd4x import QwiicSCD4x
from lib.AgXRPLib.agxrp_sensor import AgXRPSensor

class AgXRPSensorSCD4x(AgXRPSensor):
    """!
    Wrapper class for the Qwiic SCD4x CO2 sensor.
    
    This class wraps the QwiicSCD4x sensor and provides a common interface
    for reading CO2, temperature, and humidity values.
    """
    
    def __init__(self, i2c_driver=None):
        """!
        Constructor
        
        @param i2c_driver: I2C driver instance to use
        """
        super().__init__(i2c_driver)
        self._co2 = 0
        self._temperature = 0.0
        self._humidity = 0.0
    
    def begin(self):
        """!
        Initialize the SCD4x sensor.
        
        @return **bool** True if initialization was successful, False otherwise
        """
        try:
            self._sensor = QwiicSCD4x(i2c_driver=self._i2c_driver)
            
            if not self._sensor.is_connected():
                return False
            
            if not self._sensor.begin():
                return False
            
            self._connected = True
            return True
        except Exception as e:
            print(f"Error initializing SCD4x: {e}")
            return False
    
    def update(self):
        """!
        Read the latest sensor data.
        
        The SCD4x provides new data approximately every 5 seconds.
        This method will return False if new data is not yet available.
        
        @return **bool** True if new data was read, False otherwise
        """
        if not self._connected or self._sensor is None:
            return False
        
        try:
            if self._sensor.read_measurement():
                self._co2 = self._sensor.get_co2()
                self._temperature = self._sensor.get_temperature()
                self._humidity = self._sensor.get_humidity()
                return True
            return False
        except Exception as e:
            print(f"Error reading SCD4x: {e}")
            return False
    
    def get_display_lines(self):
        """!
        Get formatted strings for OLED display.
        
        @return **list** List of strings for display
        """
        return [
            f"CO2: {self._co2} ppm",
            f"Temp: {self._temperature:.1f} C",
            f"Humidity: {self._humidity:.1f} %"
        ]
    
    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.
        
        @return **dict** Dictionary with sensor values
        """
        return {
            "co2": self._co2,
            "temperature": self._temperature,
            "humidity": self._humidity
        }
    
    def get_sensor_name(self):
        """!
        Get the sensor identifier name.
        
        @return **str** Sensor name
        """
        return "SCD4x"
    
    def get_co2(self):
        """!
        Get the current CO2 reading.
        
        @return **int** CO2 value in ppm
        """
        return self._co2
    
    def get_temperature(self):
        """!
        Get the current temperature reading.
        
        @return **float** Temperature in degrees Celsius
        """
        return self._temperature
    
    def get_humidity(self):
        """!
        Get the current humidity reading.
        
        @return **float** Humidity percentage
        """
        return self._humidity

