# MPU6050/MPU6500 readout on NodeMCU-32S

On 2026-10-27 the user clarified that the IMU controller is a NodeMCU ESP32S
(classic ESP32), not the ESP32-S3 discussed earlier. The previously reported
SDA GPIO 8 / SCL GPIO 9 wiring must be moved with power disconnected: those
GPIOs are normally connected to flash on this module. The updated sketch uses
SDA GPIO 21 and SCL GPIO 22. Live diagnostics on these GPIOs now confirm an
I2C response. The agent uploaded sensor-only diagnostic firmware to COM7.
Other robot-controller files are not changed by this IMU board correction.

Live diagnostics subsequently confirmed COM7 as an ESP32-D0WD-V3 and verified
working I2C at address 0x68. WHO_AM_I returned 0x70, the MPU6500 ID, rather than
the expected MPU6050 ID 0x68. Power LED is lit and headers are soldered according
to the user. Version 3 selects the MPU6500-compatible register profile for
0x70 and MPU6050-compatible profile for 0x68; unsupported IDs remain rejected.
The profile also changes accelerometer filtering and temperature conversion,
rather than simply bypassing the identity check. The sketch filename is kept
for Arduino IDE continuity. Original diagnostic capture is retained under runs/.

Version 3 was compiled and uploaded successfully, with flash verification.
Direct COM7 capture received 622 finite samples at about 100 Hz and no ERR lines.
Observed acceleration magnitude averaged 9.37 m/s^2; gyro means were nonzero.
These are uncalibrated observations, not accepted bias/scale calibration.
Stationary conditions and mounting orientation were not verified. Bringup
summary: reports/imu/bringup-20261027.json. No motor commands were sent.

## Saved current-pose zero

At the user's request, 601 fresh samples were captured while holding the IMU
still. Acceleration/gyro variation passed the stationary-capture gates. The
captured gravity direction defines roll/pitch zero, and mean gyro rates are
saved as a stationary bias estimate in calibrations/current-zero.json, with
a timestamped copy preserved alongside it. This is not a full accelerometer
scale/bias calibration, robot mounting-axis mapping, or XYZ position estimate.
Gravity is retained, not zeroed out. No servo calibration was changed.

The read-only viewer applies the saved reference to incoming data:

```powershell
.venv\Scripts\python.exe hardware/imu/zero_view.py --port COM7
```

Close Serial Monitor first so COM7 is available. Roll/pitch are based on the
gravity direction and displayed with a 0.15-second low-pass filter; movement
acceleration can disturb them. The display is not a fused attitude estimator
or a policy-observation provider. It marks data stale after 0.5 seconds and
does not display heading or XYZ location. Full robot-axis alignment and
state-estimator work remain separate. The raw firmware CSV format is unchanged.

The sensor-only sketch uses built-in Wire, without external libraries or servo
commands. It configures the MPU6050 and publishes CSV accelerometer/gyro data
near 100 Hz at serial baud 115200. It is not automatically uploaded. Uploading
it replaces the ESP32's current sketch; preserve any firmware still needed.

After wiring and pin assignments are confirmed:

1. Open mpu6050_readout/mpu6050_readout.ino in Arduino IDE.
2. Select Tools > Board > esp32 > NodeMCU-32S and its USB-to-UART port
   (COM7 was the most recently enumerated CP210x port). This classic ESP32
   board uses Serial/UART0 through its USB bridge, rather than native USB CDC.
3. Upload, open Serial Monitor at 115200, and press Reset if needed.
4. Share the startup lines and a few imu rows while the sensor is stationary.

Accelerometer units are m/s^2 and include gravity: the stationary magnitude
should be roughly 9.81 m/s^2. Gyro units are rad/s and have not had stationary
bias removed. Axes are the sensor's axes, not yet mapped to the robot. The
timestamp is the ESP32 read-start micros() counter, not an exact sensor sample
timestamp. Later steps are bias estimation, mounting-axis mapping, filtering,
rate/latency checks and matching the policy observations. This readout is not
an orientation/velocity estimator or a motor-control/deployment program.

Register choices, data scaling, identity and sample-rate setup follow TDK's
[MPU-6000/MPU-6050 register map](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf).
The 0x70 profile follows the manufacturer's MPU6500 register map and
[MPU6500 specification](https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/mpu-6500-datasheet2.pdf).
Power wiring depends on the actual breakout board; confirm its VCC labeling
and supply requirements before supplying power.

Espressif documents [default I2C pins 21/22](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/i2c.html)
and [GPIO 6-11 being reserved for flash](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/gpio.html).
