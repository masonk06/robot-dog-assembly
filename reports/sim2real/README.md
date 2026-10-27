# Supported rear-left transfer evidence

Representative tracking logs from 2026-10-26, commanding only IDs 8/9:

| File | Trial |
| --- | --- |
| 20261026-212718.csv | 3-degree, 9.24-second initial replay |
| 20261026-213629.csv | 5-degree, 13.86-second replay |
| 20261026-220232.csv | Full-amplitude, faster 46.2-second supported replay |
| 20261026-220232.status.json | Faster trial completed; torque release verified |

CSV records time, ID, commanded/measured ticks, error and temperature.
Resolution is 360/4096 degrees per tick. This measures joint tracking on a
stand, not balance, ground walking or world motion. The user confirmed
rear-left calibration afterward. Current neutral: hip 1677, knee 1572 ticks.
See hardware/calibrations for raw captures and conservative no-wrap bounds.
