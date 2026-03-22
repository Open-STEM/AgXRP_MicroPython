#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_as7343.py
#
# Wrapper class for the AS7343 spectral sensor.
# Provides a unified interface for the AgXRPSensorKit.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

from lib.AgXRPLib.qwiic_as7343 import QwiicAS7343
from lib.AgXRPLib.agxrp_sensor import AgXRPSensor

class AgXRPSensorAS7343(AgXRPSensor):
    """!
    Wrapper class for the Qwiic AS7343 spectral sensor.
    
    This class wraps the QwiicAS7343 sensor and provides a common interface
    for reading spectral data (Blue, Green, Red, NIR values).
    """
    
    def __init__(self, i2c_driver=None):
        """!
        Constructor
        
        @param i2c_driver: I2C driver instance to use
        """
        super().__init__(i2c_driver)
        self._blue = 0
        self._green = 0
        self._red = 0
        self._nir = 0
    
    def begin(self):
        """!
        Initialize the AS7343 sensor.
        
        This includes powering on, setting AutoSmux to 18 channels,
        and enabling spectral measurements.
        
        @return **bool** True if initialization was successful, False otherwise
        """
        try:
            self._sensor = QwiicAS7343(i2c_driver=self._i2c_driver)
            
            if not self._sensor.is_connected():
                return False
            
            if not self._sensor.begin():
                return False
            
            # Power on the device
            self._sensor.power_on()
            
            # Set AutoSmux to output all 18 channels
            if not self._sensor.set_auto_smux(self._sensor.kAutoSmux18Channels):
                return False
            
            # Enable spectral measurements
            if not self._sensor.spectral_measurement_enable():
                return False
            
            self._connected = True
            return True
        except Exception as e:
            print(f"Error initializing AS7343: {e}")
            return False
    
    def update(self):
        """!
        Read the latest sensor data.
        
        Reads all spectral channels and calculates Blue, Green, Red, and NIR values.
        
        @return **bool** True if data was read successfully, False otherwise
        """
        if not self._connected or self._sensor is None:
            return False
        
        try:
            # Read all spectral data
            self._sensor.read_all_spectral_data()
            
            # Calculate the 4 values
            # 1) Blue: average of kChPurpleF1405nm, kChDarkBlueF2425nm, kChBlueFz450nm, 
            #          kChLightBlueF3475nm, kChBlueF4515nm
            blue_channels = [
                self._sensor.get_data(self._sensor.kChPurpleF1405nm),
                self._sensor.get_data(self._sensor.kChDarkBlueF2425nm),
                self._sensor.get_data(self._sensor.kChBlueFz450nm),
                self._sensor.get_data(self._sensor.kChLightBlueF3475nm),
                self._sensor.get_data(self._sensor.kChBlueF4515nm)
            ]
            blue_value = sum(blue_channels) / len(blue_channels)
            
            # 2) Green: average of kChGreenF5550nm, kChGreenFy555nm
            green_channels = [
                self._sensor.get_data(self._sensor.kChGreenF5550nm),
                self._sensor.get_data(self._sensor.kChGreenFy555nm)
            ]
            green_value = sum(green_channels) / len(green_channels)
            
            # 3) Red: average of kChBrownF6640nm, kChRedF7690nm, kChDarkRedF8745nm
            red_channels = [
                self._sensor.get_data(self._sensor.kChBrownF6640nm),
                self._sensor.get_data(self._sensor.kChRedF7690nm),
                self._sensor.get_data(self._sensor.kChDarkRedF8745nm)
            ]
            red_value = sum(red_channels) / len(red_channels)
            
            # 4) NIR: kChNir855nm
            nir_value = self._sensor.get_data(self._sensor.kChNir855nm)
            
            # Cap values at 999
            self._blue = min(blue_value, 999)
            self._green = min(green_value, 999)
            self._red = min(red_value, 999)
            self._nir = min(nir_value, 999)
            
            return True
        except Exception as e:
            print(f"Error reading AS7343: {e}")
            return False
    
    def get_display_lines(self):
        """!
        Get formatted strings for OLED display with bar graphs.
        
        @return **list** List of strings for display
        """
        def format_with_bar(label, value, max_value=999, max_bar_length=14):
            """Format value with bar graph"""
            bar_length = int((value / max_value) * max_bar_length)
            bar = "#" * bar_length
            return f"{label}: {int(value):3d} {bar}"
        
        return [
            format_with_bar("B", self._blue),
            format_with_bar("G", self._green),
            format_with_bar("R", self._red),
            format_with_bar("N", self._nir)
        ]
    
    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.
        
        @return **dict** Dictionary with sensor values
        """
        return {
            "blue": self._blue,
            "green": self._green,
            "red": self._red,
            "nir": self._nir
        }
    
    def get_sensor_name(self):
        """!
        Get the sensor identifier name.
        
        @return **str** Sensor name
        """
        return "AS7343"
    
    def get_blue(self):
        """!
        Get the current Blue value.
        
        @return **float** Blue value
        """
        return self._blue
    
    def get_green(self):
        """!
        Get the current Green value.
        
        @return **float** Green value
        """
        return self._green
    
    def get_red(self):
        """!
        Get the current Red value.
        
        @return **float** Red value
        """
        return self._red
    
    def get_nir(self):
        """!
        Get the current NIR value.
        
        @return **float** NIR value
        """
        return self._nir

    def set_led_on(self):
        """!
        Set the LED on.
        
        @return **bool** True if successful, False otherwise
        """
        return self._sensor.set_led_on()
    
    def set_led_off(self):
        """!
        Set the LED off.
        
        @return **bool** True if successful, False otherwise
        """
        return self._sensor.set_led_off()
    
    def set_led_drive(self, drive):
        """!
        Set the LED drive.
        
        @param int drive: The drive to set
        
        @return **bool** True if successful, False otherwise
        """
        return self._sensor.set_led_drive(drive)
    