"""
ROCKET SENSOR SANITY CHECK
Description: Displays live Thrust (N) and Pressure (PSI) to verify calibration.
"""
import sys
import time
from labjack import ljm

# ==========================================
#    PASTE YOUR FINAL CONFIGURATION HERE
# ==========================================

# --- THRUST (AIN0) ---
THRUST_ZERO_VOLTS = 1.2648    # From your video observation
THRUST_SLOPE = 9659.0769         # <--- REPLACE with your calculated slope!

# --- PRESSURE (AIN2) ---
PRESSURE_OFFSET_VOLTS = 0.0243 # From your video observation
PRESSURE_SLOPE = 625.0         # 2500PSI range / 4V span approx.

# --- TEMPERATURE (AIN4) ---
TEMP_SLOPE = 100.0             # 100 C per Volt

# ==========================================

def sanity_monitor():
    handle = None
    try:
        # Open LabJack
        handle = ljm.openS("T7", "USB", "ANY")
        
        # Set ranges to +/- 10V to be safe
        ljm.eWriteNames(handle, 3, 
                        ["AIN0_RANGE", "AIN2_RANGE", "AIN4_RANGE"], 
                        [10.0, 10.0, 10.0])

        print("\n--- LIVE SENSOR MONITOR ---")
        print("Verify that readings make sense before firing.")
        print("Press CTRL+C to quit.\n")
        
        print(f"{'THRUST (N)':<15} | {'PRESSURE (PSI)':<15} | {'TEMP (C)':<15}")
        print("-" * 50)

        while True:
            # Read all 3 channels
            volts = ljm.eReadNames(handle, 3, ["AIN0", "AIN2", "AIN4"])
            
            # --- MATH (Identical to Main Logger) ---
            
            # 1. Thrust
            # Force = (Voltage - Zero) * Slope
            raw_thrust = (volts[0] - THRUST_ZERO_VOLTS) * THRUST_SLOPE
            
            # 2. Pressure
            # Pressure = (Voltage - Zero) * Slope
            raw_pressure = (volts[1] - PRESSURE_OFFSET_VOLTS) * PRESSURE_SLOPE

            # 3. Temp
            raw_temp = volts[2] * TEMP_SLOPE

            # --- DISPLAY ---
            # We do NOT clamp to zero here (e.g. no "if < 0: 0")
            # We want to see if the value is drifting negative!
            
            print(f"{raw_thrust:<15.2f} | {raw_pressure:<15.2f} | {raw_temp:<15.1f}", end="\r")
            
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\nCheck complete.")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if handle:
            ljm.close(handle)

if __name__ == "__main__":
    sanity_monitor()