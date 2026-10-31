"""Apply a reviewed proposed zero capture and rebase a tick replay without servo I/O."""
import argparse
import copy
import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--current", type=Path, default=ROOT / "hardware/calibrations/zero-points-current.json")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--plan-in", type=Path, required=True)
    parser.add_argument("--plan-out", type=Path, required=True)
    parser.add_argument("--limits", type=Path, default=ROOT / "hardware/calibrations/current-frame-limits-20261029.json")
    parser.add_argument("--apply", action="store_true", help="Replace current zero-points only after generating validated outputs")
    args = parser.parse_args()
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    current = json.loads(args.current.read_text(encoding="utf-8"))
    if proposal.get("status") != "proposed_simulation_zero_capture_not_applied":
        raise ValueError("Proposal is not an unmodified read-only simulation-zero capture")
    captured = {int(sid): entry for sid, entry in proposal["servos"].items()}
    old_by_id = {entry["id"]: entry["neutral_ticks"] for entry in current["joints"].values()}
    if set(captured) != set(range(1, 13)) or set(old_by_id) != set(range(1, 13)):
        raise ValueError("Expected exactly servo IDs 1..12")

    updated = copy.deepcopy(current)
    updated["status"] = "operator_aligned_simulation_zero_applied"
    updated["recorded_local"] = datetime.now().astimezone().isoformat()
    updated["simulation_alignment"] = {
        "proposal": str(args.proposal),
        "method": "Operator manually matched physical robot to rendered MuJoCo model-zero side references; serial READ capture was torque-off.",
        "previous_calibration": str(args.backup),
        "not_servo_eeprom": True,
    }
    for entry in updated["joints"].values():
        entry["neutral_ticks"] = captured[entry["id"]]["ticks"]
        entry["simulation_zero_capture"] = captured[entry["id"]]

    limits = json.loads(args.limits.read_text(encoding="utf-8"))["joints"]
    permitted = {item["id"]: (item["minimum_ticks"] + 10, item["maximum_ticks"] - 10)
                 for item in limits.values()}
    for servo_id, value in ((entry["id"], entry["neutral_ticks"]) for entry in updated["joints"].values()):
        low, high = permitted[servo_id]
        if not low <= value <= high:
            raise ValueError(f"New neutral ID {servo_id}={value} outside reviewed bounds {low}..{high}")

    with args.plan_in.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle); fields = reader.fieldnames; rows = list(reader)
    if fields is None or any(str(i) not in fields for i in range(1, 13)):
        raise ValueError("Plan must contain time_seconds and servo IDs 1..12")
    shift = {sid: captured[sid]["ticks"] - old_by_id[sid] for sid in range(1, 13)}
    for row in rows:
        for sid in range(1, 13):
            target = int(row[str(sid)]) + shift[sid]
            low, high = permitted[sid]
            if not low <= target <= high:
                raise ValueError(f"Rebased ID {sid} target {target} outside reviewed bounds {low}..{high}")
            row[str(sid)] = str(target)

    write_json(args.snapshot, updated)
    args.plan_out.parent.mkdir(parents=True, exist_ok=True)
    with args.plan_out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    write_json(args.plan_out.with_suffix(".json"), {
        "source_plan": str(args.plan_in), "rebased_for": str(args.snapshot),
        "tick_shift_by_servo_id": shift,
        "note": "Same model-relative trajectory after software zero alignment; no hardware registers changed.",
    })
    if args.apply:
        if args.backup.exists():
            raise FileExistsError(f"Backup already exists: {args.backup}")
        write_json(args.backup, current)
        write_json(args.current, updated)
    print(json.dumps({"snapshot": str(args.snapshot), "current_updated": args.apply,
                      "backup": str(args.backup), "rebased_plan": str(args.plan_out),
                      "shift_ticks": shift}, indent=2))


if __name__ == "__main__":
    main()
