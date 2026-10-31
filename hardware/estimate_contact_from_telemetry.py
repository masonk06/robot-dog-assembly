"""Estimate foot-contact candidates from phase and STS3215 telemetry.

Diagnostic only: this does not command hardware and must not be fed into the
saved 60-input policy. Its purpose is to determine whether foot sensors are
actually needed after supported ground trials.
"""
import argparse
import csv
import json
from pathlib import Path


LEGS = {
    "front_left": {"ids": (4, 5, 6), "offset": .25},
    "front_right": {"ids": (1, 2, 3), "offset": .75},
    "rear_left": {"ids": (7, 8, 9), "offset": 0.0},
    "rear_right": {"ids": (11, 10, 12), "offset": .50},
}
CYCLE_SECONDS = 3.0
SWING_FRACTION = .20


def clamp(value, low=0., high=1.):
    return max(low, min(high, value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("telemetry", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--load-scale-percent", type=float, default=15.0)
    parser.add_argument("--error-scale-ticks", type=float, default=30.0)
    args = parser.parse_args()
    events = [json.loads(line) for line in args.telemetry.read_text(encoding="utf-8").splitlines()]
    events.sort(key=lambda event: event["host_elapsed_s"])
    latest, rows = {}, []
    held = {leg: False for leg in LEGS}
    for event in events:
        if "servo_id" in event:
            latest[event["servo_id"]] = event
            continue
        raw = event["raw"]
        if not raw.startswith("FRAME_SENT,"):
            continue
        fields = raw.split(",")
        simulated_time = float(fields[1])
        row = {"host_elapsed_s": f"{event['host_elapsed_s']:.4f}", "simulated_time_s": f"{simulated_time:.4f}"}
        for name, spec in LEGS.items():
            local = (simulated_time / CYCLE_SECONDS - spec["offset"]) % 1.0
            planned_stance = local >= SWING_FRACTION
            samples = [latest.get(servo_id) for servo_id in spec["ids"]]
            fresh = all(sample and event["host_elapsed_s"] - sample["host_elapsed_s"] <= .35 for sample in samples)
            if fresh:
                mean_load = sum(abs(sample["load_tenth_percent"]) / 10 for sample in samples) / len(samples)
                mean_error = sum(abs(sample["actual_ticks"] - sample["target_ticks"]) for sample in samples) / len(samples)
                # Phase provides a prior; load and target error provide soft,
                # imperfect evidence of a blocked/weight-bearing foot.
                score = (.35 if planned_stance else .05) + .40 * clamp(mean_load / args.load_scale_percent) + .25 * clamp(mean_error / args.error_scale_ticks)
                if not planned_stance:
                    held[name] = False
                elif held[name]:
                    held[name] = score >= .48
                else:
                    held[name] = score >= .72
                confidence = "experimental"
            else:
                mean_load = mean_error = float("nan")
                held[name] = False
                score = 0.
                confidence = "insufficient_telemetry"
            prefix = name + "_"
            row.update({prefix + "planned_stance": int(planned_stance), prefix + "load_pct": f"{mean_load:.3f}",
                        prefix + "tracking_error_ticks": f"{mean_error:.3f}", prefix + "contact_score": f"{score:.3f}",
                        prefix + "contact_candidate": int(held[name]), prefix + "confidence": confidence})
        rows.append(row)
    if not rows:
        raise ValueError("No FRAME_SENT records found; rerun a --log-imu replay with the updated receiver")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {name: sum(int(row[name + "_contact_candidate"]) for row in rows) / len(rows) for name in LEGS}
    print(json.dumps({"output": str(args.output), "frames": len(rows), "candidate_fraction": summary,
                      "warning": "Diagnostic estimator only; not a ground-truth contact signal or policy input."}, indent=2))


if __name__ == "__main__":
    main()
