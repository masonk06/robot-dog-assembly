# Preserved policy checkpoints

Useful milestones are backed up with normalization and evaluation reports,
independently of W&B retention. sources/RUN.zip holds the exact training source;
catalog.json records provenance and checksums.

| Folder | Steps | Role |
| --- | ---: | --- |
| original-v7 | 8192 | First gait approved by the user |
| tracking-baseline | 448352 | Approved tracking-weight 1.25 continuation |
| best-distance | 9516896 | Highest recorded distance, about 16.02 cm / 20 s |
| latest-long-run | 16570208 | Latest saved, about 15.75 cm / 20 s |

These are residual controllers around a programmed gait. Results describe the
saved simulated trials, not full-body hardware validation.

In a Newton-capable environment, from the repository root:

```bash
python simulation/rl/play.py policies/best-distance --source simulation/mujoco
```

The checked-in MJCF matches the saved models after normalizing line endings.
The catalog records both raw historical and LF-normalized checksums; source
archives preserve the exact historical bytes. The current compatible
implementation preserves the observation contract; extract the matching source
archive for exact historical software. Only load trusted policy/normalization
files, which contain serialized Python objects. Continue with train_cuda.py
--resume and an explicit --source; new runs save separately.
