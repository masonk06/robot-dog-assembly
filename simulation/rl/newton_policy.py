"""Closed-loop saved-policy evaluation in Newton; CPU mirror computes observations only."""
import argparse
import json
from pathlib import Path
import numpy as np
import mujoco
import newton
import warp as wp
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from env import DogWalkEnv, WalkConfig

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("checkpoint", type=Path)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--seconds", type=float, default=20.)
p.add_argument("--output", type=Path, default=Path("newton-policy-report.json"))
a = p.parse_args()
torch.set_num_threads(2)
cfg = WalkConfig(**json.loads((a.checkpoint/'environment.json').read_text())['task'])
if cfg.reward_version != 7:
    raise ValueError('This migration gate requires the selected version 7 checkpoint')
mirror = DogWalkEnv(cfg, model_path=a.source/'robot_dog_v2.xml')
vec = DummyVecEnv([lambda: mirror])
normalizer = VecNormalize.load(str(a.checkpoint/'normalize.pkl'), vec)
normalizer.training = False
normalizer.norm_reward = False
policy = PPO.load(a.checkpoint/'policy.zip', device='cpu')
wp.init()
reports = []
with wp.ScopedDevice('cuda:0'):
    b = newton.ModelBuilder()
    newton.solvers.SolverMuJoCo.register_custom_attributes(b)
    b.add_mjcf(str((a.source/'robot_dog_v2.xml').resolve()), parse_visuals=False, ctrl_direct=True)
    model = b.finalize()
    solver = newton.solvers.SolverMuJoCo(model, use_mujoco_contacts=True, njmax=256, nconmax=128)
    m = solver.mj_model
    # Fail rather than silently reinterpreting a different coordinate layout.
    assert (m.nq, m.nv, m.nu) == (mirror.model.nq, mirror.model.nv, 12)
    for field in ('jnt_type', 'jnt_axis', 'jnt_qposadr', 'jnt_dofadr', 'jnt_range', 'actuator_trnid'):
        np.testing.assert_allclose(getattr(m, field), getattr(mirror.model, field), atol=1e-6)
    for field in ('actuator_gainprm', 'actuator_biasprm', 'actuator_forcerange'):
        np.testing.assert_allclose(getattr(m, field), getattr(mirror.model, field), atol=1e-6)
    for seed in (10000, 10001, 10002):
        mirror.reset(seed=seed)
        # Newton free-joint quaternion is xyzw; MuJoCo is wxyz.
        initial = mirror.data.qpos.copy()
        initial[3:7] = initial[[4,5,6,3]]
        s0, s1, control = model.state(), model.state(), model.control()
        s0.joint_q.assign(initial.astype(np.float32))
        newton.eval_fk(model, s0.joint_q, s0.joint_qd, s0)
        trajectory = []
        for frame in range(round(min(a.seconds,cfg.episode_seconds)/cfg.control_dt)):
            obs = normalizer.normalize_obs(mirror._obs()[None])
            action, _ = policy.predict(obs, deterministic=True)
            action = np.clip(action[0], -1, 1)
            alpha = 1-np.exp(-cfg.control_dt/cfg.residual_time_constant)
            mirror.filtered_action += alpha*(action-mirror.filtered_action)
            desired = np.clip(mirror.reference()+cfg.action_scale*mirror.filtered_action,
                              mirror.limits[:,0],mirror.limits[:,1])
            mirror.targets += np.clip(desired-mirror.targets,
                                      -cfg.max_target_rate*cfg.control_dt,cfg.max_target_rate*cfg.control_dt)
            control.mujoco.ctrl.assign(mirror.targets.astype(np.float32))
            for _ in range(mirror.frame_skip):
                s0.clear_forces()
                solver.step(s0,s1,control,None,mirror.model.opt.timestep)
                s0,s1 = s1,s0
            # Read GPU dynamics, then compute kinematics/observations on CPU.
            # No CPU mj_step is called here. This is a validation bridge,
            # deliberately not a high-throughput GPU training implementation.
            mirror.data.qpos[:] = solver.mjw_data.qpos.numpy()[0]
            mirror.data.qvel[:] = solver.mjw_data.qvel.numpy()[0]
            mirror.data.time = (frame+1)*cfg.control_dt
            mirror.last_action = action.copy()
            mujoco.mj_forward(mirror.model,mirror.data)
            gravity,_,_ = mirror._state()
            height = float(mirror.data.xpos[mirror.base,2])
            tilt = float(np.rad2deg(np.arccos(np.clip(-gravity[2],-1,1))))
            trajectory.append(mirror.data.qpos.copy())
            if not np.isfinite(mirror.data.qpos).all() or height<cfg.min_height or tilt>cfg.max_tilt_degrees:
                break
        report = {'seed':seed,'seconds':mirror.data.time,
                  'forward_distance_m':mirror.start_x-float(mirror.data.xpos[mirror.base,0]),
                  'final_height_m':height,'final_tilt_degrees':tilt,
                  'completed':len(trajectory)==round(min(a.seconds,cfg.episode_seconds)/cfg.control_dt)}
        reports.append(report)
        np.savez(a.output.with_name(f'newton-policy-seed-{seed}.npz'),qpos=trajectory,dt=cfg.control_dt)
        print(json.dumps(report),flush=True)
result={'status':'closed_loop_policy_validation_not_training','episodes':reports,
        'notes':'CPU observation bridge; no sliding reset or step reward evaluation in this gate.'}
a.output.write_text(json.dumps(result,indent=2))
normalizer.close()
