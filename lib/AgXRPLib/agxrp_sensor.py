#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor.py
#
# Base interface class for AgXRP sensor wrappers.
# All sensor wrappers inherit from this class to provide a common interface.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

class AgXRPSensor:
    """!
    Base class for all AgXRP sensor wrappers.
    
    This class defines the common interface that all sensor wrappers should implement.
    It provides a consistent API for the AgXRPSensorKit to interact with different sensors.
    """
    
    def __init__(self, i2c_driver=None):
        """!
        Constructor
        
        @param i2c_driver: Optional I2C driver instance to use
        """
        self._i2c_driver = i2c_driver
        self._sensor = None
        self._connected = False
    
    def update(self):
        """!
        Read the latest sensor data and store it internally.
        
        This method should be called periodically to refresh sensor readings.
        It should handle errors gracefully and return True on success, False on failure.
        
        Subclasses must override this method.
        
        @return **bool** True if update was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement update()")
    
    def get_display_lines(self):
        """!
        Get formatted strings for OLED display.
        
        Returns a list of strings, each representing one line to display on the OLED.
        The strings should be formatted appropriately for the display size.
        
        Subclasses must override this method.
        
        @return **list** List of strings, one per display line
        """
        raise NotImplementedError("Subclasses must implement get_display_lines()")
    
    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.
        
        Returns a dictionary where keys are column names and values are the sensor readings.
        The dictionary will be merged with other sensors' data for CSV output.
        
        Subclasses must override this method.
        
        @return **dict** Dictionary of sensor values with descriptive keys
        """
        raise NotImplementedError("Subclasses must implement get_csv_data()")
    
    def get_sensor_name(self):
        """!
        Get the sensor identifier name.
        
        Returns a string identifier for this sensor type (e.g., "SCD4x", "AS7343", "VEML").
        
        Subclasses must override this method.
        
        @return **str** Sensor name identifier
        """
        raise NotImplementedError("Subclasses must implement get_sensor_name()")
    
    def is_connected(self):
        """!
        Check if the sensor is connected and initialized.
        
        @return **bool** True if sensor is connected, False otherwise
        """
        return self._connected
    
    def begin(self):
        """!
        Initialize the sensor.
        
        This method should initialize the underlying sensor hardware and configure it
        for normal operation. It should set self._connected appropriately.
        
        Subclasses must override this method.
        
        @return **bool** True if initialization was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement begin()")

