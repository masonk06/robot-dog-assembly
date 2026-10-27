# Batched Newton physics

NewtonBatchVecEnv replicates the robot into independent worlds, advances all
worlds together with one SolverMuJoCo CUDA solver, and presents a Stable
Baselines3 VecEnv interface. Each simulation tick transfers state/contact data
as a batch. Each world retains the original observation, reward and controller
logic. No subprocess or per-world solver is used during training. Independent
resets retain live state in other worlds, and terminal observations are recorded
before resetting. VecNormalize and the original PPO checkpoint are restored.

This implements GPU physics batching, not an entirely GPU-resident RL pipeline.
Reference IK, observations/rewards, normalization and PPO inference/learning
still use CPU. The CPU task loops and transfers limit scaling; do not assume
H100 utilization or speedup over the existing six-worker CPU MuJoCo trainer.
The four-world local warm benchmark measured about 43 aggregate steps/s versus
about 9 in the single-world training adapter, but those are short measurements.

The shared task generator lets the batch driver advance physics for all worlds
at a common yield point without duplicating reward/controller code. Single-world
MuJoCo/Newton continue using the same sequence through the normal step method.

Validation covers single-world parity, GPU contact force parity, independent
actions, selective resets, terminal observations and finite rollout output.
The HPC launcher benchmarks 16 worlds before starting 32768 additional steps.
Use this initial comparison before increasing batch count or training duration.
Saved eval metrics use a separate single-world Newton environment with the
same task/controller/contact source; baseline/ metrics remain CPU MuJoCo.
No new trained walking improvement is claimed by a pipeline smoke test.

Upload the training ZIP into the existing robot-dog-newton directory and run:

    bash hpc_newton_batch.sh

Keep the selected checkpoint/ directory intact. New checkpoints are written
under runs/newton-batch and are uploaded to W&B with source artifacts.
