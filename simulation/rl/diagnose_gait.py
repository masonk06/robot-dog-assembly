"""Measure achieved swing motion and tracking; simulation only."""
import json
from dataclasses import replace, asdict
from pathlib import Path
import numpy as np
from env import DogWalkEnv, WalkConfig, LEGS, gait_pattern


def diagnose(config):
    env = DogWalkEnv(config)
    samples = [[] for _ in LEGS]
    env.reset(seed=1)
    touchdowns = []
    original_update = env.cycles.update
    def track(contacts, positions, now, dt, moving, forward_position=None):
        c = env.cycles
        for i in range(4):
            if contacts[i] and not c.previous[i] and c.supported[i]:
                touchdowns.append({"leg": LEGS[i], "time": now,
                    "airtime": float(c.air[i]), "clearance_mm": float(c.clearance[i]*1000),
                    "travel_mm": float(np.linalg.norm(positions[i,:2]-c.lift[i,:2])*1000),
                    "moving": bool(moving)})
        return original_update(contacts, positions, now, dt, moving, forward_position)
    env.cycles.update = track
    try:
        while True:
            _, _, done, timeout, info = env.step(np.zeros(12))
            forces, _ = env._feet()
            swing, _ = gait_pattern(env.phase())
            for i, leg in enumerate(LEGS):
                if swing[i] and env.data.time > config.gait_cycle_seconds:
                    ix = [j for j, name in enumerate(env.names) if name.startswith(leg)]
                    samples[i].append([
                        float(env.data.site_xpos[env.feet[i], 2] - .003),
                        float(forces[i]),
                        float(np.max(np.abs(env.data.qpos[env.qadr[ix]] - env.targets[ix]))),
                        float(np.max(np.abs(env.data.actuator_force[ix]))),
                    ])
            if done or timeout:
                break
        result = {"config": asdict(config), "seconds": env.data.time,
                  "reason": info["termination_reason"], "distance_m": info["forward_distance"],
                  "legs": {}, "touchdowns": touchdowns}
        for leg, values in zip(LEGS, samples):
            a = np.asarray(values)
            result["legs"][leg] = {
                "max_swing_clearance_mm": float(a[:, 0].max()*1000),
                "swing_air_fraction": float(np.mean(a[:, 1] <= .2)),
                "mean_swing_force_n": float(a[:, 1].mean()),
                "max_tracking_error_deg": float(np.rad2deg(a[:, 2].max())),
                "peak_actuator_force_nm": float(a[:, 3].max()),
                "credited_steps": info[f"steps/{leg}"],
            } if len(a) else {}
        return result
    finally:
        env.close()


if __name__ == "__main__":
    base = WalkConfig()
    cases = {
        "baseline": base,
        "slower": replace(base, gait_cycle_seconds=5),
        "no_weight_shift": replace(base, reference_weight_shift=0),
        "reverse_weight_shift": replace(base, reference_weight_shift=-.01),
        "no_sway": replace(base, reference_sway=0),
        "reverse_sway": replace(base, reference_sway=-.06),
    }
    results = {}
    for name, config in cases.items():
        results[name] = diagnose(config)
        print(json.dumps({name: results[name]}), flush=True)
    output = Path("runs/gait-diagnostics.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
