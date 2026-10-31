# HPC storage cleanup

This tool removes redundant artifact files from `~/robot-dog-newton/runs`.
It does not delete anything from GitHub, W&B, or this PC.

Recent W&B runs j6ett8qi, sakq2z9n, mgwk5xso, mmtw7dxi, d08cd5td,
jwmozh4a, and qfwutfdb were confirmed finished with committed model/source
artifacts on October 28, 2026. GitHub has four curated policy snapshots,
not every run. The tool rechecks W&B during cleanup, since artifacts can
subsequently be deleted.

Upload `hpc_cleanup_archived.py` to your HPC home directory. Stop training
first. Use the already working CUDA environment; no installation is needed:

```bash
cd ~/robot-dog-newton
.venv-cuda/bin/python ~/hpc_cleanup_archived.py
```

The default prints the verified reclaimable space. To remove those copies:

```bash
.venv-cuda/bin/python ~/hpc_cleanup_archived.py --apply
df -h ~ /scratch
```

The tool matches each local file's path, size, and content digest against
committed, uploaded W&B artifacts from that same completed run. Missing,
deleted, referenced-only, or mismatched artifacts are kept. A currently
running run is skipped. It refuses to clean while a recognized training
or W&B CLI process is active. Symlinks and paths outside the run are excluded.

It keeps the newest dated run, project input `checkpoint` and `source`
directories, Python environments, W&B logs/offline runs, original CAD,
and files that fail verification. It handles dated run directories such as
`runs/cuda-tracking/20261026-182428-qfwutfdb`; older unrecognized layouts
remain for manual review. Each invocation saves a `cleanup-*.json` audit.
Partial removal can leave a local run incomplete; use its W&B artifacts to
restore the matching policy/normalization/source pair when needed.

Python environments and caches may use much more space than model weights.
Measure these separately; this tool deliberately leaves them intact:

```bash
df -h ~ /scratch
du -sh ~/robot-dog-newton/runs ~/robot-dog-newton/wandb ~/.cache/pip ~/.apptainer/cache 2>/dev/null
```

Pip's download cache and Apptainer's cache can be cleared through their own
commands if no installation/image build is running. Do not delete the
working `.venv-cuda` or containers you still need to launch training.
