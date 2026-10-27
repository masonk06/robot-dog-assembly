# CUDA-resident Newton + PPO continuation

The steady-state transition, reference IK, observations, smoothed residuals,
contact-force reduction, foot-cycle credit, slip reset, rewards and per-world
reset run on CUDA. CUDA graphs include the physics solver's conditional loops;
the uncaptured solver otherwise reads loop conditions back to the CPU.
Warp and Torch share one stream for zero-copy state views and graph capture.

Observation/reward running moments (float64), float32 rollouts, GAE, Gaussian
policy inference, gradients and Adam updates are CUDA tensors. KL stopping masks
parameters, moments and Adam step counters on GPU. Python/CPU orchestrates the
loop, installs/imports the model, and handles logging/checkpoint files. Logging
and checkpoint boundaries intentionally synchronize summaries/statistics.

This resumes Stable Baselines3 policy.zip plus normalize.pkl; it does not
initialize a fresh neural network. Model joint/actuator/site layouts fail closed
if they differ. Exports retain SB3 format and can use the existing playback
bridge. Custom CUDA PPO uses the existing network, optimizer state, gamma,
GAE lambda, gradient clipping, entropy coefficient and KL limit. Rollout length
128, 64 worlds and minibatches of 256 are new throughput-oriented batch settings.
Changing training layout may change learning; more speed is not gait quality.

## Local evidence

- Existing CPU environment suite: 12 passed.
- 120-frame shared-action comparison against single-world Newton: maximum
  qpos error 0.0000332, observation error 0.00101, reward error 0.00503,
  contact normal force error 0.00096 N. Floating-point/event thresholds can cause
  differences; no claim of bit-identical trajectories is made.
- Partial reset preserves another world's task state. Steady task graph replay
  passes a gate forbidding Tensor.cpu/numpy/item/tolist and scalar conversions.
- Masked Adam matches torch.optim.Adam on enabled updates and preserves state
  on skipped updates. GPU running-moment merge is checked against its formula.
- Original selected checkpoint: 3 x 20-second CUDA trials, about 0.10245 m
  forward, 6 steps per leg, no falls or slide resets.
- Graph PPO smoke: weights and normalization saved/uploaded, then loaded and
  evaluated for 3 x 20 seconds: about 0.10239 m, 6 steps per leg, no resets/falls.
  This small smoke does not establish learned improvement.
- Local 64-world, 100-control-frame graph simulation benchmark: about 4944
  aggregate environment steps/s. This excludes PPO updates/checkpoint costs and
  is not an H100 speed guarantee. Compare actual train time/fps on HPC.

## HPC setup

Let the currently running HPC job finish. Keep the old .venv and checkpoints.
Unzip the CUDA package into ~/robot-dog-newton, then:

```bash
module load python/3.12
python -m venv .venv-cuda
source .venv-cuda/bin/activate
python -m pip install --no-cache-dir -r requirements-cuda.txt
bash hpc_cuda_train.sh
```

CUDA-enabled Torch is a large download. The separate environment leaves the
CPU trainer intact. This targets CUDA 13.0 and the previously detected H100
driver; installation and the CUDA/parity gates must pass on the allocation.

The launcher defaults to the latest saved checkpoint of run 1f0ethf8 (the
longer training continuation observed during this migration). It refuses to
launch while that run is marked running. Pass another completed run explicitly:

    bash hpc_cuda_train.sh RUN_ID

The artifact downloader preserves originals under cuda-inputs/RUN-VERSION and
records pinned artifact versions in cuda-start.json. It never uploads keys.
The launcher checks numerical parity, evaluates frozen input weights, then runs
65536 additional steps with 64 worlds and checkpoint evaluations every 32768.
The first graph capture/compilation can take time before a progress line appears.

Outputs are under runs/cuda and W&B robot-dog-rl. Keep source.json, the exact
source/model artifact, policy.zip and normalize.pkl together for playback.
Original checkpoints are not overwritten. CUDA graph or contact-capacity
failures stop the experiment instead of silently switching to CPU or dropping
contacts. Evaluate trained checkpoints before extending a run.
