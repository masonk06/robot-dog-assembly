"""Compare open-loop reference targets under CPU MuJoCo and Newton CUDA."""
import argparse
import json
from pathlib import Path
import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("mode", choices=["record", "compare"])
p.add_argument("source", type=Path)
p.add_argument("--trace", type=Path, default=Path("reference-trace.npz"))
p.add_argument("--seconds", type=float, default=6.)
a = p.parse_args()
if a.mode == "record":
    from env import DogWalkEnv, WalkConfig
    cfg = WalkConfig(reset_noise=0, episode_seconds=a.seconds)
    env = DogWalkEnv(cfg, model_path=a.source / "robot_dog_v2.xml")
    env.reset(seed=1)
    q0 = env.data.qpos.copy()
    targets, poses = [], []
    for _ in range(round(a.seconds/cfg.control_dt)):
        _, _, done, timeout, _ = env.step(np.zeros(12))
        targets.append(env.targets.copy())
        poses.append(env.data.xpos[env.base].copy())
        if done or timeout:
            break
    np.savez(a.trace, targets=targets, poses=poses, q0=q0,
             names=np.array(env.names), dt=cfg.control_dt,
             physics_dt=env.model.opt.timestep)
    env.close()
    print(f"Recorded {len(targets)} control frames to {a.trace}")
else:
    import newton
    import warp as wp
    wp.init()
    trace = np.load(a.trace)
    with wp.ScopedDevice("cuda:0"):
        b = newton.ModelBuilder()
        newton.solvers.SolverMuJoCo.register_custom_attributes(b)
        b.add_mjcf(str((a.source / "robot_dog_v2.xml").resolve()),
                   parse_visuals=False, ctrl_direct=True)
        model = b.finalize()
        solver = newton.solvers.SolverMuJoCo(model, use_mujoco_contacts=True,
                                             njmax=256, nconmax=128)
        s0, s1, control = model.state(), model.state(), model.control()
        newton.eval_fk(model, s0.joint_q, s0.joint_qd, s0)
        names = [str(x).split('/')[-1] for x in model.joint_label]
        missing = set(trace['names']) - set(names)
        if missing:
            raise RuntimeError(f"Missing joints: {missing}")
        if control.mujoco.ctrl.shape[0] != 12:
            raise RuntimeError("Expected twelve imported direct actuators")
        # Verify gain and force caps in the solver's generated MuJoCo model.
        m = solver.mj_model
        np.testing.assert_allclose(m.actuator_gainprm[:,0], 12)
        np.testing.assert_allclose(m.actuator_biasprm[:,1], -12)
        np.testing.assert_allclose(m.actuator_biasprm[:,2], -.15)
        np.testing.assert_allclose(m.actuator_forcerange, np.tile([-1,1], (12,1)))
        # CTRL_DIRECT uses original MJCF actuator order, not generated names.
        import xml.etree.ElementTree as ET
        generated_names = [x.attrib['name'] for x in ET.parse(a.source / 'robot_dog_v2.xml').getroot().find('actuator')]
        order = [list(trace['names']).index(n) for n in generated_names]
        poses = []
        base = next(i for i,n in enumerate(model.body_label) if n.split('/')[-1]=='base')
        for target in trace['targets']:
            control.mujoco.ctrl.assign(np.asarray(target[order], np.float32))
            for _ in range(round(float(trace['dt'])/float(trace['physics_dt']))):
                s0.clear_forces()
                solver.step(s0, s1, control, None, float(trace['physics_dt']))
                s0, s1 = s1, s0
            poses.append(s0.body_q.numpy()[base,:3])
        poses = np.asarray(poses)
        report = {"frames":len(poses), "finite":bool(np.isfinite(poses).all()),
                  "newton_final_base_xyz":poses[-1].tolist(),
                  "mujoco_final_base_xyz":trace['poses'][-1].tolist(),
                  "base_position_rmse_m":float(np.sqrt(np.mean((poses-trace['poses'])**2))),
                  "newton_min_height_m":float(poses[:,2].min()),
                  "status":"reference_comparison_not_policy_validation"}
        Path("newton-reference-report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
