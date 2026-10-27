"""First migration gate: import the saved robot into Newton on CUDA.

This checks model import only; it does not run or retrain the PPO policy.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import newton
import warp as wp

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("source", type=Path)
p.add_argument("--device", default="cuda:0")
a = p.parse_args()
wp.init()
with wp.ScopedDevice(a.device):
    builder = newton.ModelBuilder()
    newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
    builder.add_mjcf(str((a.source / "robot_dog_v2.xml").resolve()),
                     ignore_inertial_definitions=False, collapse_fixed_joints=False,
                     parse_visuals=False)
    model = builder.finalize()
    state = model.state()
    newton.eval_fk(model, model.joint_q, model.joint_qd, state)
    report = {"newton": importlib.metadata.version("newton"),
              "device": str(model.device), "body_count": model.body_count,
              "joint_labels": list(model.joint_label),
              "joint_q_count": len(model.joint_q.numpy()),
              "finite_initial_state": bool(__import__('numpy').isfinite(state.body_q.numpy()).all()),
              "status": "import_only_not_policy_validation"}
    print(json.dumps(report, indent=2))
