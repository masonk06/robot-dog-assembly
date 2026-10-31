# Software contact-estimation prototype

The saved PPO policy has a fixed 60-value observation contract. It consumes:

1. local gravity (3), angular velocity (3), and linear velocity (3);
2. commanded forward speed (1);
3. joint position offsets (12), joint velocity (12), and previous action (12);
4. gait phase sine/cosine (2) and the 12-joint reference pose (12).

It does **not** consume foot-contact measurements. MuJoCo/Newton contact forces
are used for rewards and resets, but are not policy inputs. Adding four contact
bits would change the policy input shape and therefore requires training a new
policy plus a compatible observation normalizer.

`estimate_contact_from_telemetry.py` is deliberately outside the policy. It
combines the scheduled gait phase with current STS3215 position error and motor
load. Its output is a low-confidence contact *candidate*, suitable for logging
and evaluating whether hardware foot sensors are needed. It must not be used as
the only safety gate or as an unvalidated automatic gait controller.

For now, priorities are IMU orientation/gyro integration, joint-state feedback,
bounded target dispatch, watchdog/release behavior, and short supported tests.
Future foot sensors can be added on spare ADC pins without changing the current
policy; a new policy would be trained only if they prove necessary.
