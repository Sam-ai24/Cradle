"""Real, disclosed compatibility patches for `cell-gears` 0.1.2 — not
part of upstream GEARS. Applied idempotently (safe to call every import,
on any machine) rather than as a one-off manual edit, so this plugin
works the same way on a fresh install anywhere (this was originally
found and fixed by hand-editing this session's own installed copy; this
module makes that reproducible instead of undocumented).

Two real, confirmed version-incompatibility bugs, neither related to
Cradle's own code:

1. `GEARS.__init__` computes `self.adata.X[self.adata.obs.condition ==
   'ctrl']` — scipy's sparse `__getitem__` now requires a numpy bool
   array for row indexing, not a pandas Series, and raises
   `AttributeError: 'Series' object has no attribute 'nonzero'` under
   the scipy/pandas versions installed here.
2. `uncertainty_loss_fct` (used whenever `uncertainty=True`, which this
   adapter needs for the perturbation contract's uncertainty output)
   accumulates into `losses = torch.tensor(0.0, requires_grad=True)`
   via in-place `losses += ...` — current PyTorch's autograd no longer
   allows in-place mutation of a leaf tensor that requires grad, and
   raises `RuntimeError: a leaf Variable that requires grad is being
   used in an in-place operation`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_GEARS_PY_PATCHES = [
    (
        "self.adata.X[self.adata.obs.condition == 'ctrl']",
        "self.adata.X[(self.adata.obs.condition == 'ctrl').to_numpy()]",
    ),
]

_UTILS_PY_PATCHES = [
    (
        "torch.tensor(0.0, requires_grad=True).to(pred.device)",
        "torch.tensor(0.0).to(pred.device)",
    ),
    (
        "losses += torch.sum(",
        "losses = losses + torch.sum(",
    ),
]


def _apply_patches(path: Path, patches: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in patches:
        if old in text:
            text = text.replace(old, new)
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")


def patch_gears() -> None:
    """Idempotent: does nothing if a patch's target text is already
    gone (either already patched by a previous call, or upstream fixed
    it themselves in a future release).

    MUST be called before anything in this process does
    `import gears`/`from gears import ...` — `importlib.util.find_spec`
    locates the package's on-disk location without executing it (unlike
    a real import, which would already have loaded the buggy function
    bodies into memory, where rewriting the file on disk afterward has
    no effect for the rest of this process).
    """
    spec = importlib.util.find_spec("gears")
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError("'gears' (cell-gears) is not installed")
    gears_dir = Path(spec.origin).resolve().parent
    _apply_patches(gears_dir / "gears.py", _GEARS_PY_PATCHES)
    _apply_patches(gears_dir / "utils.py", _UTILS_PY_PATCHES)
