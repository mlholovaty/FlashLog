"""
ROCKET CALIBRATION TOOL
Reads AIN0 (Thrust) and AIN2 (Pressure)
"""
import time
import sys
from labjack import ljm

def calibration_wizard():
    try:
        # Connect to LabJack
        handle = ljm.openS("T7", "USB", "ANY")
        info = ljm.getHandleInfo(handle)
        print(f"Connected to LabJack T7 (Serial: {info[2]})")
        
        # Configure Ranges (0-10V is safest for amplified signals)
        ljm.eWriteName(handle, "AIN0_RANGE", 10.0)
        ljm.eWriteName(handle, "AIN2_RANGE", 10.0)

        print("\nReading Sensors... (Press Ctrl+C to Stop)")
        print(f"{'THRUST (AIN0)':<20} | {'PRESSURE (AIN2)':<20}")
        print("-" * 45)

        while True:
            # Read AIN0 (Thrust) and AIN2 (Pressure)
            v_thrust = ljm.eReadName(handle, "AIN0")
            v_pressure = ljm.eReadName(handle, "AIN2")

            # Print voltage with 4 decimal places
            print(f"{v_thrust:<20.4f} | {v_pressure:<20.4f}", end="\r")
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n\n--- CALIBRATION DONE ---")
        print("Use these voltage numbers to update the 'User Configuration' in the main code.")
        if 'handle' in locals():
            ljm.close(handle)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    calibration_wizard()