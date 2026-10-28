# Combined IMU and read-only servo feedback

Open the complete imu_servo_readout.ino sketch in Arduino IDE. This replaces
the IMU-only sketch when you choose to upload it; the agent does not upload
this combined sketch automatically. Select NodeMCU-32S, COM7 (or its current
USB port), and upload speed 115200. No external libraries are needed: Wire and
HardwareSerial are provided by the installed ESP32 core.

Confirmed wiring from the REAL chat:

| NodeMCU ESP-32S | Connection |
| --- | --- |
| GPIO 16 (UART RX) | Waveshare Adapter (A) RX |
| GPIO 17 (UART TX) | Waveshare Adapter (A) TX |
| GND | Waveshare GND |
| GPIO 21 | IMU SDA |
| GPIO 22 | IMU SCL |
| 3V3 / GND | IMU power / ground as used in the working readout |

Waveshare's UART-control jumpers remain at A. Its external supply powers the
servos at their rated voltage. The adapter header uses the host-perspective
RX-RX / TX-TX labeling described in the
[Waveshare wiring guide](https://docs.waveshare.com/Bus_Servo_Adapter_A/Product-Wiring-Example).
The ESP32's pins labeled RX0/TX0 remain its USB serial connection.

## View the readings

Close the separate IMU zero-view window before uploading so it releases COM7.
After upload, open Serial Monitor at 115200 baud with New Line selected.

- SERVOS, then Enter: show servo feedback only.
- IMU, then Enter: show accelerometer/gyro readings only.
- BOTH, then Enter: show both (startup default).
- HELP, then Enter: show the CSV column descriptions.

Commands only change which measurements are printed. They do not change
torque, motor position, IDs, neutral offsets, limits, or saved IMU references.
Raw IMU output is unchanged and supports the prior 0x70 MPU6500-compatible
profile and 0x68 MPU6050-compatible profile.

Servo CSV columns:

```text
servo,id,t_us,ticks,voltage_v,temp_c,torque_enabled,mode,status
servo,1,12345678,2009,12.0,31,0,0,0
```

The second line is an illustration, not a measurement. A failed read prints
servo_error,ID,no_valid_response. Only IDs 1 through 12 are queried. Each ID
is polled roughly once every 1.2 seconds; the IMU is sampled near 100 Hz.
These rates are for manual identification, not closed-loop walking control.
UART response timeouts and USB buffering can affect the actual rates.

Servo register reads cover addresses 33..63 in one transaction, providing mode
(33), torque flag (40), position (56-57), voltage (62) and temperature (63).
The packet parser checks ID, expected length and checksum, skipping noise and
possible transmitted-packet echoes. Missing replies never become zero angles.
The only instruction sent on the servo UART is READ (0x02); host USB input is
not forwarded to the servo bus.

Leg labels are deliberately not assigned: IDs remain with their physical
motors when leg assemblies move. For manual identification, support the robot,
verify the relevant servo reports torque_enabled=0, gently move one joint,
and watch its ID/ticks. This program does not itself release a powered servo.
Do not overwrite the old mapping/neutral limits until locations and directions
have been verified against the new frame.
