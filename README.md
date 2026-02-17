# FlashLog
FlashLog is a system created by Kent State University High-Powered Rocket Team, Golden Flashes, for logging data from statict test burn of solid rocket motors. FlashLog uses a Data Aquisition (DAQ) system T7 from LabJack with a CB37 Terminal Board from the same company. All codes were made using python 3 programing language.

# Requirements
In order to properly work, the following libraries are required to be installed: numpy 2.4.1, labjack-ljm compatible with T7 DAQ system and matplotlib 3.10.8. A compatible check is needed for newer versions of the libraries to ensure the codes run properly.
In addition to the libraries, the LabJack drivers are needed in order to the DAQ system to be recognized by the code. The link for the softwares is the following: https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit

# FlashLog Code
This is the main code for FlashLog. It reads the inputs from the sensors through LabJack units and amplifiers. It calculates the Thrust and Pressure and it will in the furture provides Temperature. In the code there is a Configuration part that requires the user to imput the zero values for the sensors and the slope, both can be found using the CalibrationTool code. 

# Calibration Tool
The repository includes a calibartion tool in which will display live data of the value outputing from the sensors connected to the system. It display a value in Volts, when no force is being applied to the system, it will show the zero value. When a force is applied, a load or pressure, it will show the voltage reading. The equation for founding the slope is commented in the FlashLog code.

# Live Monitors
This code shows a live monitor for sanity check of the sensors and system. It displays live data from the sensors in the same configuration as the main code should be. It also requires user imput for the same values. This tool can help to check the system without logging a burn.
