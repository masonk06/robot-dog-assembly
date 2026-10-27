"""MuJoCo-only slow locomotion task. No serial/hardware dependencies."""
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

MODEL = Path(__file__).resolve().parents[1] / "mujoco" / "robot_dog_v2.xml"
if not MODEL.exists():
    MODEL = Path(__file__).resolve().parents[2] / "source" / "robot_dog_v2.xml"
LEGS = ("front_left", "front_right", "rear_left", "rear_right")
# Swing order: rear-left, front-left, rear-right, front-right.
SWING_OFFSETS = np.array([.25, .75, 0., .5])


def gait_pattern(phase, swing_fraction=.20):
    local = (phase - SWING_OFFSETS) % 1.
    swing = local < swing_fraction
    lift = np.where(swing, np.sin(np.pi * np.clip(local / swing_fraction, 0, 1)), 0.)
    return swing, lift


def slip_penalty(mean_squared_speed, scale=.03, weight=2.):
    return -weight * float(np.clip(mean_squared_speed / scale ** 2, 0., 10.))


@dataclass
class WalkConfig:
    reward_version: int = 7
    target_speed: float = 0.01
    tracking_reward_weight: float = 1.0
    control_dt: float = 0.02
    episode_seconds: float = 20.0
    action_scale: float = 0.035
    residual_time_constant: float = 0.12
    max_target_rate: float = 1.5
    min_height: float = 0.06
    max_tilt_degrees: float = 45.0
    reset_noise: float = 0.015
    min_airtime: float = 0.12
    min_clearance: float = 0.004
    min_step_distance: float = 0.004
    leg_use_window: float = 12.0
    soft_landing_speed: float = 0.15
    lift_clearance: float = 0.008
    slip_distance: float = 0.004
    slip_speed: float = 0.04
    slip_duration: float = 0.08
    slip_grace: float = 0.30
    gait_cycle_seconds: float = 3.0
    severe_slip_distance: float = 0.02
    severe_slip_speed: float = 0.08
    severe_slip_duration: float = 0.5
    reference_stride: float = 0.020
    reference_lift: float = 0.025
    reference_ramp_seconds: float = 1.0
    reference_sway: float = 0.06
    reference_weight_shift: float = 0.01
    reference_rear_lift_multiplier: float = 1.5


class SlidingMonitor:
    """Track planted feet in world coordinates, tolerating brief force chatter."""
    def __init__(self, config):
        self.config = config
        self.anchors = np.zeros((4, 2))
        self.age = np.zeros(4)
        self.gap = np.full(4, 1.)
        self.bad_time = np.zeros(4)

    def update(self, contacts, positions, velocities, now, dt):
        cfg = self.config
        for i in range(4):
            if contacts[i]:
                if self.gap[i] > .04:
                    self.anchors[i] = positions[i, :2]
                    self.age[i] = self.bad_time[i] = 0
                self.gap[i] = 0
                self.age[i] += dt
            else:
                self.gap[i] += dt
                if self.gap[i] > .04:
                    self.age[i] = self.bad_time[i] = 0
        drift = np.linalg.norm(positions[:, :2] - self.anchors, axis=1)
        speed = np.linalg.norm(velocities[:, :2], axis=1)
        distance_limit = cfg.severe_slip_distance if cfg.reward_version >= 4 else cfg.slip_distance
        speed_limit = cfg.severe_slip_speed if cfg.reward_version >= 4 else cfg.slip_speed
        duration_limit = cfg.severe_slip_duration if cfg.reward_version >= 4 else cfg.slip_duration
        bad = (contacts & (self.age >= .08) & (now > cfg.slip_grace)
               & ((drift > distance_limit) | (speed > speed_limit)))
        self.bad_time = np.where(bad, self.bad_time + dt, 0.)
        return bool(np.any(self.bad_time >= duration_limit)), float(np.max(drift[contacts], initial=0.))


class FootCycles:
    """Credit lift/land cycles, excluding initial drops and stationary taps."""
    def __init__(self, config):
        self.config = config
        self.supported = np.zeros(4, dtype=bool)
        self.previous = np.zeros(4, dtype=bool)
        self.air = np.zeros(4)
        self.lift = np.zeros((4, 3))
        self.clearance = np.zeros(4)
        self.last_step = np.full(4, -np.inf)
        self.credits = np.zeros(4, dtype=bool)
        self.counts = np.zeros(4, dtype=int)
        self.lift_paid = np.zeros(4, dtype=bool)
        self.last_lift = np.full(4, -np.inf)
        self.new_lifts = 0
        self.new_lift_mask = np.zeros(4, dtype=bool)
        self.body_at_liftoff = np.zeros(4)
        self.body_at_touchdown = np.zeros(4)

    def update(self, contacts, positions, now, dt, moving, forward_position=None):
        cfg = self.config
        if forward_position is not None:
            self.body_at_touchdown[contacts & ~self.supported] = forward_position
        for i in range(4):
            if self.previous[i] and not contacts[i]:
                if forward_position is not None:
                    self.body_at_liftoff[i] = forward_position
                self.lift[i] = positions[i]
                self.air[i] = self.clearance[i] = 0
                self.lift_paid[i] = False
            if not contacts[i]:
                self.air[i] += dt
                self.clearance[i] = max(self.clearance[i], positions[i, 2] - self.lift[i, 2])
        touchdown = contacts & ~self.previous
        travel = np.linalg.norm(positions[:, :2] - self.lift[:, :2], axis=1)
        lifted = (~contacts & self.supported & ~self.lift_paid
                  & (self.air >= .08) & (self.air <= .5)
                  & (self.clearance >= cfg.lift_clearance)
                  & (travel >= cfg.min_step_distance) & ((now - self.last_lift) >= .5))
        self.new_lifts = int(lifted.sum())
        self.new_lift_mask = lifted.copy()
        self.lift_paid[lifted] = True
        self.last_lift[lifted] = now
        progress = moving
        if cfg.reward_version >= 6 and forward_position is not None:
            # Net progress since this foot's preceding landing includes stance
            # propulsion and swing. A brief slowdown at landing is acceptable.
            progress = ((forward_position - self.body_at_touchdown) > .0005)
        valid = (touchdown & self.supported & (self.air >= cfg.min_airtime)
                 & (self.clearance >= cfg.min_clearance) & (travel >= cfg.min_step_distance)
                 & ((now - self.last_step) >= .5) & progress)
        if forward_position is not None:
            completed = touchdown & (self.air >= cfg.min_airtime)
            self.body_at_touchdown[completed] = forward_position
        self.last_step[valid] = now
        self.counts[valid] += 1
        self.credits &= (now - self.last_step) <= cfg.leg_use_window
        self.credits |= valid
        all_four = bool(self.credits.all())
        if all_four:
            self.credits[:] = False
        self.supported |= contacts
        self.air[contacts] = 0
        self.previous = contacts.copy()
        return int(valid.sum()), all_four


class DogWalkEnv(gym.Env):
    """12 bounded position targets; body -X is forward in the CAD frame."""
    metadata = {"render_modes": ["human"], "render_fps": 50}

    def __init__(self, config=None, render_mode=None, model_path=MODEL):
        super().__init__()
        self.config = config or WalkConfig()
        if self.config.target_speed <= 0 or self.config.control_dt <= 0:
            raise ValueError("Speed and control timestep must be positive")
        self.model_path = Path(model_path).resolve()
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)
        self.render_mode = render_mode
        self.viewer = None
        self.base = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "base")
        if self.base < 0 or self.model.nu != 12:
            raise ValueError("Expected base body and twelve actuators")
        self.joints = self.model.actuator_trnid[:, 0].copy()
        self.qadr = self.model.jnt_qposadr[self.joints]
        self.vadr = self.model.jnt_dofadr[self.joints]
        self.names = [mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_JOINT, int(j))
                      for j in self.joints]
        if not np.all(self.model.jnt_limited[self.joints]):
            raise ValueError("All policy-controlled joints must have limits")
        self.limits = self.model.jnt_range[self.joints].copy()
        self.neutral = np.clip(np.zeros(12), self.limits[:, 0], self.limits[:, 1])
        self.frame_skip = round(self.config.control_dt / self.model.opt.timestep)
        if self.frame_skip < 1 or not np.isclose(
                self.frame_skip * self.model.opt.timestep, self.config.control_dt):
            raise ValueError("Control timestep must be an integer multiple of physics timestep")
        self.action_space = spaces.Box(-1.0, 1.0, shape=(12,), dtype=np.float32)
        # Local gravity, angular/linear velocity, command, joint errors/speeds,
        # and previous actions. No absolute world position or simulator clock.
        self.obs_size = 60 if self.config.reward_version >= 5 else 48 if self.config.reward_version >= 4 else 46
        self.observation_space = spaces.Box(-np.inf, np.inf, (self.obs_size,), np.float32)
        self.phase_offset = 0.
        self.last_action = np.zeros(12)
        self.filtered_action = np.zeros(12)
        self.targets = self.neutral.copy()
        self.steps = 0
        self.start_x = 0.0
        self.feet = np.array([mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, f"{leg}_foot") for leg in LEGS])
        geoms = [mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, f"{leg}_foot_contact_proxy") for leg in LEGS]
        self.floor = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
        if min(*self.feet, *geoms, self.floor) < 0:
            raise ValueError("Expected four foot sites/contact proxies and a floor")
        self.geom_to_foot = {g: i for i, g in enumerate(geoms)}
        self.soft_force = 3 * float(self.model.body_mass.sum()) * 9.80665 / 4
        self.cycles = FootCycles(self.config)
        self.sliding = SlidingMonitor(self.config)

    def _feet(self):
        forces, velocities = np.zeros(4), np.zeros((4, 3))
        for i, site in enumerate(self.feet):
            v = np.zeros(6)
            mujoco.mj_objectVelocity(self.model, self.data, mujoco.mjtObj.mjOBJ_SITE, int(site), v, 0)
            velocities[i] = v[3:]
        for c in range(self.data.ncon):
            contact = self.data.contact[c]
            other = contact.geom2 if contact.geom1 == self.floor else contact.geom1 if contact.geom2 == self.floor else -1
            if other in self.geom_to_foot:
                wrench = np.zeros(6)
                mujoco.mj_contactForce(self.model, self.data, c, wrench)
                forces[self.geom_to_foot[other]] += max(0., wrench[0])
        return forces, velocities

    def _state(self):
        velocity = np.zeros(6)
        mujoco.mj_objectVelocity(self.model, self.data, mujoco.mjtObj.mjOBJ_BODY,
                                self.base, velocity, 1)
        rotation = self.data.xmat[self.base].reshape(3, 3)
        gravity = rotation.T @ np.array([0., 0., -1.])
        return gravity, velocity[:3], velocity[3:]

    def _obs(self):
        gravity, angular, linear = self._state()
        obs = np.concatenate((gravity, angular, linear, [self.config.target_speed],
                               self.data.qpos[self.qadr] - self.neutral,
                               self.data.qvel[self.vadr], self.last_action))
        if self.config.reward_version >= 4:
            angle = 2 * np.pi * self.phase()
            obs = np.concatenate((obs, [np.sin(angle), np.cos(angle)]))
        if self.config.reward_version >= 5:
            obs = np.concatenate((obs, self.reference()))
        return obs.astype(np.float32)

    def reference(self):
        """Per-leg IK from the loaded model, not a shared rear-leg approximation."""
        cfg = self.config
        targets = self.neutral.copy()
        phase = self.phase()
        ramp = min(1., self.data.time / cfg.reference_ramp_seconds)
        ramp = ramp * ramp * (3 - 2 * ramp)
        for i, leg in enumerate(LEGS):
            local = (phase - SWING_OFFSETS[i]) % 1.
            if local < .2:
                t = local / .2
                x_offset = cfg.reference_stride * (.5 - t * t * (3 - 2 * t))
                lift = cfg.reference_lift * np.sin(np.pi * t) ** 2
                if leg.startswith("rear"):
                    lift *= cfg.reference_rear_lift_multiplier
            else:
                t = (local - .2) / .8
                x_offset = cfg.reference_stride * (-.5 + t * t * (3 - 2 * t))
                lift = 0.
            lower_body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, f"{leg}_lower_link")
            upper = self.model.body_pos[lower_body][[0, 2]]
            lower = self.model.site_pos[self.feet[i]][[0, 2]]
            l1, l2 = np.linalg.norm(upper), np.linalg.norm(lower)
            alpha, beta = np.arctan2(upper[1], upper[0]), np.arctan2(lower[1], lower[0])
            # Move stance targets opposite the desired body weight shift.
            weight_shift = cfg.reference_weight_shift * np.cos(4 * np.pi * (phase - .1))
            x, z = upper + lower + np.array([x_offset + weight_shift, lift])
            cosine = (x*x + z*z - l1*l1 - l2*l2) / (2*l1*l2)
            if abs(cosine) > 1 + 1e-6:
                raise ValueError(f"Unreachable {leg} reference target; reduce stride/lift")
            elbow = np.sign(beta - alpha) * np.arccos(np.clip(cosine, -1, 1))
            hip = np.arctan2(z, x) - np.arctan2(l2*np.sin(elbow), l1+l2*np.cos(elbow)) - alpha
            knee = elbow - (beta - alpha)
            for joint, value in ((f"{leg}_hip_pitch", hip), (f"{leg}_knee_pitch", knee)):
                index = self.names.index(joint)
                targets[index] = ramp * value
        swing, curve = gait_pattern(phase)
        sway = sum((-1 if LEGS[i].endswith("left") else 1) * curve[i]
                   for i in range(4) if swing[i]) * cfg.reference_sway * ramp
        for i, name in enumerate(self.names):
            if name.endswith("hip_roll"):
                targets[i] = sway
        if np.any(targets < self.limits[:, 0]) or np.any(targets > self.limits[:, 1]):
            raise ValueError("Reference exceeds model joint limits")
        return targets

    def phase(self):
        return (self.phase_offset + self.data.time / self.config.gait_cycle_seconds) % 1.

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.phase_offset = float(self.np_random.uniform()) if 4 <= self.config.reward_version < 5 else 0.
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[self.qadr] = np.clip(
            self.neutral + self.np_random.uniform(-self.config.reset_noise,
                                                  self.config.reset_noise, 12),
            self.limits[:, 0], self.limits[:, 1])
        self.targets = self.data.qpos[self.qadr].copy()
        self.data.ctrl[:] = self.targets
        self.last_action[:] = 0
        self.filtered_action[:] = 0
        self.cycles = FootCycles(self.config)
        self.sliding = SlidingMonitor(self.config)
        self.steps = 0
        mujoco.mj_forward(self.model, self.data)
        self.start_x = float(self.data.xpos[self.base, 0])
        return self._obs(), {}

    def step(self, action):
        action = np.asarray(action, dtype=np.float64)
        if action.shape != (12,) or not np.isfinite(action).all():
            raise ValueError("Expected twelve finite actions")
        action = np.clip(action, -1, 1)
        reference = self.reference() if self.config.reward_version >= 5 else self.neutral
        residual = action
        if self.config.reward_version >= 7:
            alpha = 1 - np.exp(-self.config.control_dt / self.config.residual_time_constant)
            self.filtered_action += alpha * (action - self.filtered_action)
            residual = self.filtered_action
        desired = np.clip(reference + self.config.action_scale * residual,
                          self.limits[:, 0], self.limits[:, 1])
        max_change = self.config.max_target_rate * self.config.control_dt
        self.targets += np.clip(desired - self.targets, -max_change, max_change)
        self.data.ctrl[:] = self.targets
        impact, force_cost, slip_cost, useful_steps, four_cycles = 0., 0., 0., 0, 0
        peak_force, peak_landing = 0., 0.
        sliding, max_drift, foot_lifts = False, 0., 0
        pattern_score, clearance_score, scheduled_lifts = 0., 0., 0
        for _ in range(self.frame_skip):
            _, before_v = self._feet()
            previous = self.cycles.previous.copy()
            mujoco.mj_step(self.model, self.data)
            forces, velocity = self._feet()
            contacts = forces > .2
            touchdown = contacts & ~previous
            landing = np.maximum(0., -before_v[:, 2])
            impact += float(np.sum(np.maximum(0., landing[touchdown] - self.config.soft_landing_speed) ** 2))
            force_cost += float(np.mean(np.maximum(0., forces / self.soft_force - 1.) ** 2)) / self.frame_skip
            slip_cost += float(np.mean(contacts * np.sum(velocity[:, :2] ** 2, axis=1))) / self.frame_skip
            _, _, base_v = self._state()
            count, cycle = self.cycles.update(contacts, self.data.site_xpos[self.feet], self.data.time,
                                             self.model.opt.timestep, -base_v[0] > self.config.target_speed * .25,
                                             forward_position=-float(self.data.xpos[self.base, 0]))
            useful_steps += count
            foot_lifts += self.cycles.new_lifts
            if self.config.reward_version >= 4:
                swing, lift_curve = gait_pattern(self.phase())
                pattern_score += float(np.mean(contacts == ~swing)) / self.frame_skip
                # Site centers coincide with the existing 3 mm foot spheres.
                clearance = np.maximum(0., self.data.site_xpos[self.feet, 2] - .003)
                if swing.any():
                    desired_lift = self.config.lift_clearance * lift_curve[swing]
                    score = np.exp(-((clearance[swing] - desired_lift) / .004) ** 2)
                    clearance_score += float(np.mean(score * (~contacts[swing]) * lift_curve[swing])) / self.frame_skip
                scheduled_lifts += int(np.sum(self.cycles.new_lift_mask & swing))
            four_cycles += int(cycle)
            slip, drift = self.sliding.update(contacts, self.data.site_xpos[self.feet], velocity,
                                               self.data.time, self.model.opt.timestep)
            max_drift = max(max_drift, drift)
            sliding |= slip and self.config.reward_version >= 3
            peak_force = max(peak_force, float(forces.max()))
            if touchdown.any():
                peak_landing = max(peak_landing, float(landing[touchdown].max()))
            if sliding:
                break
        self.steps += 1
        gravity, angular, linear = self._state()
        forward = -float(linear[0])
        tilt = float(np.arccos(np.clip(-gravity[2], -1, 1)))
        height = float(self.data.xpos[self.base, 2])
        finite = bool(np.isfinite(self.data.qpos).all() and np.isfinite(self.data.qvel).all())
        fallen = bool(not finite or height < self.config.min_height or tilt > np.deg2rad(self.config.max_tilt_degrees))
        # Tracking alone can favor standing; the progress term gives standing
        # strictly less reward than achieving the commanded forward velocity.
        terms = {
            "tracking": self.config.tracking_reward_weight * float(np.exp(-((forward - self.config.target_speed) / 0.03) ** 2)),
            "progress": float(np.clip(forward / self.config.target_speed, -1, 1)),
            "lateral": -2.0 * float(linear[1] ** 2),
            "vertical": -0.5 * float(linear[2] ** 2),
            "tilt": -1.0 * float(gravity[0] ** 2 + gravity[1] ** 2),
            "rotation": -0.05 * float(angular @ angular),
            "effort": -0.002 * float(np.mean(self.data.actuator_force ** 2)),
            "smoothness": -0.02 * float(np.mean((action - self.last_action) ** 2)),
            "fall": -5.0 if fallen else 0.0,
        }
        if self.config.reward_version >= 2:
            stale = np.clip((self.data.time - self.cycles.last_step) / self.config.leg_use_window, 0, 1)
            terms.update({"stomp": -2 * impact - .1 * force_cost,
                          "foot_slip": -2 * slip_cost,
                          "useful_steps": .2 * useful_steps,
                          "all_four_legs": .8 * four_cycles,
                          "unused_legs": -.1 * float(stale.mean()) if self.data.time > 4 else 0.})
        if self.config.reward_version >= 3:
            terms.update({"foot_lift": .25 * foot_lifts,
                          "slide_reset": -5.0 if sliding else 0.})
            if sliding:
                terms["tracking"] = terms["progress"] = 0.
        if self.config.reward_version >= 4:
            terms.update({"foot_slip": slip_penalty(slip_cost),
                          "foot_lift": .75 * foot_lifts,
                          "scheduled_lift": .25 * scheduled_lifts,
                          "gait_contacts": .2 * pattern_score,
                          "gait_clearance": .8 * clearance_score})
        if self.config.reward_version >= 5:
            terms["residual_size"] = -.05 * float(np.mean(action ** 2))
        self.last_action = action.copy()
        obs = self._obs()
        reward = sum(terms.values()) if finite else -5.0
        info = {"forward_speed": forward, "height": height, "tilt_degrees": np.rad2deg(tilt),
                "forward_distance": self.start_x - float(self.data.xpos[self.base, 0]),
                "fallen": fallen, "peak_foot_force_n": peak_force,
                "peak_landing_speed_m_s": peak_landing, "foot_slip_m2_s2": slip_cost,
                "useful_steps": useful_steps, "four_leg_cycles": four_cycles,
                "sliding": sliding, "stance_drift_m": max_drift, "foot_lifts": foot_lifts,
                "gait_contact_match": pattern_score, "gait_clearance_match": clearance_score,
                "termination_reason": "sliding" if sliding else "fall" if fallen else "",
                **{f"steps/{leg}": int(self.cycles.counts[i]) for i, leg in enumerate(LEGS)},
                **{f"reward/{k}": v for k, v in terms.items()}}
        if not np.isfinite(obs).all():
            obs = np.nan_to_num(obs, nan=0, posinf=0, neginf=0)
        if self.render_mode == "human":
            self.render()
        return obs, float(reward), bool(fallen or sliding), self.data.time >= self.config.episode_seconds, info

    def render(self):
        if self.viewer is None:
            import mujoco.viewer
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        if self.viewer.is_running():
            self.viewer.sync()

    def close(self):
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

    def manifest(self):
        return {"task": asdict(self.config), "joint_order": self.names,
                "joint_limits_radians": self.limits.tolist(), "neutral_radians": self.neutral.tolist(),
                "xml_sha256": hashlib.sha256(self.model_path.read_bytes()).hexdigest(),
                "observation_size": self.obs_size, "action_size": 12,
                "forward_axis": "negative local X", "observation_note":
                "Body linear velocity is simulator state; deployment requires an estimator."}
