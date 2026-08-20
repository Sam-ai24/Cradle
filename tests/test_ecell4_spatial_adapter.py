from __future__ import annotations

import math

import pytest

from cradle.registry import discover
from cradle.spatial import SpatialManifest, SpatialSpecies, write_manifest

pytest.importorskip("ecell4_base")

DIFFUSION_COEFFICIENT = 1.0


def _adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "ecell4-spatiocyte":
            return plugin.instance
    pytest.skip("'ecell4-spatiocyte' simulation adapter is not installed")


@pytest.fixture()
def manifest_path(tmp_path):
    manifest = SpatialManifest(
        domain_edge_lengths=(6.0, 2.0, 2.0),
        source_center=(3.0, 1.0, 1.0),
        source_radius=0.5,
        species=[
            SpatialSpecies(
                name="M",
                diffusion_coefficient=DIFFUSION_COEFFICIENT,
                radius=0.01,
                initial_count=500,
            )
        ],
        step_duration=0.1,
        n_steps=4,
    )
    path = str(tmp_path / "manifest.json")
    write_manifest(manifest, path)
    return path


def test_point_source_diffusion_matches_the_analytical_sqrt_t_scaling_law(manifest_path):
    """A real physics claim, not a shape check: for free diffusion from a
    point source, the standard deviation of particle position along any
    one axis grows as sqrt(2*D*t) — the exact solution of the diffusion
    equation, not a qualitative approximation. Checked at every reported
    time point, not just the last one.
    """
    result = _adapter().run({"manifest_path": manifest_path}, {})

    times = result["t"]
    std_x = result["trajectories"]["M_std_x"]
    n_particles = result["trajectories"]["M_n_particles"]

    assert len(times) == len(std_x) == 5  # initial + 4 steps

    # No molecules should be created or destroyed - this manifest has no
    # reactions, only diffusion.
    assert all(n == n_particles[0] for n in n_particles)

    for t, observed_std in zip(times[1:], std_x[1:]):  # skip t=0 (near-zero by construction)
        predicted_std = math.sqrt(2 * DIFFUSION_COEFFICIENT * t)
        assert observed_std == pytest.approx(predicted_std, rel=0.25), (
            f"at t={t}, observed std_x={observed_std:.3f} deviates too far from the "
            f"analytical prediction {predicted_std:.3f} for free diffusion"
        )
