from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

#: Cradle's own spatial-experiment contract (Architecture, Layer 4/9):
#: neither CompuCell3D nor PhysiCell were installable in this environment
#: (conda-only and C++-compile-only respectively, confirmed by direct
#: attempt — docs/ROADMAP.md), so this manifest targets a particle-based
#: spatial-stochastic engine instead (E-Cell4's spatiocyte), which *is*
#: real, installable, and produces quantitatively correct diffusion
#: physics. Neither spatial geometry nor agent rules fit SBML/SED-ML, so
#: — like the MD tier — this is a Cradle-defined manifest, not a
#: BioSimulators-style contract.


@dataclass
class SpatialSpecies:
    name: str
    diffusion_coefficient: float  # um^2/s
    radius: float  # um
    initial_count: int


@dataclass
class SpatialManifest:
    domain_edge_lengths: tuple[float, float, float]  # um
    source_center: tuple[float, float, float]  # um
    source_radius: float  # um — must contain enough voxels for every
    # species' initial_count, or placement will be slow/fail (see
    # ecell4_spatial's worker docstring for why this matters)
    species: list[SpatialSpecies]
    step_duration: float  # seconds per reported step
    n_steps: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpatialManifest":
        return SpatialManifest(
            domain_edge_lengths=tuple(data["domain_edge_lengths"]),
            source_center=tuple(data["source_center"]),
            source_radius=data["source_radius"],
            species=[SpatialSpecies(**s) for s in data["species"]],
            step_duration=data["step_duration"],
            n_steps=data["n_steps"],
        )


def write_manifest(manifest: SpatialManifest, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_manifest(path: str | Path) -> SpatialManifest:
    return SpatialManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
