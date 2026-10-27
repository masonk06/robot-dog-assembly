"""Screen zero-residual gait under contact dynamics; never commands hardware."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
import numpy as np
from env import DogWalkEnv, WalkConfig


def screen(config, seed=1, model_path=None):
    env = DogWalkEnv(config, **({"model_path": model_path} if model_path is not None else {}))
    env.reset(seed=seed)
    lift_count, min_height, max_tilt = 0, 1., 0.
    try:
        while True:
            _, _, terminated, truncated, info = env.step(np.zeros(12))
            lift_count += info["foot_lifts"]
            min_height = min(min_height, info["height"])
            max_tilt = max(max_tilt, info["tilt_degrees"])
            if terminated or truncated:
                return {"config": asdict(config), "seconds": env.data.time,
                        "distance_m": info["forward_distance"], "reason": info["termination_reason"],
                        "foot_lifts": lift_count, "min_height": min_height,
                        "max_tilt_degrees": float(max_tilt),
                        "steps": {k: v for k, v in info.items() if k.startswith("steps/")}}
    finally:
        env.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--output", type=Path, default=Path("runs/reference-screen.json"))
    a = p.parse_args()
    configs = [WalkConfig()]
    if a.sweep:
        configs = [WalkConfig(reference_stride=s, reference_lift=h, gait_cycle_seconds=t)
                   for s in (.01, .02, .03) for h in (.015, .025) for t in (3., 5.)]
    results = []
    for cfg in configs:
        r = screen(cfg)
        results.append(r)
        print(json.dumps(r), flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(results, indent=2))
