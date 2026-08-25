const API = "";

async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${response.status}`;
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return body;
}

function renderResult(container, label, promise, opts) {
  opts = opts || {};
  container.innerHTML = `<p class="pending">Running ${label}...</p>`;
  promise
    .then((data) => {
      container.innerHTML = "";
      if (opts.mode === "resolve_all") {
        container.appendChild(buildResolveAllView(data));
      } else {
        container.appendChild(buildSmartView(data));
      }
    })
    .catch((err) => {
      const cls = err.status === 409 ? "result-skip" : "result-error";
      const label2 = err.status === 409 ? "Not configured (this is an expected, honest state, not a crash):" : "Error:";
      const pre = document.createElement("pre");
      pre.className = cls;
      pre.textContent = `${label2}\n${err.message}`;
      container.appendChild(pre);
    });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ---- Result rendering: every shape below is inferred generically from the
// real response JSON (trajectories, long numeric arrays, per-connector
// records) — there is no per-adapter special-casing of *content*, only of
// *shape*, so this stays honest for plugins that don't exist yet either.

function isNumberArray(value) {
  return Array.isArray(value) && value.length > 0 && value.every((v) => typeof v === "number");
}

function makeRawDetails(data) {
  const details = document.createElement("details");
  details.className = "raw-json";
  const summary = document.createElement("summary");
  summary.textContent = "Show raw JSON";
  const pre = document.createElement("pre");
  pre.className = "result-ok";
  pre.textContent = JSON.stringify(data, null, 2);
  details.appendChild(summary);
  details.appendChild(pre);
  return details;
}

function makeBadgeRow(pairs) {
  const row = document.createElement("div");
  row.className = "badge-row";
  for (const [key, value] of pairs) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.innerHTML = `<b>${escapeHtml(key)}</b> ${escapeHtml(String(value))}`;
    row.appendChild(badge);
  }
  return row;
}

function drawLineChart(canvas, series, xLabel) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 40, padB = 20, padT = 10, padR = 10;
  ctx.clearRect(0, 0, w, h);
  const allVals = series.flatMap((s) => s.values);
  const minV = Math.min(0, ...allVals);
  const maxV = Math.max(...allVals, minV + 1e-9);
  const n = series[0].values.length;
  const x = (i) => padL + (n === 1 ? 0 : (i / (n - 1)) * (w - padL - padR));
  const y = (v) => h - padB - ((v - minV) / (maxV - minV || 1)) * (h - padT - padB);

  ctx.strokeStyle = "#c9c2b3";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, y(minV));
  ctx.lineTo(w - padR, y(minV));
  ctx.stroke();

  ctx.font = "10px ui-monospace, monospace";
  ctx.fillStyle = "#7a7364";
  ctx.fillText(maxV.toPrecision(4), 2, y(maxV) + 8);
  ctx.fillText(minV.toPrecision(4), 2, y(minV) + 4);

  const colors = ["#7a4b3a", "#3a6a5a", "#4a5a8a", "#8a6a3a", "#8a3a6a", "#3a8a8a", "#5a5a5a", "#8a4a4a"];
  series.forEach((s, si) => {
    ctx.strokeStyle = colors[si % colors.length];
    ctx.lineWidth = 1.6;
    if (n === 1) {
      ctx.beginPath();
      ctx.arc(x(0), y(s.values[0]), 3, 0, 2 * Math.PI);
      ctx.fillStyle = colors[si % colors.length];
      ctx.fill();
    } else {
      ctx.beginPath();
      s.values.forEach((v, i) => (i === 0 ? ctx.moveTo(x(i), y(v)) : ctx.lineTo(x(i), y(v))));
      ctx.stroke();
    }
  });
}

function drawBarChart(canvas, series) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 44, padB = 20, padT = 10, padR = 10;
  ctx.clearRect(0, 0, w, h);
  const vals = series.map((s) => s.values[0]);
  const minV = Math.min(0, ...vals);
  const maxV = Math.max(0, ...vals, minV + 1e-9);
  const y0 = h - padB - ((0 - minV) / (maxV - minV || 1)) * (h - padT - padB);
  const y = (v) => h - padB - ((v - minV) / (maxV - minV || 1)) * (h - padT - padB);
  const bandW = (w - padL - padR) / series.length;

  ctx.font = "10px ui-monospace, monospace";
  ctx.fillStyle = "#7a7364";
  ctx.fillText(maxV.toPrecision(4), 2, y(maxV) + 8);
  ctx.fillText(minV.toPrecision(4), 2, y(minV) - 2 < 10 ? y(minV) - 2 : y(minV) - 2);
  ctx.strokeStyle = "#c9c2b3";
  ctx.beginPath();
  ctx.moveTo(padL, y0);
  ctx.lineTo(w - padR, y0);
  ctx.stroke();

  const colors = ["#7a4b3a", "#3a6a5a", "#4a5a8a", "#8a6a3a", "#8a3a6a", "#3a8a8a", "#5a5a5a", "#8a4a4a"];
  series.forEach((s, i) => {
    const v = s.values[0];
    const barW = bandW * 0.6;
    const xCenter = padL + bandW * (i + 0.5);
    ctx.fillStyle = colors[i % colors.length];
    const top = Math.min(y(v), y0);
    const height = Math.abs(y(v) - y0);
    ctx.fillRect(xCenter - barW / 2, top, barW, Math.max(height, 1));
  });
}

function buildTrajectoryChart(data) {
  const wrap = document.createElement("div");
  wrap.className = "chart-wrap";

  const scalarPairs = Object.entries(data).filter(
    ([k, v]) => k !== "trajectories" && k !== "t" && (typeof v === "string" || typeof v === "number" || typeof v === "boolean")
  );
  if (scalarPairs.length) wrap.appendChild(makeBadgeRow(scalarPairs));

  const names = Object.keys(data.trajectories);
  const isSteadyState = (data.t || []).length <= 1;
  const ranked = names
    .map((name) => {
      const values = data.trajectories[name];
      const range = Math.max(...values) - Math.min(...values);
      return { name, values, magnitude: isSteadyState ? Math.abs(values[0]) : range };
    })
    .sort((a, b) => b.magnitude - a.magnitude);
  const top = ranked.filter((s) => s.magnitude > 1e-9).slice(0, 8);

  if (top.length) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = isSteadyState
      ? `Top ${top.length} of ${names.length} reactions by |flux| (steady-state FBA snapshot — bars, not a time course):`
      : `Top ${top.length} of ${names.length} variables by range, over ${data.t.length} time points:`;
    wrap.appendChild(note);

    const canvas = document.createElement("canvas");
    canvas.width = 560;
    canvas.height = 200;
    wrap.appendChild(canvas);
    if (isSteadyState) drawBarChart(canvas, top);
    else drawLineChart(canvas, top, "t");

    const legend = document.createElement("div");
    legend.className = "badge-row";
    const colors = ["#7a4b3a", "#3a6a5a", "#4a5a8a", "#8a6a3a", "#8a3a6a", "#3a8a8a", "#5a5a5a", "#8a4a4a"];
    top.forEach((s, i) => {
      const b = document.createElement("span");
      b.className = "badge";
      b.style.borderColor = colors[i % colors.length];
      b.textContent = `${s.name}: ${(isSteadyState ? s.values[0] : s.values[s.values.length - 1]).toPrecision(4)}`;
      legend.appendChild(b);
    });
    wrap.appendChild(legend);
  } else {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = `All ${names.length} reported variables are ~0 — see raw JSON below.`;
    wrap.appendChild(note);
  }
  return wrap;
}

function buildVectorView(name, values) {
  const wrap = document.createElement("div");
  wrap.className = "chart-wrap";
  const note = document.createElement("p");
  note.className = "hint";
  note.textContent = `${name}: a ${values.length}-dimensional real vector (sparkline of all ${values.length} values):`;
  wrap.appendChild(note);
  const canvas = document.createElement("canvas");
  canvas.width = 560;
  canvas.height = 100;
  wrap.appendChild(canvas);
  drawLineChart(canvas, [{ name, values }]);
  return wrap;
}

// Recursively collect scalar fields and long numeric vectors anywhere in the
// response tree (bounded depth) - handles both flat sim results and the
// AI-adapter `{output: {...}, provenance: {...}}` wrapper shape without
// hardcoding either one by name.
function collectFields(obj, prefix, depth, scalars, vectors) {
  if (depth > 3 || obj === null || typeof obj !== "object") return;
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (isNumberArray(value)) {
      if (value.length > 16) vectors.push([path, value]);
    } else if (Array.isArray(value)) {
      // short arrays / arrays-of-objects: leave for raw JSON
    } else if (value !== null && typeof value === "object") {
      collectFields(value, path, depth + 1, scalars, vectors);
    } else if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      scalars.push([path, value]);
    }
  }
}

function buildSmartView(data) {
  const root = document.createElement("div");
  if (data && typeof data === "object" && !Array.isArray(data)) {
    if (data.trajectories && typeof data.trajectories === "object") {
      root.appendChild(buildTrajectoryChart(data));
    } else {
      const scalars = [];
      const vectors = [];
      collectFields(data, "", 0, scalars, vectors);
      if (scalars.length) root.appendChild(makeBadgeRow(scalars));
      for (const [path, values] of vectors) root.appendChild(buildVectorView(path, values));
    }
  }
  root.appendChild(makeRawDetails(data));
  return root;
}

function buildResolveAllView(data) {
  const root = document.createElement("div");
  const pairs = Object.entries(data).map(([connector, record]) => [
    connector,
    record && record.error ? "no match / not configured" : "match",
  ]);
  const row = document.createElement("div");
  row.className = "badge-row";
  for (const [connector, state] of pairs) {
    const b = document.createElement("span");
    b.className = state === "match" ? "badge badge-ok" : "badge badge-skip";
    b.textContent = `${connector}: ${state}`;
    row.appendChild(b);
  }
  root.appendChild(row);
  root.appendChild(makeRawDetails(data));
  return root;
}

async function loadInventory() {
  const plugins = await fetchJSON("/api/plugins");

  const dataList = document.getElementById("inventory-data");
  for (const p of plugins.data_connector) {
    const li = document.createElement("li");
    li.textContent = p.name;
    li.title = p.distribution;
    li.addEventListener("click", () => {
      document.getElementById("data-curie").scrollIntoView({ behavior: "smooth" });
    });
    dataList.appendChild(li);
  }

  const simSelect = document.getElementById("sim-select");
  const simList = document.getElementById("inventory-sim");
  for (const p of plugins.simulation_adapter) {
    const option = document.createElement("option");
    option.value = p.name;
    option.textContent = `${p.name} (${p.input_mode || "toy_dict"})`;
    simSelect.appendChild(option);

    const li = document.createElement("li");
    li.textContent = `${p.name} — ${p.input_mode || "toy_dict"}`;
    li.addEventListener("click", () => {
      simSelect.value = p.name;
      document.getElementById("sim-panel").scrollIntoView({ behavior: "smooth" });
    });
    simList.appendChild(li);
  }

  const aiSelect = document.getElementById("ai-select");
  const aiList = document.getElementById("inventory-ai");
  for (const p of plugins.ai_model_adapter) {
    const option = document.createElement("option");
    option.value = p.name;
    option.textContent = `${p.name} (${p.contract_type})`;
    aiSelect.appendChild(option);

    const li = document.createElement("li");
    li.textContent = `${p.name} — ${p.contract_type}`;
    li.addEventListener("click", () => {
      aiSelect.value = p.name;
      document.getElementById("ai-panel").scrollIntoView({ behavior: "smooth" });
    });
    aiList.appendChild(li);
  }
}

function setupDataPanel() {
  const button = document.getElementById("data-search-btn");
  const input = document.getElementById("data-curie");
  const results = document.getElementById("data-results");

  button.addEventListener("click", () => {
    const curie = input.value.trim();
    if (!curie) return;
    renderResult(results, `resolve_all("${curie}")`, fetchJSON(`/api/data/resolve?curie=${encodeURIComponent(curie)}`), { mode: "resolve_all" });
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") button.click();
  });
}

function setupAiPanel() {
  const select = document.getElementById("ai-select");
  const textarea = document.getElementById("ai-input");
  const results = document.getElementById("ai-results");

  document.getElementById("ai-load-example-btn").addEventListener("click", async () => {
    const example = await fetchJSON(`/api/ai/example/${select.value}`);
    textarea.value = JSON.stringify(example, null, 2);
  });

  document.getElementById("ai-run-btn").addEventListener("click", () => {
    let input;
    try {
      input = JSON.parse(textarea.value || "{}");
    } catch (err) {
      results.innerHTML = `<pre class="result-error">Invalid JSON input:\n${escapeHtml(err.message)}</pre>`;
      return;
    }
    renderResult(
      results,
      `${select.value}.predict(...)`,
      fetchJSON(`/api/ai/predict/${select.value}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input }),
      })
    );
  });
}

function setupSimPanel() {
  const select = document.getElementById("sim-select");
  const textarea = document.getElementById("sim-input");
  const results = document.getElementById("sim-results");

  document.getElementById("sim-load-example-btn").addEventListener("click", async () => {
    const example = await fetchJSON(`/api/sim/example/${select.value}`);
    textarea.value = JSON.stringify(example, null, 2);
  });

  document.getElementById("sim-run-btn").addEventListener("click", () => {
    let body;
    try {
      body = JSON.parse(textarea.value || "{}");
    } catch (err) {
      results.innerHTML = `<pre class="result-error">Invalid JSON input:\n${escapeHtml(err.message)}</pre>`;
      return;
    }
    renderResult(
      results,
      `${select.value}.run(...)`,
      fetchJSON(`/api/sim/run/${select.value}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
    );
  });
}

async function main() {
  await loadInventory();
  setupDataPanel();
  setupAiPanel();
  setupSimPanel();
}

main();
