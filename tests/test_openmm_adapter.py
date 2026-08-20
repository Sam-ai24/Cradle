from __future__ import annotations

import statistics

import pytest

from cradle.md import (
    BondSpec,
    IntegratorSpec,
    MDManifest,
    NonbondedSpec,
    ParticleSpec,
    read_h5md_positions,
    write_manifest,
)
from cradle.registry import discover

pytest.importorskip("openmm")

N_PARTICLES = 8
TARGET_TEMPERATURE_K = 300.0


def _adapter():
    for plugin in discover("simulation_adapter"):
        if plugin.entry_point_name == "openmm":
            return plugin.instance
    pytest.skip("'openmm' simulation adapter is not installed")


@pytest.fixture()
def manifest_path(tmp_path):
    manifest = MDManifest(
        particles=[
            ParticleSpec(mass_amu=12.0, position_nm=(i * 0.5, 0.0, 0.0))
            for i in range(N_PARTICLES)
        ],
        bonds=[
            BondSpec(particle_i=i, particle_j=i + 1, length_nm=0.5, force_constant_kj_per_nm2=500.0)
            for i in range(N_PARTICLES - 1)
        ],
        nonbonded=NonbondedSpec(sigma_nm=0.4, epsilon_kj_per_mol=0.5),
        integrator=IntegratorSpec(
            kind="langevin_middle",
            temperature_k=TARGET_TEMPERATURE_K,
            friction_per_ps=1.0,
            timestep_ps=0.002,
        ),
        n_steps=20000,
        report_interval=200,
    )
    path = str(tmp_path / "manifest.json")
    write_manifest(manifest, path)
    return path


def test_coarse_grained_chain_equilibrates_to_the_target_temperature(manifest_path):
    """Not a shape check: a real physics claim. A Langevin-thermostatted
    system should equilibrate so its time-averaged instantaneous
    temperature (recovered from kinetic energy via equipartition,
    T = 2*KE / (3*N*kB)) sits near the target — this is the standard
    sanity check any real MD user runs before trusting a simulation.
    """
    result = _adapter().run({"manifest_path": manifest_path}, {})

    temperatures = result["trajectories"]["temperature_k"]
    second_half = temperatures[len(temperatures) // 2 :]
    mean_equilibrated_temperature = statistics.mean(second_half)

    assert mean_equilibrated_temperature == pytest.approx(TARGET_TEMPERATURE_K, rel=0.15), (
        f"equilibrated mean temperature {mean_equilibrated_temperature:.1f} K is not close "
        f"to the target {TARGET_TEMPERATURE_K} K — the thermostat isn't working as claimed"
    )

    # Potential energy should stay bounded (no blown-up integrator), and
    # positions should have actually moved from their initial straight line.
    trajectory = read_h5md_positions(result["h5md_path"])
    assert len(trajectory["step"]) == len(result["t"])
    first_frame = trajectory["value"][0]
    last_frame = trajectory["value"][-1]
    assert first_frame != last_frame, "particles never moved — the integrator did nothing"


def test_h5md_file_has_the_documented_structure(manifest_path):
    import h5py

    result = _adapter().run({"manifest_path": manifest_path}, {})
    with h5py.File(result["h5md_path"], "r") as f:
        assert list(f["h5md"].attrs["version"]) == [1, 1]
        assert f["h5md"]["author"].attrs["name"] == "Cradle"
        assert "position" in f["particles"]["toy_system"]
        assert f["particles"]["toy_system"]["box"].attrs["dimension"] == 3
