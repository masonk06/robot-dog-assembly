# Pi shared-battery assembly change

The user has confirmed that the Pi and camera will share the robot's 3S battery.
The Pi has its own external buck converter. AUX retains its separate converter
for the ESP32 and MPU6050. This supersedes the separate-Pi-battery operating plan.

## Retained connections

Battery positive passes through F1, then F7 to J10 pin 1. J10 pin 2 is ground.
The Pi branch is upstream of J3, so opening the servo switch loop leaves the Pi
powered. Disconnect battery power after an orderly Pi shutdown.

J10 pin 3 accepts the external Pi converter's regulated output; pin 4 is ground.
J11 pin 1 carries that output and pin 2 is ground. The USB-C supply interface
must be selected and verified before connecting these terminals to a Pi.

## Assembly status and required work

The existing manufacturing package marks F7, J10 and J11 DNP. Re-enabling them
requires an assembly revision or hand installation. F7's current footprint is
Luca_Review:Bel_0680H_2410_DNP_NoPaste. For reflow assembly, restore the verified
fuse footprint's paste apertures and regenerate the manufacturing package.

J10 uses the same four-position Phoenix footprint as J7; J11 uses the same
two-position family as J5. Check the actual sourced parts against these
footprints before changing the assembly BOM.

The candidate Pololu D42V55F5 (#5571) has a nominal 5 V, 6 A output. Selection
remains provisional pending thermal performance and voltage-drop checks.
The Pi 5 target is 5 V at 5 A at its input. Its USB-C interface requires a
compatible source and cable, including USB Power Delivery for automatic 5 A
recognition. A bare buck converter does not provide that interface.

Select F7 against converter input current, startup/inrush, wiring and its
time-current and DC interruption ratings. Audit the retained Pi copper at the
required input and output currents; the existing DNP release did not establish
this branch's loaded performance. Recheck the total battery/main-fuse load with
the Pi and camera included. Verify Pi voltage during servo startup and walking.

Manufacturer references

- https://www.pololu.com/product/5571
- https://www.raspberrypi.com/documentation/computers/getting-started.html
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
