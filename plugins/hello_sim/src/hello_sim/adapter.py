from __future__ import annotations

from typing import Any

from cradle.contracts.simulation_adapter import SimulationResult


class HelloSimulationAdapter:
    """Trivial reference implementation of `cradle.contracts.SimulationAdapter`.

    Integrates dx/dt = -k*x by explicit Euler with no external solver
    dependency. It exists only to prove the adapter/conformance mechanism
    works end to end, per Roadmap Phase 0. Phase 2 replaces this with real
    engines (Tellurium/libRoadRunner, COPASI) behind the identical `run()`
    boundary.
    """

    name = "hello-sim"

    def run(self, model: dict[str, Any], config: dict[str, Any]) -> SimulationResult:
        k = model["k"]
        x = model["x0"]
        t_end = config["t_end"]
        steps = config["steps"]
        dt = t_end / steps

        ts = [0.0]
        xs = [x]
        for _ in range(steps):
            x = x + dt * (-k * x)
            ts.append(ts[-1] + dt)
            xs.append(x)

        return {"t": ts, "trajectories": {"x": xs}, "engine": self.name}
