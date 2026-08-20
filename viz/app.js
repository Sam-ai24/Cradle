// Cradle Phase 10: the scale-router. Loads real, already-validated Cradle
// data (Phase 1-4's repressilator, Phase 2's two adapters, Phase 3's real
// AlphaFold structures) and links a pathway-scale view, a molecular-scale
// view, and a two-run comparison behind one shared time-slider state.

const CHART_PADDING = 24;

async function main() {
  const [graph, trajectories] = await Promise.all([
    fetch("data/repressilator_graph.json").then((r) => r.json()),
    fetch("data/repressilator_trajectories.json").then((r) => r.json()),
  ]);

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

  setupComparison(trajectories);
}

function setupComparison(trajectories) {
  const tellurium = trajectories.tellurium;
  const copasi = trajectories.copasi;

  const telluriumSvg = document.getElementById("chart-tellurium");
  const copasiSvg = document.getElementById("chart-copasi");

  const telluriumChart = drawChart(telluriumSvg, tellurium.t, tellurium.PX);
  const copasiChart = drawChart(copasiSvg, copasi.t, copasi.PX);

  const slider = document.getElementById("time-slider");
  const readout = document.getElementById("time-readout");
  slider.max = String(tellurium.t.length - 1);

  function update() {
    const index = Number(slider.value);
    telluriumChart.setMarker(index);
    copasiChart.setMarker(index);
    readout.textContent =
      `t = ${tellurium.t[index].toFixed(1)}  |  Tellurium PX = ${tellurium.PX[index].toFixed(1)}` +
      `  |  COPASI PX = ${copasi.PX[index].toFixed(1)}`;
  }

  slider.addEventListener("input", update);
  update();
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
