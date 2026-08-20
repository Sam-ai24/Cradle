from __future__ import annotations

import tempfile
from typing import Any

import numpy as np
import openmm
from openmm import unit

from cradle.contracts.simulation_adapter import SimulationResult
from cradle.md import MDManifest, read_manifest, write_h5md_trajectory

#: kB in the same unit system OpenMM reports energy in (kJ/mol/K) — used to
#: recover instantaneous temperature from kinetic energy via equipartition
#: (KE = 3/2 * N * kB * T), the same real-physics check a real MD user
#: would run to confirm a thermostatted simulation is actually equilibrating,
#: not just producing numbers.
_KB_KJ_PER_MOL_K = unit.MOLAR_GAS_CONSTANT_R.value_in_unit(
    unit.kilojoule_per_mole / unit.kelvin
)

_SUPPORTED_INTEGRATORS = {"langevin_middle"}


class UnsupportedIntegratorError(ValueError):
    pass


def _build_system(manifest: MDManifest) -> tuple[openmm.System, openmm.Vec3]:
    system = openmm.System()
    for particle in manifest.particles:
        system.addParticle(particle.mass_amu)

    bonds = openmm.HarmonicBondForce()
    for bond in manifest.bonds:
        bonds.addBond(
            bond.particle_i, bond.particle_j, bond.length_nm, bond.force_constant_kj_per_nm2
        )
    system.addForce(bonds)

    nonbonded = openmm.NonbondedForce()
    nonbonded.setNonbondedMethod(openmm.NonbondedForce.NoCutoff)
    for _ in manifest.particles:
        nonbonded.addParticle(0.0, manifest.nonbonded.sigma_nm, manifest.nonbonded.epsilon_kj_per_mol)
    system.addForce(nonbonded)

    positions = [openmm.Vec3(*p.position_nm) for p in manifest.particles] * unit.nanometer
    return system, positions


def _build_integrator(manifest: MDManifest) -> openmm.Integrator:
    spec = manifest.integrator
    if spec.kind not in _SUPPORTED_INTEGRATORS:
        raise UnsupportedIntegratorError(
            f"integrator kind '{spec.kind}' is not implemented; supported: {_SUPPORTED_INTEGRATORS}"
        )
    return openmm.LangevinMiddleIntegrator(
        spec.temperature_k * unit.kelvin,
        spec.friction_per_ps / unit.picosecond,
        spec.timestep_ps * unit.picoseconds,
    )


class OpenMMSimulationAdapter:
    """Molecular-dynamics/coarse-grained tier (Architecture, Layer 4's
    third execution tier). No BioSimulators-equivalent contract exists for
    MD, so this adapter consumes Cradle's own manifest
    (`cradle.md.MDManifest`) rather than a COMBINE archive, and writes a
    full trajectory to H5MD alongside a scalar-diagnostic `SimulationResult`
    (potential/kinetic energy, instantaneous temperature) — the particle
    positions themselves don't fit the `trajectories: dict[str, list[float]]`
    shape built for scalar species/flux values, so they go to the H5MD file
    referenced in the result instead of being forced into it.
    """

    name = "openmm"
    input_mode = "md_manifest"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        manifest = read_manifest(model["manifest_path"])
        n_particles = len(manifest.particles)

        system, positions = _build_system(manifest)
        integrator = _build_integrator(manifest)

        context = openmm.Context(system, integrator)
        context.setPositions(positions)
        context.setVelocitiesToTemperature(manifest.integrator.temperature_k * unit.kelvin)

        n_reports = manifest.n_steps // manifest.report_interval
        steps, times_ps, all_positions = [], [], []
        potential_energy, kinetic_energy, temperature_k = [], [], []

        current_step = 0
        for report_index in range(n_reports + 1):
            state = context.getState(getPositions=True, getEnergy=True)
            pe = state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
            ke = state.getKineticEnergy().value_in_unit(unit.kilojoule_per_mole)

            steps.append(current_step)
            times_ps.append(current_step * manifest.integrator.timestep_ps)
            all_positions.append(
                [list(v) for v in state.getPositions().value_in_unit(unit.nanometer)]
            )
            potential_energy.append(pe)
            kinetic_energy.append(ke)
            # Equipartition: KE = (3N/2) kB T -> T = 2 KE / (3 N kB)
            temperature_k.append(2 * ke / (3 * n_particles * _KB_KJ_PER_MOL_K))

            if report_index < n_reports:
                integrator.step(manifest.report_interval)
                current_step += manifest.report_interval

        h5md_path = config.get("h5md_output_path") or tempfile.mktemp(suffix=".h5")
        write_h5md_trajectory(h5md_path, steps, times_ps, np.array(all_positions))

        return {
            "t": times_ps,
            "trajectories": {
                "potential_energy_kj_per_mol": potential_energy,
                "kinetic_energy_kj_per_mol": kinetic_energy,
                "temperature_k": temperature_k,
            },
            "engine": self.name,
            "h5md_path": h5md_path,
        }
