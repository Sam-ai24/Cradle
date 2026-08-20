from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import h5py
import numpy as np

#: Cradle's own MD-tier contract (Architecture, Layer 4): no
#: BioSimulators-equivalent registry exists for molecular dynamics, so
#: this manifest — not SED-ML/COMBINE — is the swap boundary. Any engine
#: adapter that can build a system from this manifest and step an
#: integrator satisfies the contract; H5MD is the standardized output.


@dataclass
class ParticleSpec:
    mass_amu: float
    position_nm: tuple[float, float, float]


@dataclass
class BondSpec:
    particle_i: int
    particle_j: int
    length_nm: float
    force_constant_kj_per_nm2: float


@dataclass
class NonbondedSpec:
    """Uniform Lennard-Jones parameters applied to every particle — the
    simplest possible coarse-grained nonbonded model, deliberately not a
    full MARTINI parameterization. Real MARTINI force-field support is a
    documented future increment (Architecture: "prioritize coarse-grained
    over raw atomistic MD"), not something this manifest pretends to be.
    """

    sigma_nm: float
    epsilon_kj_per_mol: float


@dataclass
class IntegratorSpec:
    kind: str  # "langevin_middle" is the only one implemented so far
    temperature_k: float
    friction_per_ps: float
    timestep_ps: float


@dataclass
class MDManifest:
    particles: list[ParticleSpec]
    bonds: list[BondSpec]
    nonbonded: NonbondedSpec
    integrator: IntegratorSpec
    n_steps: int
    report_interval: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "MDManifest":
        return MDManifest(
            particles=[ParticleSpec(**p) for p in data["particles"]],
            bonds=[BondSpec(**b) for b in data["bonds"]],
            nonbonded=NonbondedSpec(**data["nonbonded"]),
            integrator=IntegratorSpec(**data["integrator"]),
            n_steps=data["n_steps"],
            report_interval=data["report_interval"],
        )


def write_manifest(manifest: MDManifest, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_manifest(path: str | Path) -> MDManifest:
    return MDManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def write_h5md_trajectory(
    path: str | Path,
    steps: list[int],
    times_ps: list[float],
    positions_nm: np.ndarray,  # shape (n_frames, n_particles, 3)
    creator_name: str = "Cradle MD adapter",
    creator_version: str = "0.0.0",
) -> Path:
    """Write a trajectory following the core H5MD structure (h5md.nongnu.org):
    the `/h5md` metadata group (version, author, creator) and
    `/particles/toy_system/{box,position}` as a time-dependent element with
    matching step/time/value datasets. Implements only what this adapter
    actually produces — positions for one non-periodic particle group —
    not the full H5MD spec (no species/mass-as-element/multiple particle
    groups/periodic box edges). That's an honest scope limit, not a claim
    of full compliance.
    """
    path = Path(path)
    with h5py.File(path, "w") as f:
        h5md_group = f.create_group("h5md")
        h5md_group.attrs["version"] = [1, 1]
        h5md_group.create_group("author").attrs["name"] = "Cradle"
        creator = h5md_group.create_group("creator")
        creator.attrs["name"] = creator_name
        creator.attrs["version"] = creator_version

        particles = f.create_group("particles").create_group("toy_system")
        box = particles.create_group("box")
        box.attrs["dimension"] = 3
        box.attrs["boundary"] = ["none", "none", "none"]

        position = particles.create_group("position")
        position.create_dataset("step", data=np.asarray(steps, dtype=np.int64))
        position.create_dataset("time", data=np.asarray(times_ps, dtype=np.float64))
        position.create_dataset("value", data=np.asarray(positions_nm, dtype=np.float64))

    return path


def read_h5md_positions(path: str | Path) -> dict[str, Any]:
    with h5py.File(path, "r") as f:
        position = f["particles"]["toy_system"]["position"]
        return {
            "step": position["step"][:].tolist(),
            "time": position["time"][:].tolist(),
            "value": position["value"][:].tolist(),
        }
