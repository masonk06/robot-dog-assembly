# P2S IK diagnostic workflow

Use the IK generator to inspect the new chassis before RL policy transfer. It
creates model-angle data only; it cannot open a serial port or move Luca.

```powershell
python simulation\p2s_crawl\generate_ik_diagnostic.py `
  --output runs\ik-diagnostic\p2s-crawl.csv
```

View exactly that exported trajectory in the P2S model:

```powershell
python simulation\p2s_crawl\view_ik_diagnostic.py runs\ik-diagnostic\p2s-crawl.csv
```

Review the CSV in MuJoCo after the current P2S joint map is finalized. The
default is deliberately small: 8 mm foot stroke, 5 mm lift, one swing leg at a
time, and all non-swing joints at simulated zero.

## Gate before physical replay

Before converting model angles to ticks, record for all twelve joints:

1. physical servo ID;
2. tick position at the matched simulation-zero pose;
3. tick change for a small manually moved positive model angle;
4. reviewed non-wrapping travel bounds with a clearance margin.

Then the offline converter `hardware/prepare_supported_gait.py` can make a
tick CSV. Do not use the old P2S predecessor maps with a new chassis without
re-verifying them. A physical replay remains a supported test, not a walking
test.
