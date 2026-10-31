# Stride sweep: frozen learned weights

Continued reference-stride testing using the preserved 24 mm learned policy (mmtw7dxi, step 28,309,344). No new PPO updates or normalization changes. Original three-second cycle and all reward weights retained.

| Stride (mm) | Phase | Net speed (cm/s) | Slip score | Decision |
| ---: | --- | ---: | ---: | --- |
| 25.5 | screen | 1.0149 | 0.00014238 | Passed |
| 26 | screen | 1.0295 | 0.00014305 | Passed |
| 27 | screen | 1.0567 | 0.00014524 | Passed |
| 28 | screen | 1.0886 | 0.00015069 | Passed |
| 29 | screen | 1.1174 | 0.00015503 | Passed |
| 30 | screen | 1.1364 | 0.00016383 | Passed |
| 31 | screen | 1.1579 | 0.00017065 | Passed |
| 32 | screen | 1.1841 | 0.00017816 | foot_slip_m2_s2 exceeds comparison budget |
| 31.5 | refine | 1.1728 | 0.00017365 | Passed |
| 31.5 | validation | 1.1714 | 0.00017369 | Passed |

31.5 mm passed five held-out 60-second trials with every leg taking 19-20 useful steps, no falls or slide resets. Net speed was 1.1714 cm/s, 15.6% above the matched 25.5 mm control, while slip score rose 21.9%.

Speed was still rising at 32 mm. The search stopped because the slip score exceeded the chosen 25% increase budget; this is a quality cutoff, not a demonstrated maximum possible speed or a physical failure threshold. Only flat ground and small reset noise were tested.

[W&B evaluation](https://forge.coreweave.com/wandb/marsdenm-oregon-state-university/robot-dog-rl/runs/sakq2z9n)

Playback from the extracted package, using the existing Newton/CUDA environment:

```bash
python source/play.py best --source source --seconds 300
```

The original 25.5 mm and preceding learned policies remain unchanged. This candidate uses exactly the same policy.zip and normalize.pkl; only the task reference stride changed.
