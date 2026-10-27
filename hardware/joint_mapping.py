"""Authoritative knee model-angle to encoder-delta directions (no hardware I/O).

ticks = physical_neutral_ticks + sign * model_angle_degrees * 4096 / 360.
The inverse conversion uses the same sign. Front signs were corrected from
the user's live comparison on 2026-10-26; rear signs retain prior calibration.
"""
KNEE_MODEL_TO_SERVO_SIGN = {
    'front_left': -1,
    'front_right': -1,
    'rear_left': -1,
    'rear_right': -1,
}
