import numpy as np
import mujoco
from stable_baselines3.common.env_checker import check_env
from env import DogWalkEnv, WalkConfig, FootCycles, SlidingMonitor, gait_pattern, slip_penalty


def test_interface_limits_and_reproducibility():
    env = DogWalkEnv()
    check_env(env, warn=True)
    a, _ = env.reset(seed=9)
    b, _ = env.reset(seed=9)
    np.testing.assert_array_equal(a, b)
    for _ in range(30):
        obs, reward, done, truncated, _ = env.step(np.ones(12))
        assert np.isfinite(obs).all() and np.isfinite(reward)
        assert np.all(env.targets <= env.limits[:, 1])
        assert np.all(env.targets >= env.limits[:, 0])
        if done or truncated:
            env.reset(seed=9)
    env.close()


def test_timeout_and_fall_are_distinct():
    env = DogWalkEnv(WalkConfig(episode_seconds=.02, reset_noise=0))
    env.reset(seed=1)
    _, _, terminated, truncated, _ = env.step(np.zeros(12))
    assert truncated and not terminated
    env.reset(seed=1)
    env.data.qpos[2] = .02
    _, _, terminated, _, _ = env.step(np.zeros(12))
    assert terminated
    env.close()


def test_all_four_legs_requires_real_steps_from_each_leg():
    tracker = FootCycles(WalkConfig())
    positions = np.zeros((4, 3))
    contacts = np.ones(4, dtype=bool)
    assert tracker.update(contacts, positions, 0., .02, True) == (0, False)
    now = 0.
    for leg in range(4):
        contacts[leg] = False
        for frame in range(10):
            now += .02
            positions[leg, 2] = .001 * frame
            assert tracker.update(contacts, positions, now, .02, True) == (0, False)
        positions[leg, 0] += .01
        positions[leg, 2] = 0
        contacts[leg] = True
        now += .02
        count, cycle = tracker.update(contacts, positions, now, .02, True)
        assert count == 1 and cycle == (leg == 3)
    np.testing.assert_array_equal(tracker.counts, np.ones(4))
    assert tracker.update(contacts, positions, now + .02, .02, True) == (0, False)


def test_tracking_weight_changes_only_tracking_reward():
    from dataclasses import replace
    cfg = WalkConfig()
    original = DogWalkEnv(cfg)
    weighted = DogWalkEnv(replace(cfg, tracking_reward_weight=1.25))
    try:
        original.reset(seed=19)
        weighted.reset(seed=19)
        o1,r1,_,_,i1 = original.step(np.zeros(12))
        o2,r2,_,_,i2 = weighted.step(np.zeros(12))
        np.testing.assert_array_equal(o1,o2)
        np.testing.assert_allclose(i2['reward/tracking'],1.25*i1['reward/tracking'])
        np.testing.assert_allclose(r2-r1,.25*i1['reward/tracking'])
        for key in i1:
            if key.startswith('reward/') and key != 'reward/tracking':
                assert i1[key] == i2[key]
    finally:
        original.close(); weighted.close()


def test_residual_filter_limits_changes_and_resets():
    env = DogWalkEnv(WalkConfig(reward_version=7))
    try:
        env.reset(seed=1)
        env.step(np.ones(12))
        expected = 1 - np.exp(-env.config.control_dt / env.config.residual_time_constant)
        np.testing.assert_allclose(env.filtered_action, expected)
        assert env.config.action_scale * expected < .006
        env.reset(seed=1)
        np.testing.assert_array_equal(env.filtered_action, np.zeros(12))
    finally:
        env.close()


def test_step_progress_uses_air_phase_not_touchdown_speed():
    for distance, expected in ((.003, 1), (0., 0), (-.003, 0)):
        tracker = FootCycles(WalkConfig(reward_version=6))
        positions = np.zeros((4, 3))
        contacts = np.ones(4, bool)
        tracker.update(contacts, positions, 0., .02, False, 0.)
        contacts[0] = False
        for frame in range(10):
            positions[0] = (.001 * frame, 0., .001 * frame)
            tracker.update(contacts, positions, (frame+1)*.02, .02, False,
                           distance * frame / 9)
        contacts[0] = True
        positions[0, 2] = 0.
        count, _ = tracker.update(contacts, positions, .22, .02, False, distance)
        assert count == expected


def test_stationary_taps_and_initial_hover_have_no_step_credit():
    for supported, moving, travel in ((False, True, .01), (True, False, .01), (True, True, 0.)):
        tracker = FootCycles(WalkConfig())
        tracker.supported[:] = supported
        positions = np.zeros((4, 3))
        for i in range(10):
            positions[:, 2] = .01
            tracker.update(np.zeros(4, bool), positions, i * .02, .02, moving)
        positions[:, 2] = 0
        positions[:, 0] = travel
        assert tracker.update(np.ones(4, bool), positions, .22, .02, moving) == (0, False)


def test_slide_reset_requires_sustained_planted_slip():
    monitor = SlidingMonitor(WalkConfig(reward_version=3))
    contacts, positions, velocities = np.ones(4, bool), np.zeros((4, 3)), np.zeros((4, 3))
    for i in range(40):
        # Tiny oscillation is below the displacement tolerance.
        positions[:, 0] = .0002 * (-1) ** i
        assert not monitor.update(contacts, positions, velocities, i * .02, .02)[0]
    positions[0, 0] = .006
    assert not monitor.update(contacts, positions, velocities, .82, .02)[0]
    for i in range(5):
        slip, _ = monitor.update(contacts, positions, velocities, .84 + i * .02, .02)
    assert slip
    # Airborne motion is never a planted-foot slip.
    monitor = SlidingMonitor(WalkConfig())
    for i in range(30):
        positions[:, 0] += .01
        assert not monitor.update(np.zeros(4, bool), positions, np.ones((4, 3)), i * .02, .02)[0]


def test_foot_lift_paid_once_and_hover_does_not_repeat():
    tracker = FootCycles(WalkConfig())
    positions = np.zeros((4, 3))
    contacts = np.ones(4, bool)
    tracker.update(contacts, positions, 0., .02, False)
    contacts[0] = False
    paid = 0
    for i in range(40):
        positions[0] = (min(.01, i * .001), 0, min(.015, i * .001))
        tracker.update(contacts, positions, (i + 1) * .02, .02, False)
        paid += tracker.new_lifts
    assert paid == 1 and not tracker.credits.any()


def test_walk_rhythm_uses_each_leg_and_never_requests_two_swings():
    expected = [2, 0, 3, 1]
    for quarter, leg in enumerate(expected):
        swing, lift = gait_pattern(quarter * .25 + .1)
        assert swing.sum() == 1 and swing[leg]
        assert lift[leg] > .99
    for phase in np.linspace(0, 1, 401):
        assert gait_pattern(phase)[0].sum() <= 1


def test_slip_cost_is_strong_and_monotonic_and_minor_slip_does_not_reset():
    assert slip_penalty(0) == 0
    assert slip_penalty(.001) < slip_penalty(.0001) < 0
    assert slip_penalty(.001) < -2  # Comparable to the maximum tracking+progress reward.
    monitor = SlidingMonitor(WalkConfig())
    pos, vel, contacts = np.zeros((4, 3)), np.zeros((4, 3)), np.ones(4, bool)
    for i in range(40):
        pos[0, 0] = min(i * .0002, .006)
        vel[0, 0] = .01
        assert not monitor.update(contacts, pos, vel, i * .02, .02)[0]
    # Severe sustained drift still terminates; one brief excursion does not.
    pos[0, 0] = .04
    assert not monitor.update(contacts, pos, vel, .82, .02)[0]
    for i in range(30):
        slipping, _ = monitor.update(contacts, pos, vel, .84 + i * .02, .02)
    assert slipping


def test_rhythm_observation_and_backward_compatibility():
    old = DogWalkEnv(WalkConfig(reward_version=3))
    new = DogWalkEnv(WalkConfig(reward_version=4))
    a, _ = old.reset(seed=1)
    b, _ = new.reset(seed=1)
    assert a.shape == (46,) and b.shape == (48,)
    assert np.isclose(np.linalg.norm(b[-2:]), 1)
    old.close()
    new.close()


def test_residual_reference_uses_real_per_leg_geometry():
    cfg = WalkConfig(reference_sway=0, reference_weight_shift=0, reset_noise=0)
    env = DogWalkEnv(cfg)
    obs, _ = env.reset(seed=1)
    assert obs.shape == (60,)
    neutral_positions = env.data.site_xpos[env.feet].copy()
    env.data.time = 2.
    env.phase_offset = .1 - env.data.time / cfg.gait_cycle_seconds
    reference = env.reference()
    env.data.qpos[env.qadr] = reference
    mujoco.mj_forward(env.model, env.data)
    dz = env.data.site_xpos[env.feet, 2] - neutral_positions[:, 2]
    np.testing.assert_allclose(dz, [0, 0, cfg.reference_lift * cfg.reference_rear_lift_multiplier, 0], atol=1e-7)
    env.reset(seed=1)
    env.step(np.zeros(12))
    expected = env.reference()  # reference advances by one control interval
    assert np.isfinite(expected).all()
    assert np.all(reference >= env.limits[:, 0]) and np.all(reference <= env.limits[:, 1])
    env.close()
