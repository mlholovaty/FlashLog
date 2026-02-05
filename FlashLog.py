"""
ROCKET STATIC FIRE LOGGER
Hardware: LabJack T7
 - Thrust: Load Cell + Amp (Gain 201) -> AIN0
 - Pressure: Transducer + Amp (Gain 11) -> AIN2
 - Temperature: Future Probe -> AIN4
"""

import sys
import time
import csv
import datetime
import numpy as np
import matplotlib.pyplot as plt
from labjack import ljm

# ==========================================
#        USER CONFIGURATION SECTION
# ==========================================

# --- CALIBRATION (YOU MUST UPDATE THESE!) ---

# THRUST (AIN0)
# Formula: Slope = (Known_Weight_Newtons) / (Voltage_Loaded - Voltage_Empty)
THRUST_ZERO_VOLTS = 1.2648     # Voltage when motor is empty
THRUST_SLOPE = 9659.0769          # Newtons per Volt (Example value, please calculate!)

# PRESSURE (AIN2)
# Formula: Slope = Max_PSI / (Max_Voltage - Zero_Voltage)
# If your sensor is 2500 PSI, and reads 0.5V at 0PSI and 4.5V at max:
PRESSURE_OFFSET_VOLTS = 0.0243 # Voltage at 0 PSI
PRESSURE_SLOPE = 625.0         # PSI per Volt (Example value)

# TEMPERATURE (AIN4)
# Placeholder for now. 10mV/C is standard for LM35 sensors.
TEMP_SLOPE = 100.0            # Degrees C per Volt

# --- TEST SETTINGS ---
IGNITION_TRIGGER = 20.0       # Newtons (Start recording when thrust > this)
BURNOUT_TRIGGER = 10.0        # Newtons (Stop counting burn time when < this)
SAMPLE_RATE_HZ = 200          # Hz (Samples per second)

# ==========================================

class RocketLogger:
    def __init__(self):
        self.handle = None
        self.data = [] # Stores [time, thrust, pressure, temperature]
        self.start_timestamp = 0
        self.test_date = ""

    def connect(self):
        print("Connecting to LabJack T7...")
        try:
            self.handle = ljm.openS("T7", "USB", "ANY")
            
            # Configure Ranges to +/- 10V to handle amplified signals safely
            names = ["AIN0_RANGE", "AIN2_RANGE", "AIN4_RANGE"]
            values = [10.0, 10.0, 10.0]
            ljm.eWriteNames(self.handle, 3, names, values)
            
            print("Success! Sensors Connected.")
            print(f"  - Thrust:   AIN0")
            print(f"  - Pressure: AIN2")
            print(f"  - Temp:     AIN4")
            
        except ljm.LJMError as e:
            print(f"Connection Failed: {e}")
            sys.exit()

    def get_readings(self):
        """Reads AIN0, AIN2, AIN4 and converts to units."""
        # Read 3 channels: AIN0 (Thrust), AIN2 (Pressure), AIN4 (Temp)
        # Note: We skip AIN1 and AIN3 because the amps output to the Even channels.
        volts = ljm.eReadNames(self.handle, 3, ["AIN0", "AIN2", "AIN4"])
        
        # 1. Thrust Calculation
        thrust_N = (volts[0] - THRUST_ZERO_VOLTS) * THRUST_SLOPE
        
        # 2. Pressure Calculation
        pressure_PSI = (volts[1] - PRESSURE_OFFSET_VOLTS) * PRESSURE_SLOPE

        # 3. Temperature Calculation
        temp_C = volts[2] * TEMP_SLOPE

        # Zero Clamping (Hide negative noise)
        if thrust_N < 0: thrust_N = 0.0
        if pressure_PSI < 0: pressure_PSI = 0.0

        return thrust_N, pressure_PSI, temp_C

    def classify_motor(self, impulse_ns):
        """Returns motor class (e.g. K50%) based on Ns."""
        ranges = [
            (160, 320, 'H'), (320, 640, 'I'), (640, 1280, 'J'),
            (1280, 2560, 'K'), (2560, 5120, 'L'), (5120, 10240, 'M'),
            (10240, 20480, 'N'), (20480, 40960, 'O'), (40960, 81920, 'P')
        ]
        for low, high, char in ranges:
            if low <= impulse_ns < high:
                pct = int(((impulse_ns - low) / (high - low)) * 100)
                return f"{char} {pct}%"
        return "Unknown"
    def run(self):
        print("\n--- READY FOR FIRE ---")
        print(f"Waiting for Thrust > {IGNITION_TRIGGER} N...")
        print("(Press Ctrl+C to Stop Test Manually)")

        burning = False
        finished = False
        low_thrust_count = 0  # To ensure it's actually finished and not just noise
        
        try:
            while not finished:
                thrust, pressure, temp = self.get_readings()

                if not burning:
                    # Waiting for ignition
                    sys.stdout.write(f"\rWAIT | Thrust: {thrust:6.1f} N | Press: {pressure:6.1f} PSI")
                    sys.stdout.flush()
                    
                    if thrust > IGNITION_TRIGGER:
                        print("\n\n*** IGNITION DETECTED! LOGGING STARTED ***")
                        burning = True
                        self.start_timestamp = time.time()
                        self.test_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                else:
                    # Recording data
                    t_elapsed = time.time() - self.start_timestamp
                    self.data.append([t_elapsed, thrust, pressure, temp])
                    
                    # Update screen
                    if len(self.data) % 20 == 0:
                        sys.stdout.write(f"\rREC  | T+{t_elapsed:5.2f}s | Thrust: {thrust:6.1f} N | Press: {pressure:6.1f} PSI")
                        sys.stdout.flush()

                    # --- AUTO-STOP LOGIC ---
                    if thrust < BURNOUT_TRIGGER:
                        low_thrust_count += 1
                    else:
                        low_thrust_count = 0 # Reset if thrust kicks back up

                    # Stop if thrust is low for 0.5 seconds (adjust as needed)
                    # ... inside the 'if burning:' block ...
                    if low_thrust_count > (SAMPLE_RATE_HZ * 0.5):
                        print("\n\n*** BURNOUT DETECTED! STOPPING... ***")

                        # --- THE FIX: TRIM THE TRAILING NOISE ---
                        # Remove the last 'low_thrust_count' samples from the data
                        if len(self.data) > low_thrust_count:
                            self.data = self.data[:-low_thrust_count]

                        finished = True
                        
                    #if low_thrust_count > (SAMPLE_RATE_HZ * 0.5):
                    #    print("\n\n*** BURNOUT DETECTED! STOPPING... ***")
                    #    finished = True

                time.sleep(1.0 / SAMPLE_RATE_HZ)

            # Proceed to analysis after loop finishes naturally
            self.shutdown()
            self.analyze()

        except KeyboardInterrupt:
            print("\n\nTest Aborted Manually. analyzing collected data...")
            self.shutdown()
            self.analyze()

#    def run(self):
#        print("\n--- READY FOR FIRE ---")
#        print(f"Waiting for Thrust > {IGNITION_TRIGGER} N...")
#        print("(Press Ctrl+C to Stop Test Manually)")
#
#        burning = False
#        
#        try:
#            while True:
#                thrust, pressure, temp = self.get_readings()
#
#                if not burning:
#                    # Waiting for ignition
#                    sys.stdout.write(f"\rWAIT | Thrust: {thrust:6.1f} N | Press: {pressure:6.1f} PSI")
#                    sys.stdout.flush()
#                    
#                    if thrust > IGNITION_TRIGGER:
#                        print("\n\n*** IGNITION DETECTED! LOGGING STARTED ***")
#                        burning = True
#                        self.start_timestamp = time.time()
#                        self.test_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#
#                if burning:
#                    # Recording data
#                    t_elapsed = time.time() - self.start_timestamp
#                    self.data.append([t_elapsed, thrust, pressure, temp])
#                    
#                    # Update screen every 20 samples (approx 10 times/sec)
#                    if len(self.data) % 20 == 0:
#                        sys.stdout.write(f"\rREC  | T+{t_elapsed:5.2f}s | Thrust: {thrust:6.1f} N | Press: {pressure:6.1f} PSI")
#                        sys.stdout.flush()
#
#                # Control loop speed
#                time.sleep(1.0 / SAMPLE_RATE_HZ)
#
#        except KeyboardInterrupt:
#            print("\n\nTest Finished. analyzing data...")
#            self.shutdown()
#            self.analyze()

    def analyze(self):
        if not self.data:
            print("No data collected.")
            return

        # Convert to numpy array
        arr = np.array(self.data)
        t = arr[:, 0]  # Time
        f = arr[:, 1]  # Force
        p = arr[:, 2]  # Pressure
        tmp = arr[:, 3] # Temperature

        # --- CALCULATIONS ---
        total_impulse = np.trapz(f, t) # Integral
        
        # Burn Time Calculation
        active_indices = np.where(f > BURNOUT_TRIGGER)[0]
        if len(active_indices) > 2:
            burn_time = t[active_indices[-1]] - t[active_indices[0]]
            avg_thrust = total_impulse / burn_time
        else:
            burn_time = 0
            avg_thrust = 0

        motor_class = self.classify_motor(total_impulse)
        max_thrust = np.max(f)
        max_pressure = np.max(p)
        max_temp = np.max(tmp)

        # --- REPORT ---
        print("\n" + "="*40)
        print(f"  STATIC FIRE REPORT")
        print("="*40)
        print(f"Total Impulse  : {total_impulse:.2f} Ns")
        print(f"Motor Class    : {motor_class}")
        print(f"Burn Time      : {burn_time:.3f} s")
        print(f"Avg Thrust     : {avg_thrust:.2f} N")
        print(f"Max Thrust     : {max_thrust:.2f} N")
        print(f"Max Pressure   : {max_pressure:.2f} PSI")
        print(f"Max Temp       : {max_temp:.2f} C")
        print("="*40)

        self.save_csv()
        self.plot(t, f, p, total_impulse, motor_class)

    def save_csv(self):
        fname = f"Motor_Data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Time(s)", "Thrust(N)", "Pressure(PSI)", "Temp(C)"])
            writer.writerows(self.data)
        print(f"Data saved to: {fname}")

    def plot(self, t, f, p, impulse, m_class):
        fig, ax1 = plt.subplots(figsize=(12, 7))

        # Thrust (Red)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Thrust (N)', color='tab:red', fontweight='bold')
        ax1.plot(t, f, color='tab:red', linewidth=2, label="Thrust")
        ax1.tick_params(axis='y', labelcolor='tab:red')
        ax1.grid(True, which='both', linestyle='--', alpha=0.5)

        # Pressure (Blue)
        ax2 = ax1.twinx()
        ax2.set_ylabel('Pressure (PSI)', color='tab:blue', fontweight='bold')
        ax2.plot(t, p, color='tab:blue', linewidth=1.5, linestyle=':', label="Pressure")
        ax2.tick_params(axis='y', labelcolor='tab:blue')

        # Title and Info
        plt.title(f"Static Fire: Class {m_class} ({impulse:.0f} Ns)", fontsize=14)
        
        # Add text box with stats
        stats = (f"Burn Time: {t[-1]:.2f}s\n"
                 f"Max Force: {np.max(f):.0f} N\n"
                 f"Max Press: {np.max(p):.0f} PSI")
        plt.figtext(0.15, 0.8, stats, bbox=dict(facecolor='white', alpha=0.9))

        plt.tight_layout()
        plt.show()

    def shutdown(self):
        if self.handle:
            ljm.close(self.handle)

if __name__ == "__main__":
    app = RocketLogger()
    app.connect()
    app.run()