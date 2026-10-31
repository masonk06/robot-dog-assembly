"""Provisional gravity-direction estimator in simulation body coordinates.

Not a complete orientation or position estimate: yaw heading is unobservable.
"""
import math
import numpy as np


class TiltFilter:
    def __init__(self, correction_seconds=1.0):
        self.up = None
        self.correction_seconds = correction_seconds

    def update(self, accel, angular, dt):
        a = np.asarray(accel, dtype=float)
        w = np.asarray(angular, dtype=float)
        if a.shape != (3,) or w.shape != (3,) or not np.isfinite(a).all() or not np.isfinite(w).all():
            raise ValueError('Invalid IMU vector')
        norm = np.linalg.norm(a)
        if not math.isfinite(dt) or dt <= 0 or dt > .5 or norm < 1e-6:
            raise ValueError('Invalid sample interval or acceleration')
        observed_up = a / norm
        if self.up is None:
            self.up = observed_up.copy()
        else:
            # A fixed world vector expressed in rotating body axes changes by -omega cross vector.
            predicted = self.up - np.cross(w, self.up) * dt
            predicted /= np.linalg.norm(predicted)
            # Reduce correction when acceleration magnitude differs from gravity.
            trust = max(0.0, 1.0 - abs(norm - 9.80665) / 2.0)
            alpha = (1.0 - math.exp(-dt / self.correction_seconds)) * trust
            self.up = (1.0-alpha)*predicted + alpha*observed_up
            self.up /= np.linalg.norm(self.up)
        roll = math.degrees(math.atan2(self.up[1], self.up[2]))
        pitch = math.degrees(math.atan2(-self.up[0], math.hypot(self.up[1], self.up[2])))
        return roll, pitch, -self.up.copy()
