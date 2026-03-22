#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_sensor_kit_demo.py
#
# Demo script showing usage of the AgXRPSensorKit.
# Demonstrates full configuration with all sensors, and partial configurations.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import sys
import time
from lib.AgXRPLib.agxrp_sensor_kit import AgXRPSensorKit

def demo_full_configuration():
    """!
    Demo with all sensors, OLED, and CSV logger registered.
    """
    print("\n" + "="*60)
    print("Demo 1: Full Configuration (All Sensors + OLED + CSV Logger)")
    print("="*60)
    
    # Create kit with default I2C pins
    kit = AgXRPSensorKit(sda_pin=4, scl_pin=5, i2c_freq=100000)
    
    # Register all sensors
    kit.register_co2_sensor()
    kit.register_spectral_sensor()
    kit.register_light_sensor()
    kit.register_soil_sensor()
    
    # Register OLED display
    kit.register_screen()
    
    # Register CSV logger (logs every 5 seconds)
    kit.register_csv_logger("sensor_data.csv", 5000)
    
    print("\nAll components registered. Starting main loop...")
    print("Data will be logged to 'sensor_data.csv' every 5 seconds.")
    print("Press Ctrl+C to stop.\n")
    
    # Run the main loop
    kit.run()

def demo_partial_configuration():
    """!
    Demo with only SCD4x and OLED (no CSV logger).
    """
    print("\n" + "="*60)
    print("Demo 2: Partial Configuration (SCD4x + OLED only)")
    print("="*60)
    
    # Create kit
    kit = AgXRPSensorKit(sda_pin=4, scl_pin=5, i2c_freq=100000)
    
    # Register only SCD4x
    kit.register_co2_sensor()
    
    # Register OLED display
    kit.register_screen()
    
    print("\nSCD4x and OLED registered. Starting main loop...")
    print("Press Ctrl+C to stop.\n")
    
    # Run the main loop
    kit.run()

def demo_manual_update_loop():
    """!
    Demo showing manual update() loop instead of run() method.
    """
    print("\n" + "="*60)
    print("Demo 3: Manual Update Loop (AS7343 + VEML)")
    print("="*60)
    
    # Create kit
    kit = AgXRPSensorKit(sda_pin=4, scl_pin=5, i2c_freq=100000)
    
    # Register AS7343 and VEML
    kit.register_spectral_sensor()
    kit.register_light_sensor()
    
    # Register OLED
    kit.register_screen()
    
    print("\nAS7343, VEML, and OLED registered.")
    print("Using manual update() loop instead of run() method.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Manual update loop
        for i in range(20):  # Run for 20 iterations (10 seconds at 0.5s intervals)
            kit.update()
            
            # Print readings
            if kit.spectral_sensor and kit.spectral_sensor.is_connected():
                print(f"AS7343 - B: {int(kit.spectral_sensor.get_blue())}, "
                      f"G: {int(kit.spectral_sensor.get_green())}, "
                      f"R: {int(kit.spectral_sensor.get_red())}, "
                      f"N: {int(kit.spectral_sensor.get_nir())}")
            
            if kit.light_sensor and kit.light_sensor.is_connected():
                print(f"VEML - Light: {kit.light_sensor.get_ambient_light():.1f} lux")
            
            time.sleep(0.5)
        
        print("\nManual update loop completed.")
    
    except (KeyboardInterrupt, SystemExit):
        print("\nManual update loop interrupted.")

def demo_csv_logger_only():
    """!
    Demo with CSV logger but no OLED display.
    """
    print("\n" + "="*60)
    print("Demo 4: CSV Logger Only (All Sensors, No OLED)")
    print("="*60)
    
    # Create kit
    kit = AgXRPSensorKit(sda_pin=4, scl_pin=5, i2c_freq=100000)
    
    # Register all sensors
    kit.register_co2_sensor()
    kit.register_spectral_sensor()
    kit.register_light_sensor()
    
    # Register CSV logger (logs every 2 seconds)
    kit.register_csv_logger("sensor_data_no_oled.csv", 2000)
    
    print("\nAll sensors and CSV logger registered (no OLED).")
    print("Data will be logged to 'sensor_data_no_oled.csv' every 2 seconds.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Run for 30 seconds
        start_time = time.time()
        while time.time() - start_time < 30:
            kit.update()
            time.sleep(0.5)
        
        print("\nCSV logger demo completed.")
    
    except (KeyboardInterrupt, SystemExit):
        print("\nCSV logger demo interrupted.")
    finally:
        if kit._csv_logger:
            kit._csv_logger.stop()

def demo_soil_sensor():
    """!
    Demo with soil sensor, OLED, and CSV logger.
    """
    print("\n" + "="*60)
    print("Demo 5: Soil Sensor (Soil + OLED + CSV Logger)")
    print("="*60)
    
    # Create kit
    kit = AgXRPSensorKit(sda_pin=4, scl_pin=5, i2c_freq=100000)
    
    # Register soil sensor (uses GPIO 44 by default)
    kit.register_soil_sensor()
    
    # Register OLED display
    kit.register_screen()
    
    # Register CSV logger (logs every 2 seconds)
    kit.register_csv_logger("soil_sensor_data.csv", 2000)
    
    print("\nSoil sensor, OLED, and CSV logger registered.")
    print("Soil sensor is reading from GPIO 44 (ADC).")
    print("Data will be logged to 'soil_sensor_data.csv' every 2 seconds.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Run for 60 seconds or until interrupted
        start_time = time.time()
        while time.time() - start_time < 60:
            kit.update()
            
            # Print soil sensor readings
            if kit.soil_sensor and kit.soil_sensor.is_connected():
                print(f"Soil - Moisture: {kit.soil_sensor.get_moisture():.1f}%, "
                      f"Raw ADC: {kit.soil_sensor.get_raw_value()}")
            
            time.sleep(0.5)
        
        print("\nSoil sensor demo completed.")
    
    except (KeyboardInterrupt, SystemExit):
        print("\nSoil sensor demo interrupted.")
    finally:
        if kit._csv_logger:
            kit._csv_logger.stop()

def main():
    """!
    Main function - select which demo to run.
    """
    print("\nAgXRPSensorKit Demo Script")
    print("="*60)
    print("\nAvailable demos:")
    print("1. Full Configuration (All Sensors + OLED + CSV Logger)")
    print("2. Partial Configuration (SCD4x + OLED only)")
    print("3. Manual Update Loop (AS7343 + VEML)")
    print("4. CSV Logger Only (All Sensors, No OLED)")
    print("5. Soil Sensor (Soil + OLED + CSV Logger)")
    print("\nNote: This script assumes sensors are connected.")
    print("If a sensor is not connected, that demo may fail.")
    print("="*60)
    
    # For this demo, we'll run the full configuration by default
    # In a real scenario, you might want to add user input to select which demo
    
    try:
        # Run full configuration demo
        demo_full_configuration()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running demo: {e}")
        print("\nTrying partial configuration demo instead...")
        try:
            demo_partial_configuration()
        except Exception as e2:
            print(f"\nError in partial demo: {e2}")
            sys.exit(1)

if __name__ == '__main__':
    main()

