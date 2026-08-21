"""Real device auto-detection, shared by the adapter and the training
script — this plugin was built on a CPU-only Windows machine but is
meant to also run on real GPU/Apple Silicon hardware (e.g. a Mac Mini's
`mps` backend), which is materially faster for GEARS' GNN training.
Picks the best available real backend rather than hardcoding one.
"""

from __future__ import annotations

import torch


def resolve_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
