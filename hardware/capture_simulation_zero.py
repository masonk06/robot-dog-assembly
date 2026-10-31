"""Read and save a proposed simulation-zero encoder capture; never commands motion."""
import argparse
import json
from datetime import datetime
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".servo_tools"))
import serial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "hardware/calibrations/proposed-simulation-zero.json")
    args = parser.parse_args()
    bus = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=.2)
    bus.dtr = bus.rts = False
    bus.port = args.port
    captures = {}
    try:
        bus.open(); bus.reset_input_buffer(); bus.write(b"READ\n"); bus.flush()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            line = bus.readline().decode("ascii", errors="replace").strip()
            if line: print(line)
            fields = line.split(",")
            if len(fields) == 7 and fields[0] == "READ":
                servo_id, ticks, torque, status, voltage, temperature = map(int, fields[1:])
                if torque != 0 or status != 0:
                    raise RuntimeError(f"ID {servo_id} is not torque-off/healthy: torque={torque}, status={status}")
                captures[servo_id] = {"ticks": ticks, "voltage_v": voltage / 10, "temperature_c": temperature}
            if line == "READ_DONE": break
        if set(captures) != set(range(1, 13)):
            raise RuntimeError(f"Expected all IDs 1..12; received {sorted(captures)}")
    finally:
        if bus.is_open: bus.close()
    payload = {
        "status": "proposed_simulation_zero_capture_not_applied",
        "captured_local": datetime.now().astimezone().isoformat(),
        "port": args.port,
        "operator_instruction": "Capture only after manually aligning physical robot to the simulation zero reference images.",
        "servos": {str(i): captures[i] for i in range(1, 13)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Saved proposed capture to {args.output}. Current calibration was not changed.")


if __name__ == "__main__":
    main()
