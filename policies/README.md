# Selected PPO policies

Only two checkpoints are kept in the active repository. Each folder includes
the Stable-Baselines3 policy, observation normalization state and evaluation
metadata needed to reproduce its corresponding simulation playback.

| Folder | Role |
| --- | --- |
| `tracking-baseline/` | Early conservative policy used as a stable reference. |
| `latest-long-run/` | Latest retained long-run simulation checkpoint. |

These policies are residual controllers around a programmed gait and were
trained with a fixed observation contract. Do not add IMU/contact inputs to a
checkpoint at runtime—changing input dimensions requires training or adapting
a new policy.

Use them only in simulation or supported diagnostic replay after checking the
calibration and safety documentation in `hardware/`.
