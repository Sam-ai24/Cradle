// Cradle Phase 10: the scale-router. Loads real, already-validated Cradle
// data (Phase 1-4's repressilator, Phase 3's real AlphaFold structures) and
// links a pathway-scale view, a molecular-scale view, and a comparison
// across every currently-registered combine_archive engine (queried live
// from the same API the Explorer uses, not a fixed pair of pre-baked runs)
// behind one shared time-slider state.

const CHART_PADDING = 24;

async function main() {
  const graph = await fetch("data/repressilator_graph.json").then((r) => r.json());

  const viewer = await molstar.Viewer.create("molstar-app", {
    layoutIsExpanded: false,
    layoutShowControls: false,
    layoutShowSequence: false,
    layoutShowLog: false,
    layoutShowLeftPanel: false,
    viewportShowExpand: false,
    viewportShowSelectionMode: false,
    viewportShowAnimation: false,
  });

  const cy = cytoscape({
    container: document.getElementById("cy"),
    elements: graph.elements,
    style: [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "text-valign": "center",
          "text-halign": "center",
          "background-color": "#46579e",
          color: "#fff",
          "font-size": 11,
          width: 90,
          height: 90,
        },
      },
      {
        selector: "edge",
        style: {
          label: "data(label)",
          "font-size": 9,
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "line-color": "#b14e64",
          "target-arrow-color": "#b14e64",
          width: 2,
        },
      },
    ],
    layout: { name: "circle" },
  });

  const structureTitle = document.getElementById("structure-title");
  const structureNote = document.getElementById("structure-note");

  cy.on("tap", "node", async (event) => {
    const data = event.target.data();
    structureTitle.textContent = `${data.label} (${data.curie})`;
    if (!data.structure) {
      structureNote.textContent =
        "No AlphaFold DB entry for this protein — a real, confirmed gap, not a loading error " +
        "(checked directly against the live API; see docs/ROADMAP.md Phase 10).";
      return;
    }
    structureNote.textContent =
      `Real AlphaFold prediction, global pLDDT ${data.structure.global_plddt.toFixed(1)}.`;
    await viewer.loadStructureFromUrl(data.structure.local_path, "pdb", false, {
      label: data.label,
    });
  });

  await setupComparison();
}

// Runs the real repressilator.omex archive live against every registered
// combine_archive-input_mode simulation adapter - whatever GET /api/plugins
// reports right now, not a hardcoded tellurium/copasi pair - and lets the
// user pick which of the model's real species to plot, instead of a
// hardcoded PX.
async function setupComparison() {
  const chartsContainer = document.getElementById("charts-container");
  const speciesSelect = document.getElementById("species-select");
  const slider = document.getElementById("time-slider");
  const readout = document.getElementById("time-readout");

  chartsContainer.innerHTML = '<p class="hint">Running every registered combine_archive engine live…</p>';

  const plugins = await fetch("/api/plugins").then((r) => r.json());
  const engineNames = plugins.simulation_adapter
    .filter((p) => p.input_mode === "combine_archive")
    .map((p) => p.name);

  if (!engineNames.length) {
    chartsContainer.innerHTML = '<p class="hint">No combine_archive simulation adapter is currently registered.</p>';
    return;
  }

  const runs = await Promise.all(
    engineNames.map(async (name) => {
      try {
        const example = await fetch(`/api/sim/example/${name}`).then((r) => r.json());
        const res = await fetch(`/api/sim/run/${name}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(example),
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
        return { name, ok: true, data: body };
      } catch (err) {
        return { name, ok: false, error: err.message };
      }
    })
  );

  const ok = runs.filter((r) => r.ok);
  chartsContainer.innerHTML = "";

  const speciesSet = new Set();
  for (const run of ok) for (const key of Object.keys(run.data.trajectories)) speciesSet.add(key);
  const species = [...speciesSet].sort();

  speciesSelect.innerHTML = "";
  for (const key of species) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = key;
    speciesSelect.appendChild(option);
  }
  if (species.includes("PX")) speciesSelect.value = "PX";

  const charts = {};
  for (const run of runs) {
    const block = document.createElement("div");
    block.className = "chart-block" + (run.ok ? "" : " chart-missing");
    const heading = document.createElement("h3");
    heading.textContent = run.name;
    block.appendChild(heading);
    if (run.ok) {
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 600 220");
      svg.setAttribute("preserveAspectRatio", "none");
      block.appendChild(svg);
      charts[run.name] = { svg, data: run.data };
    } else {
      const note = document.createElement("p");
      note.textContent = `Not available right now: ${run.error}`;
      block.appendChild(note);
    }
    chartsContainer.appendChild(block);
  }

  const longestRun = ok.reduce((a, b) => (a.data.t.length >= b.data.t.length ? a : b), ok[0]);
  slider.max = String((longestRun ? longestRun.data.t.length : 1) - 1);

  let chartHandles = {};

  function redraw() {
    const key = speciesSelect.value;
    chartHandles = {};
    for (const [name, chart] of Object.entries(charts)) {
      const values = chart.data.trajectories[key] || chart.data.t.map(() => 0);
      chartHandles[name] = drawChart(chart.svg, chart.data.t, values);
    }
    update();
  }

  function update() {
    const index = Number(slider.value);
    const key = speciesSelect.value;
    const parts = [];
    let tLabel = null;
    for (const [name, chart] of Object.entries(charts)) {
      const t = chart.data.t;
      const idx = Math.min(index, t.length - 1);
      chartHandles[name].setMarker(idx);
      if (tLabel === null) tLabel = t[idx];
      const values = chart.data.trajectories[key];
      parts.push(`${name} ${key} = ${values ? values[idx].toFixed(2) : "n/a"}`);
    }
    readout.textContent = `t ≈ ${(tLabel ?? 0).toFixed(1)}  |  ${parts.join("  |  ")}`;
  }

  speciesSelect.addEventListener("change", redraw);
  slider.addEventListener("input", update);
  if (ok.length) redraw();
}

function drawChart(svg, times, values) {
  const width = 600;
  const height = 220;
  const maxValue = Math.max(...values);
  const scaleX = (t) =>
    CHART_PADDING + (t / times[times.length - 1]) * (width - 2 * CHART_PADDING);
  const scaleY = (v) => height - CHART_PADDING - (v / maxValue) * (height - 2 * CHART_PADDING);

  const pathD = values
    .map((v, i) => `${i === 0 ? "M" : "L"} ${scaleX(times[i])} ${scaleY(v)}`)
    .join(" ");

  svg.innerHTML = "";

  const axis = document.createElementNS("http://www.w3.org/2000/svg", "line");
  axis.setAttribute("x1", CHART_PADDING);
  axis.setAttribute("y1", height - CHART_PADDING);
  axis.setAttribute("x2", width - CHART_PADDING);
  axis.setAttribute("y2", height - CHART_PADDING);
  axis.setAttribute("class", "trace-axis");
  svg.appendChild(axis);

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pathD);
  path.setAttribute("class", "trace-path");
  svg.appendChild(path);

  const marker = document.createElementNS("http://www.w3.org/2000/svg", "line");
  marker.setAttribute("y1", CHART_PADDING);
  marker.setAttribute("y2", height - CHART_PADDING);
  marker.setAttribute("class", "trace-marker");
  svg.appendChild(marker);

  return {
    setMarker(index) {
      const x = scaleX(times[index]);
      marker.setAttribute("x1", x);
      marker.setAttribute("x2", x);
    },
  };
}

main();
