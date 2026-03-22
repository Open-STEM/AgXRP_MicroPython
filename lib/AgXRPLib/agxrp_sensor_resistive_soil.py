#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_resistive_soil.py
#
# Wrapper class for the SparkFun Qwiic resistive soil moisture sensor.
# Provides a unified interface for the AgXRPSensorKit.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

from lib.AgXRPLib.qwiic_soil_moisture_sensor import QwiicSoilMoistureSensor
from lib.AgXRPLib.agxrp_sensor import AgXRPSensor


# Raw ADC range from Qwiic soil moisture sensor (10-bit)
_RAW_MAX = 1023


class AgXRPResistiveSoilSensor(AgXRPSensor):
    """!
    Wrapper class for the SparkFun Qwiic resistive soil moisture sensor.

    This class wraps the QwiicSoilMoistureSensor and provides a common interface
    for reading soil moisture as a percentage 0-100 (0 = dry, 100 = wet).
    """

    def __init__(self, i2c_driver=None, address=None):
        """!
        Constructor

        @param i2c_driver: I2C driver instance
        @param address: I2C address (default: 0x28, the Qwiic default)
        """
        super().__init__(i2c_driver)
        self._address = address
        self._moisture_raw = 0  # Raw level 0-1023 from sensor

    def begin(self):
        """!
        Initialize the resistive soil sensor.

        @return **bool** True if initialization was successful, False otherwise
        """
        try:
            self._sensor = QwiicSoilMoistureSensor(
                address=self._address,
                i2c_driver=self._i2c_driver
            )

            if not self._sensor.begin():
                print(f"ERROR: Qwiic resistive soil sensor not found at address 0x{self._sensor.address:02X}")
                self._connected = False
                return False

            self._connected = True
            return True
        except Exception as e:
            print(f"Error initializing resistive soil sensor: {e}")
            self._connected = False
            return False

    def update(self):
        """!
        Read the latest sensor data.

        Reads the raw moisture level from the sensor (0-1023) and stores it.

        @return **bool** True if data was read successfully, False otherwise
        """
        if not self._connected or self._sensor is None:
            return False

        try:
            self._sensor.read_moisture_level()
            self._moisture_raw = self._sensor.level
            return True
        except Exception as e:
            print(f"Error reading resistive soil sensor: {e}")
            return False

    def _moisture_percent(self):
        """Convert raw 0-1023 to percentage 0-100 (0=dry, 100=wet)."""
        p = round((self._moisture_raw / _RAW_MAX) * 100)
        return max(0, min(100, p))

    def get_display_lines(self):
        """!
        Get formatted strings for OLED display.

        @return **list** List of strings for display
        """
        return [f"Resistive Soil: {self._moisture_percent()}%"]

    def get_csv_data(self):
        """!
        Get sensor data as a dictionary for CSV logging.

        @return **dict** Dictionary with sensor values (soil_moisture 0-100)
        """
        return {
            "soil_moisture": self._moisture_percent()
        }

    def get_sensor_name(self):
        """!
        Get the sensor identifier name.

        @return **str** Sensor name
        """
        return "ResistiveSoil"

    def get_moisture(self):
        """!
        Get the current soil moisture as a percentage (0-100).
        0 = dry, 100 = wet. Use this value for controller threshold (e.g. water when below 30%).

        @return **int** Moisture percentage 0-100
        """
        return self._moisture_percent()

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
                self._sensor.led_on()
            else:
                self._sensor.led_off()
            return True
        except Exception as e:
            print(f"Error setting LED: {e}")
            return False
