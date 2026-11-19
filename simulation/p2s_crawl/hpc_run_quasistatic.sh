#!/usr/bin/env bash
# Run from the repository root inside an already allocated GPU job.
# This is simulation-only; it cannot communicate with Luca hardware.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${LUCA_CUDA_VENV:-$HOME/robot-dog-newton/.venv-cuda}"
SLOTS="${P2S_CRAWL_SLOTS:-6}"
SLOT_SECONDS="${P2S_CRAWL_SLOT_SECONDS:-6600}"
ENVS="${P2S_CRAWL_ENVS:-64}"
MODE="${WANDB_MODE:-online}"

if [[ ! -f "$VENV/bin/activate" ]]; then
  echo "CUDA environment not found: $VENV" >&2
  echo "Set LUCA_CUDA_VENV to the existing CUDA-enabled virtual environment." >&2
  exit 1
fi
source "$ROOT/simulation/rl/hpc_storage.sh"
source "$VENV/bin/activate"
cd "$ROOT"

python -c "import torch; assert torch.cuda.is_available(), 'CUDA PyTorch is required'; print(torch.cuda.get_device_name(0))"
SOURCE="$DOG_WORK/p2s-crawl-source"
python simulation/p2s_crawl/prepare_source.py --output "$SOURCE" --replace
python simulation/rl/check_cuda.py --source "$SOURCE" --frames 120

python -u simulation/rl/robust_crawl_curriculum.py \
  --checkpoint policies/tracking-baseline \
  --source "$SOURCE" \
  --output "$DOG_WORK/runs/p2s-quasistatic-crawl" \
  --slots "$SLOTS" \
  --slot-seconds "$SLOT_SECONDS" \
  --envs "$ENVS" \
  --mode "$MODE"
