#!/usr/bin/env python
#-------------------------------------------------------------------------------
# agxrp_controller.py
#
# AgXRPController class that manages automatic watering control for plant systems.
# Each plant system consists of a soil moisture sensor and water pump pair.
#-------------------------------------------------------------------------------
# Written for AgXRPSensorKit, 2024
#===============================================================================

import time
import uasyncio
from lib.AgXRPLib.agxrp_water_pump import AgXRPWaterPump

class AgXRPController:
    """!
    Controller class that manages automatic watering control for plant systems.
    
    This class coordinates soil moisture sensors and water pumps to automatically
    water plants when soil moisture falls below a threshold. Each plant system
    consists of a soil sensor and pump pair with independent control parameters.
    """
    
    def __init__(self, sensor_kit):
        """!
        Constructor
        
        @param sensor_kit: AgXRPSensorKit instance
        """
        self._sensor_kit = sensor_kit
        self._water_pumps = {}  # Dictionary mapping pump_index to AgXRPWaterPump
        self._plant_systems = {}  # Dictionary mapping (sensor_index, pump_index) tuple to plant system data
        self._control_loop_task = None
        self._control_loop_running = False
    
    def get_sensor_kit(self):
        """!
        Get the sensor kit instance.
        
        @return **AgXRPSensorKit** The sensor kit instance
        """
        return self._sensor_kit
    
    def register_water_pump(self, pump_index: int, csv_filename: str = None):
        """!
        Register a water pump for control.
        
        @param pump_index: The motor index for the pump (1, 2, 3, or 4)
        @type pump_index: int
        @param csv_filename: Optional CSV filename for logging (default: "water_pump_log_{index}.csv")
        @type csv_filename: str
        @return **bool** True if registration was successful, False otherwise
        """
        if pump_index in self._water_pumps:
            print(f"WARNING: Pump {pump_index} is already registered. Overwriting...")
        
        try:
            if csv_filename is None:
                csv_filename = f"water_pump_log_{pump_index}.csv"
            
            pump = AgXRPWaterPump(index=pump_index, csv_filename=csv_filename)
            self._water_pumps[pump_index] = pump
            print(f"Water pump {pump_index} registered successfully")
            return True
        except Exception as e:
            print(f"ERROR: Failed to register water pump {pump_index}: {e}")
            return False
    
    def get_pump(self, pump_index: int):
        """!
        Get a water pump instance by index.
        
        @param pump_index: The pump index
        @type pump_index: int
        @return **AgXRPWaterPump** The pump instance, or None if not registered
        """
        return self._water_pumps.get(pump_index)
    
    def register_plant_system(self, sensor_index: int, pump_index: int, 
                             interval_hours: float, threshold: float, 
                             duration_seconds: float, enabled: bool = True):
        """!
        Register a plant system (sensor + pump pair) for automatic control.
        
        @param sensor_index: Soil sensor index (1-4)
        @type sensor_index: int
        @param pump_index: Pump index (must be registered first)
        @type pump_index: int
        @param interval_hours: Frequency to check soil moisture in minutes (can be fractional)
        @type interval_hours: float
        @param threshold: Soil moisture threshold below which to water (pF for capacitive sensors, 0-100% for resistive)
        @type threshold: float
        @param duration_seconds: How long to run the pump when watering (seconds)
        @type duration_seconds: float
        @param enabled: Whether the control loop is active for this system (default: True)
        @type enabled: bool
        @return **bool** True if registration was successful, False otherwise
        """
        if sensor_index not in [1, 2, 3, 4]:
            print(f"ERROR: Invalid sensor index {sensor_index}. Must be 1-4.")
            return False
        
        if pump_index not in self._water_pumps:
            print(f"ERROR: Pump {pump_index} not registered. Register pump first.")
            return False
        
        # Verify sensor exists
        sensor = self._sensor_kit.soil_sensors.get(sensor_index)
        if sensor is None or not sensor.is_connected():
            print(f"ERROR: Soil sensor {sensor_index} not registered or not connected.")
            return False
        
        system_key = (sensor_index, pump_index)
        
        # Create or update plant system
        self._plant_systems[system_key] = {
            "sensor_index": sensor_index,
            "pump_index": pump_index,
            "interval_hours": interval_hours,
            "threshold": threshold,
            "duration_seconds": duration_seconds,
            "enabled": enabled,
            "last_check_time": time.time()
        }
        
        print(f"Plant system registered: Sensor {sensor_index} -> Pump {pump_index} "
              f"(Interval: {interval_hours} hrs, Threshold: {threshold}%, "
              f"Duration: {duration_seconds}s, Enabled: {enabled})")
        return True
    
    def update_plant_system(self, sensor_index: int, pump_index: int, **kwargs):
        """!
        Update plant system parameters.
        
        @param sensor_index: Soil sensor index (1-4)
        @type sensor_index: int
        @param pump_index: Pump index
        @type pump_index: int
        @param kwargs: Parameters to update (interval_hours, threshold, duration_seconds, enabled)
        @return **bool** True if update was successful, False otherwise
        """
        system_key = (sensor_index, pump_index)
        
        if system_key not in self._plant_systems:
            print(f"ERROR: Plant system (Sensor {sensor_index}, Pump {pump_index}) not registered.")
            return False
        
        system = self._plant_systems[system_key]
        
        # Update allowed parameters
        if "interval_hours" in kwargs:
            system["interval_hours"] = float(kwargs["interval_hours"])
        if "threshold" in kwargs:
            system["threshold"] = float(kwargs["threshold"])
        if "duration_seconds" in kwargs:
            system["duration_seconds"] = float(kwargs["duration_seconds"])
        if "enabled" in kwargs:
            system["enabled"] = bool(kwargs["enabled"])
        
        print(f"Plant system updated: Sensor {sensor_index} -> Pump {pump_index}")
        return True
    
    def get_plant_systems(self):
        """!
        Get all registered plant systems.
        
        @return **dict** Dictionary of plant systems, keyed by (sensor_index, pump_index) tuple
        """
        return self._plant_systems.copy()
    
    def get_plant_system(self, sensor_index: int, pump_index: int):
        """!
        Get a specific plant system.
        
        @param sensor_index: Soil sensor index (1-4)
        @type sensor_index: int
        @param pump_index: Pump index
        @type pump_index: int
        @return **dict** Plant system data, or None if not found
        """
        system_key = (sensor_index, pump_index)
        return self._plant_systems.get(system_key)
    
    async def _control_loop(self):
        """!
        Internal async control loop that checks plant systems and activates pumps.
        
        This method runs continuously, checking each enabled plant system at its
        specified interval and activating pumps when soil moisture is below threshold.
        """
        while self._control_loop_running:
            current_time = time.time()
            
            # Check each plant system
            for system_key, system in self._plant_systems.items():
                if not system["enabled"]:
                    continue
                
                sensor_index = system["sensor_index"]
                pump_index = system["pump_index"]
                interval_seconds = system["interval_hours"] * 3600.0
                
                # Check if enough time has passed since last check
                time_since_last_check = current_time - system["last_check_time"]
                
                if time_since_last_check >= interval_seconds:
                    # Time to check this system
                    try:
                        # Get soil moisture reading
                        sensor = self._sensor_kit.soil_sensors.get(sensor_index)
                        
                        if sensor and sensor.is_connected():
                            # Update sensor to get latest reading
                            sensor.update()
                            moisture = sensor.get_moisture()
                            unit = "%" if sensor.get_sensor_name() == "ResistiveSoil" else "pF"
                            print(f"Control check: Sensor {sensor_index} -> Pump {pump_index}: "
                                  f"Moisture = {moisture:.1f} {unit}, Threshold = {system['threshold']:.1f} {unit}")
                            
                            # Check if watering is needed
                            if moisture < system["threshold"]:
                                print(f"Watering needed! Activating Pump {pump_index} for {system['duration_seconds']}s")
                                
                                # Get pump and activate it
                                pump = self._water_pumps[pump_index]
                                if pump:
                                    # Activate pump with logging
                                    pump.set_pump_effort(
                                        effort=1,
                                        time_ms=int(system["duration_seconds"] * 1000),
                                        log=True,
                                        soil_moisture=moisture
                                    )
                            
                            # Update last check time
                            system["last_check_time"] = current_time
                        else:
                            print(f"WARNING: Sensor {sensor_index} not connected. Skipping check.")
                    except Exception as e:
                        print(f"ERROR in control loop for system {system_key}: {e}")
            
            # Sleep for a short interval before next check (1 second)
            await uasyncio.sleep(1.0)
    
    def start_control_loop(self):
        """!
        Start the async control loop.
        
        This creates a background task that continuously monitors and controls
        all enabled plant systems.
        """
        if self._control_loop_running:
            print("WARNING: Control loop is already running.")
            return
        
        if len(self._plant_systems) == 0:
            print("WARNING: No plant systems registered. Control loop will do nothing.")
            return
        
        self._control_loop_running = True
        
        try:
            loop = uasyncio.get_event_loop()
            self._control_loop_task = loop.create_task(self._control_loop())
            print("Control loop started")
        except Exception as e:
            print(f"ERROR: Failed to start control loop: {e}")
            self._control_loop_running = False
    
    def stop_control_loop(self):
        """!
        Stop the async control loop.
        """
        if not self._control_loop_running:
            print("WARNING: Control loop is not running.")
            return
        
        self._control_loop_running = False
        
        if self._control_loop_task:
            try:
                self._control_loop_task.cancel()
            except:
                pass
            self._control_loop_task = None
        
        print("Control loop stopped")

