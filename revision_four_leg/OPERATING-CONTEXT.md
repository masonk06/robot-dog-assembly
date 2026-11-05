# Operating context supplied 2026-11-04

Confirmed by the user:
- Walking only; running and jumping are outside the intended operating scope.
- Battery purchase link: https://www.amazon.com/dp/B0C2CTZPMZ
  Previously specified as Gens ace 3S 2200 mAh 35C, XT60; actual label and
  mating-connector identity remain the authority over a marketplace listing.
- Servo leads are 150 mm, 22 AWG, three-pin connectors described as JST.
- Three ST3215 servos may be daisy chained within each leg.
- AUX supplies a NodeMCU ESP32S development board and MPU6050 module.
  Exact manufacturer/revision and breakout-board input-power details remain
  to be checked before selecting the regulator connection.
- Pi and camera use a completely separate power source. Preserve the existing
  Pi interface circuit per the earlier scope instruction, but designate it
  unused in the intended assembly: leave F7 and the external Pi buck absent,
  and leave J10/J11 unconnected. Do not combine the two supplies' positive rails.
  If a wired communication link joins Pi and ESP32, review its ground reference
  and USB power/backfeed behavior as part of the harness design.
- User will design the chassis around the PCB; clearance is not a current
  board-layout constraint. Keep documented component envelopes available.

## Supplied gait telemetry

Screenshot reports three 15-second gait replays using sequential servo feedback:

| Replay | Mean summed absolute feedback | 95th percentile | Sampled peak sum |
| --- | --- | --- | --- |
| Latest | 129 mA | 195 mA | 241 mA |
| Previous | 121 mA | 189 mA | 202 mA |
| Earlier | 100 mA | 137 mA | 169 mA |

Latest highest individual feedback: ID 12, 123.5 mA sampled peak.
The screenshot states approximately 10 ms per servo read, hence 120 ms for
12 servos. The sum is not a simultaneous measurement and excludes other
electronics and supply losses. Sensor scaling/calibration, load condition,
and fast peaks are not verified. Do not reduce fuse or copper targets based
on these numbers. The user answered yes to the floor-supported replay question
and stated that the robot supports its weight because of the high gear ratio.
This is user-reported operation, not an independently observed load test.
Measure supply current directly with suitable transient capture.

## Harness review implications

Walking-only operation does not eliminate blocked-joint or startup faults.
With one-ended power injection into a three-servo V+/GND/DATA chain, its first
cable/contact pair carries all three servos' current. Using the user's 2.7 A
per-servo stall figure, successive segments could carry 8.1 A, 5.4 A, and
2.7 A respectively. The 16 AWG feeder does not uprate the downstream 22 AWG
lead or its contacts. Exact housing/contact identity, cable lengths, crimp
quality, fault-clearing behavior and temperature rise are still required.

Waveshare identifies the ST3215 interface as 5264-3P / 2.54 mm; 'JST' alone
does not establish its manufacturer, family or current rating:
https://docs.waveshare.com/ST3215_Servo/FAQ
https://www.waveshare.com/wiki/ST3215_Servo

The user subsequently selected one-ended power injection into each existing
three-servo daisy chain, retaining a 5 A leg fuse and expecting less than 5 A
per leg during walking based on training/gait data. Preserve that selected
configuration. Separate power tails are an alternative, not the selected
harness. Expected walking current does not establish fault current or prove
connector capacity. No servo cable has been physically modified by this work.

## 150 mm lead calculation (copper only)

Using nominal 22 AWG copper resistance of 0.0535 Ohm/m at 20 C, a 150 mm
positive plus 150 mm return pair has about 0.01605 Ohm resistance. If all three
servos draw 2.7 A each, the first pair carries 8.1 A: about 0.130 V drop and
1.05 W copper dissipation. Three successive equal-length pairs carrying
8.1/5.4/2.7 A give about 0.260 V drop to the last servo and 1.64 W distributed
cable dissipation. This model excludes contact/crimp resistance and the
servos' internal through-power paths; it is not an ampacity or temperature
approval. The first pair's aggregate current remains the concern despite the
short leads and walking-only operation.

Separate equal-length 22 AWG tails from a local leg distribution point would
each carry one servo's current: approximately 0.043 V and 0.117 W per pair at
2.7 A, before contact loss. This reduces aggregate current through the first
servo's plug but still requires correct contact ratings and fault protection.
