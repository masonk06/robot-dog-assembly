from copy import deepcopy
from overnight_cuda import quality, eligible_to_advance, goal_reached


def report(speed=.02):
    return {'episodes': 2, 'gait_cycle_seconds': 3.,
            'eval/net_speed_m_s': speed, 'eval/foot_slip_m2_s2': .00016,
            'eval/peak_foot_force_n': 15., 'eval/peak_landing_speed_m_s': .15,
            'per_episode': [dict(seconds=60., fallen=0, sliding=0, slip_cost=.00016,
                                 peak_force_n=15., peak_landing_m_s=.15, net_speed_m_s=speed,
                                 steps=dict(fl=19, fr=19, rl=19, rr=19)) for _ in range(2)]}


def test_individual_failure_cannot_be_hidden_by_average():
    baseline = report()
    for field, value in [('fallen', 1), ('seconds', 20), ('sliding', 1),
                         ('slip_cost', .001), ('peak_force_n', 30),
                         ('peak_landing_m_s', .3), ('net_speed_m_s', float('nan'))]:
        r = deepcopy(baseline)
        r['per_episode'][1][field] = value
        assert quality(r, baseline)
    r = deepcopy(baseline)
    r['per_episode'][1]['steps']['rl'] = 0
    assert quality(r, baseline)


def test_promotions_and_goal_need_every_trial():
    r = report(.019)
    assert not quality(r, r)
    assert eligible_to_advance(r, .02)
    assert not goal_reached(r, [])
    r['per_episode'][1]['net_speed_m_s'] = .015
    assert not eligible_to_advance(r, .02)
    assert goal_reached(report(.02), [])
    assert not goal_reached(report(.02), ['too much slipping'])
