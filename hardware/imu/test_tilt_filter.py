import numpy as np
import pytest
from tilt_filter import TiltFilter


def test_stationary_gravity_and_gyro_rotation():
    f = TiltFilter(correction_seconds=1e9)
    roll, pitch, gravity = f.update([0, 0, 9.80665], [0, 0, 0], .1)
    assert roll == pytest.approx(0)
    assert pitch == pytest.approx(0)
    assert gravity == pytest.approx([0, 0, -1])
    roll, pitch, gravity = f.update([0, 0, 9.80665], [0, 1, 0], .1)
    assert pitch > 0
    assert np.linalg.norm(gravity) == pytest.approx(1)


def test_rejects_stale_interval():
    with pytest.raises(ValueError): TiltFilter().update([0, 0, 9.8], [0, 0, 0], 1.0)
