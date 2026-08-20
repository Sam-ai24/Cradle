"""Runs in its own OS process, never imported into cradle-core or any
other plugin's process (Architecture, Layer 8: E-Cell4 is GPL-3.0 and
stays process/container-isolated, per NOTICE.md — same pattern as
cobrapy_fba.worker). Invoked as `python -m ecell4_spatial.worker
<manifest_path>`; prints one JSON object to stdout.

Placement note: `add_molecules(species, count, Sphere(center, radius))`
does rejection-sampling to find `count` distinct empty voxels inside the
sphere. If `radius` is too small relative to `count` and the world's
voxel size, this is pathologically slow (confirmed directly: a radius of
0.3 with 300-1000 molecules never completed placement within 40+ seconds,
while the same molecule count at radius 0.5 placed near-instantly) — the
manifest's `source_radius` has to leave real headroom, not just be
"small enough to look like a point source."
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    manifest_path = sys.argv[1]

    from ecell4_base.core import NetworkModel, Real3, Species, Sphere
    from ecell4_base.spatiocyte import SpatiocyteSimulator, SpatiocyteWorld

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    model = NetworkModel()
    species_objects = {}
    for spec in manifest["species"]:
        species = Species(spec["name"])
        species.set_attribute("D", spec["diffusion_coefficient"])
        species.set_attribute("radius", spec["radius"])
        model.add_species_attribute(species)
        species_objects[spec["name"]] = species

    world = SpatiocyteWorld(Real3(*manifest["domain_edge_lengths"]))
    world.bind_to(model)

    source_center = Real3(*manifest["source_center"])
    source_shape = Sphere(source_center, manifest["source_radius"])
    for spec in manifest["species"]:
        placed = world.add_molecules(
            species_objects[spec["name"]], spec["initial_count"], source_shape
        )
        if not placed:
            raise RuntimeError(
                f"failed to place all {spec['initial_count']} '{spec['name']}' molecules "
                f"in source_radius={manifest['source_radius']} — likely too small for that count"
            )

    simulator = SpatiocyteSimulator(world, model)
    step_duration = manifest["step_duration"]
    n_steps = manifest["n_steps"]

    times = [0.0]
    per_species_stats = {spec["name"]: {"std_x": [], "std_y": [], "std_z": [], "n_particles": []} for spec in manifest["species"]}

    def record() -> None:
        for spec in manifest["species"]:
            particles = world.list_particles_exact(species_objects[spec["name"]])
            xs = [p[1].position()[0] - source_center[0] for p in particles]
            ys = [p[1].position()[1] - source_center[1] for p in particles]
            zs = [p[1].position()[2] - source_center[2] for p in particles]
            stats = per_species_stats[spec["name"]]
            stats["std_x"].append(_std(xs))
            stats["std_y"].append(_std(ys))
            stats["std_z"].append(_std(zs))
            stats["n_particles"].append(len(particles))

    record()
    for _ in range(n_steps):
        simulator.run(step_duration)
        times.append(world.t())
        record()

    print(json.dumps({"times": times, "species": per_species_stats}))
    return 0


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


if __name__ == "__main__":
    sys.exit(main())
