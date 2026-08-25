const API = "";

// Categorical palette for charts — accent first, then the semantic hues,
// so a chart's series colors stay visually related to the rest of the UI
// instead of an arbitrary color wheel.
const CHART_COLORS = ["#0c7b74", "#b3791f", "#4a5a8a", "#a83b3b", "#5a8a3a", "#8a3a6a", "#3a8a8a", "#6a5a3a"];

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

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

// ---- Run history: every renderResult call is kept here so past queries
// stay visible instead of being overwritten by the next run.
const HISTORY = [];
let historySeq = 0;

function pushHistory(entry) {
  entry.id = ++historySeq;
  entry.time = new Date();
  HISTORY.unshift(entry);
  HISTORY.length = Math.min(HISTORY.length, 50);
  renderHistoryPanel();
  const stat = document.getElementById("stat-history");
  if (stat) stat.textContent = historySeq;
}

function renderHistoryPanel() {
  const list = document.getElementById("history-list");
  if (!list) return;
  list.innerHTML = "";
  for (const entry of HISTORY) {
    const li = document.createElement("li");
    li.className = "history-item";
    const row = document.createElement("div");
    row.className = "history-row";
    const pill = document.createElement("span");
    pill.className = "badge " + (entry.ok ? "badge-ok" : entry.status === 409 ? "badge-skip" : "badge-error");
    pill.textContent = entry.ok ? "ok" : entry.status === 409 ? "not configured" : "error";
    const time = document.createElement("span");
    time.className = "history-time";
    time.textContent = entry.time.toLocaleTimeString();
    const label = document.createElement("span");
    label.className = "history-label";
    label.textContent = entry.label;
    row.append(time, pill, label);
    if (entry.rerun) {
      const rerunBtn = document.createElement("button");
      rerunBtn.type = "button";
      rerunBtn.className = "history-rerun-btn";
      rerunBtn.textContent = "Re-run";
      rerunBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        entry.rerun();
      });
      row.appendChild(rerunBtn);
    }
    li.appendChild(row);
    row.addEventListener("click", () => {
      const existing = li.querySelector(".history-detail");
      if (existing) {
        existing.remove();
        return;
      }
      const detail = document.createElement("div");
      detail.className = "history-detail";
      if (entry.ok) {
        detail.appendChild(entry.viewBuilder ? entry.viewBuilder() : buildSmartView(entry.data));
      } else {
        const pre = document.createElement("pre");
        pre.className = entry.status === 409 ? "result-skip" : "result-error";
        pre.textContent = entry.message;
        detail.appendChild(pre);
      }
      li.appendChild(detail);
    });
    list.appendChild(li);
  }
}

function setupHistoryPanel() {
  document.getElementById("history-clear-btn").addEventListener("click", () => {
    HISTORY.length = 0;
    renderHistoryPanel();
  });
}

function renderResult(container, label, promise, opts) {
  opts = opts || {};
  container.innerHTML = `<p class="pending">Running ${label}...</p>`;
  return promise
    .then((data) => {
      container.innerHTML = "";
      const viewBuilder = opts.mode === "resolve_all" ? () => buildResolveAllView(data) : () => buildSmartView(data);
      container.appendChild(viewBuilder());
      pushHistory({ label, ok: true, data, viewBuilder, rerun: opts.rerun });
    })
    .catch((err) => {
      const cls = err.status === 409 ? "result-skip" : "result-error";
      const label2 = err.status === 409 ? "Not configured (this is an expected, honest state, not a crash):" : "Error:";
      const pre = document.createElement("pre");
      pre.className = cls;
      pre.textContent = `${label2}\n${err.message}`;
      container.appendChild(pre);
      pushHistory({ label, ok: false, status: err.status, message: `${label2}\n${err.message}`, rerun: opts.rerun });
    });
}

// Disables `button` and swaps its label for the duration of `task()`, so a
// slow adapter (a genome-scale FBA run, a real embedding model) can't be
// double-submitted by an impatient extra click.
function withBusy(button, task) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Running…";
  const settle = () => {
    button.disabled = false;
    button.textContent = original;
  };
  Promise.resolve(task()).then(settle, settle);
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
  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "result-copy-btn";
  copyBtn.textContent = "Copy JSON";
  copyBtn.addEventListener("click", (event) => {
    event.preventDefault();
    navigator.clipboard.writeText(JSON.stringify(data, null, 2)).then(() => {
      copyBtn.textContent = "Copied";
      setTimeout(() => (copyBtn.textContent = "Copy JSON"), 1200);
    });
  });
  summary.appendChild(copyBtn);
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

  ctx.strokeStyle = cssVar("--line-strong") || "#c9c2b3";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, y(minV));
  ctx.lineTo(w - padR, y(minV));
  ctx.stroke();

  ctx.font = "10px " + (cssVar("--font-mono") || "ui-monospace, monospace");
  ctx.fillStyle = cssVar("--ink-faint") || "#7a7364";
  ctx.fillText(maxV.toPrecision(4), 2, y(maxV) + 8);
  ctx.fillText(minV.toPrecision(4), 2, y(minV) + 4);

  series.forEach((s, si) => {
    ctx.strokeStyle = CHART_COLORS[si % CHART_COLORS.length];
    ctx.lineWidth = 1.8;
    if (n === 1) {
      ctx.beginPath();
      ctx.arc(x(0), y(s.values[0]), 3, 0, 2 * Math.PI);
      ctx.fillStyle = CHART_COLORS[si % CHART_COLORS.length];
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

  ctx.font = "10px " + (cssVar("--font-mono") || "ui-monospace, monospace");
  ctx.fillStyle = cssVar("--ink-faint") || "#7a7364";
  ctx.fillText(maxV.toPrecision(4), 2, y(maxV) + 8);
  ctx.fillText(minV.toPrecision(4), 2, y(minV) - 2 < 10 ? y(minV) - 2 : y(minV) - 2);
  ctx.strokeStyle = cssVar("--line-strong") || "#c9c2b3";
  ctx.beginPath();
  ctx.moveTo(padL, y0);
  ctx.lineTo(w - padR, y0);
  ctx.stroke();

  series.forEach((s, i) => {
    const v = s.values[0];
    const barW = bandW * 0.6;
    const xCenter = padL + bandW * (i + 0.5);
    ctx.fillStyle = CHART_COLORS[i % CHART_COLORS.length];
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
    top.forEach((s, i) => {
      const b = document.createElement("span");
      b.className = "badge";
      b.style.borderColor = CHART_COLORS[i % CHART_COLORS.length];
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
function collectFields(obj, prefix, depth, scalars, vectors, excluded) {
  if (depth > 3 || obj === null || typeof obj !== "object") return;
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (excluded && excluded.has(value)) {
      continue; // rendered separately (e.g. as a ranked-dict table)
    } else if (isNumberArray(value)) {
      if (value.length > 16) vectors.push([path, value]);
    } else if (Array.isArray(value)) {
      // short arrays / arrays-of-objects: leave for raw JSON
    } else if (value !== null && typeof value === "object") {
      collectFields(value, path, depth + 1, scalars, vectors, excluded);
    } else if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      scalars.push([path, value]);
    }
  }
}

// Finds plain objects that are really a flat lookup of name -> number (e.g.
// a per-gene perturbation-response delta map) and treats them as a ranked
// table instead of exploding into dozens of individual badges via
// collectFields.
function findNumericDicts(obj, prefix, depth, dicts, excluded) {
  if (depth > 3 || obj === null || typeof obj !== "object" || Array.isArray(obj)) return;
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      const entries = Object.entries(value);
      const allNumeric = entries.length >= 4 && entries.every(([, v]) => typeof v === "number");
      if (allNumeric) {
        dicts.push({ path, entries });
        excluded.add(value);
      } else {
        findNumericDicts(value, path, depth + 1, dicts, excluded);
      }
    }
  }
}

function buildNumericDictTable(dict) {
  const sorted = [...dict.entries].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  return buildObjectArrayTable({
    path: dict.path,
    columns: ["key", "value"],
    rows: sorted.map(([k, v]) => ({ key: k, value: v })),
  });
}

// Finds {category labels} + {one or more parallel numeric series of the
// same length} sitting side by side in the response (e.g. an aging
// trajectory's `index_values` age bins alongside its `values`/
// `cell_counts`) - a shape too small to trigger the sparkline threshold but
// too meaningful to leave as raw JSON.
function findLabeledSeriesGroups(obj, prefix, depth, groups) {
  if (depth > 3 || obj === null || typeof obj !== "object" || Array.isArray(obj)) return;
  const entries = Object.entries(obj);
  const stringArrays = entries.filter(([, v]) => Array.isArray(v) && v.length >= 2 && v.every((x) => typeof x === "string"));
  const numberArrays = entries.filter(([, v]) => isNumberArray(v) && v.length >= 2);
  for (const [, labels] of stringArrays) {
    const aligned = numberArrays.filter(([, v]) => v.length === labels.length);
    if (aligned.length) groups.push({ path: prefix, labels, series: aligned });
  }
  for (const [key, value] of entries) {
    if (value !== null && typeof value === "object") {
      findLabeledSeriesGroups(value, prefix ? `${prefix}.${key}` : key, depth + 1, groups);
    }
  }
}

function buildLabeledSeriesView(group) {
  const wrap = document.createElement("div");
  wrap.className = "chart-wrap";
  const note = document.createElement("p");
  note.className = "hint";
  note.textContent = `${group.path || "(top level)"}, by [${group.labels.join(", ")}] — one chart per series (different series can be on very different scales):`;
  wrap.appendChild(note);

  // One mini chart per series rather than one shared canvas: series here
  // (e.g. a 0-1 fraction next to a raw cell count) can differ by orders of
  // magnitude, and overlaying them on one y-axis would silently flatten
  // the smaller one into a flat line.
  const grid = document.createElement("div");
  grid.className = "labeled-series-grid";
  group.series.forEach(([name, values], i) => {
    const cell = document.createElement("div");
    const label = document.createElement("p");
    label.className = "hint";
    label.innerHTML = `<b>${escapeHtml(name)}</b>`;
    cell.appendChild(label);
    const canvas = document.createElement("canvas");
    canvas.width = 260;
    canvas.height = 120;
    cell.appendChild(canvas);
    drawLineChart(canvas, [{ name, values }]);
    const legend = document.createElement("span");
    legend.className = "badge";
    legend.style.borderColor = CHART_COLORS[i % CHART_COLORS.length];
    legend.textContent = `${group.labels[group.labels.length - 1]}: ${values[values.length - 1]}`;
    cell.appendChild(legend);
    grid.appendChild(cell);
  });
  wrap.appendChild(grid);
  return wrap;
}

// Finds arrays of same-shaped small objects anywhere in the response (e.g.
// a ranked regulator->target edge list, or a top-N gene-delta list) and
// renders each as a real table instead of leaving it to raw JSON, which is
// where structured list results were previously invisible.
function findObjectArrayTables(obj, prefix, depth, tables) {
  if (depth > 3 || obj === null || typeof obj !== "object" || Array.isArray(obj)) return;
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (
      Array.isArray(value) &&
      value.length >= 2 &&
      value.every((v) => v !== null && typeof v === "object" && !Array.isArray(v))
    ) {
      const columns = [];
      for (const row of value) {
        for (const [k, v] of Object.entries(row)) {
          if ((typeof v === "string" || typeof v === "number" || typeof v === "boolean") && !columns.includes(k)) {
            columns.push(k);
          }
        }
      }
      if (columns.length) tables.push({ path, columns, rows: value });
    } else if (value !== null && typeof value === "object") {
      findObjectArrayTables(value, path, depth + 1, tables);
    }
  }
}

function buildObjectArrayTable(table) {
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const ROW_LIMIT = 15;
  const note = document.createElement("p");
  note.className = "hint";
  note.textContent =
    table.rows.length > ROW_LIMIT
      ? `${table.path || "(top level)"}: showing the first ${ROW_LIMIT} of ${table.rows.length} rows (see raw JSON for the rest):`
      : `${table.path || "(top level)"}: ${table.rows.length} rows.`;
  wrap.appendChild(note);

  const el = document.createElement("table");
  el.className = "data-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const col of table.columns) {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  el.appendChild(thead);

  const tbody = document.createElement("tbody");
  for (const row of table.rows.slice(0, ROW_LIMIT)) {
    const tr = document.createElement("tr");
    for (const col of table.columns) {
      const td = document.createElement("td");
      const v = row[col];
      td.textContent = v === undefined ? "" : typeof v === "number" ? (Number.isInteger(v) ? v : v.toPrecision(4)) : String(v);
      if (typeof v === "number") td.className = "num";
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  el.appendChild(tbody);

  const scroller = document.createElement("div");
  scroller.className = "table-scroll";
  scroller.appendChild(el);
  wrap.appendChild(scroller);
  return wrap;
}

function isMonotonic(values) {
  let increasing = true;
  let decreasing = true;
  for (let i = 1; i < values.length; i++) {
    if (values[i] <= values[i - 1]) increasing = false;
    if (values[i] >= values[i - 1]) decreasing = false;
  }
  return increasing || decreasing;
}

// Finds exactly-two same-length numeric arrays at one object level (e.g. a
// dose-response curve's `doses` + `responses`) and treats them as an X/Y
// pair rather than two independent series — the monotonic one (doses
// always are, by construction) is taken as the X axis so this works
// without hardcoding either array's name.
function findXYPairs(obj, prefix, depth, pairs, consumed) {
  if (depth > 3 || obj === null || typeof obj !== "object" || Array.isArray(obj)) return;
  const entries = Object.entries(obj);
  const numArrays = entries.filter(([, v]) => isNumberArray(v) && v.length >= 3 && !consumed.has(v));
  if (numArrays.length === 2) {
    const [a, b] = numArrays;
    const xFirst = isMonotonic(a[1]) || !isMonotonic(b[1]);
    const [xKey, xValues] = xFirst ? a : b;
    const [yKey, yValues] = xFirst ? b : a;
    pairs.push({ path: prefix, xKey, xValues, yKey, yValues });
    consumed.add(xValues);
    consumed.add(yValues);
  }
  for (const [key, value] of entries) {
    if (value !== null && typeof value === "object") {
      findXYPairs(value, prefix ? `${prefix}.${key}` : key, depth + 1, pairs, consumed);
    }
  }
}

function drawXYChart(canvas, xValues, yValues, useLogX) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  const padL = 46, padB = 22, padT = 10, padR = 10;
  ctx.clearRect(0, 0, w, h);
  const tx = useLogX ? (v) => Math.log10(v) : (v) => v;
  const xs = xValues.map(tx);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(0, ...yValues), maxY = Math.max(...yValues, minY + 1e-9);
  const x = (v) => padL + ((v - minX) / (maxX - minX || 1)) * (w - padL - padR);
  const y = (v) => h - padB - ((v - minY) / (maxY - minY || 1)) * (h - padT - padB);

  ctx.strokeStyle = cssVar("--line-strong") || "#c9c2b3";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padL, y(minY));
  ctx.lineTo(w - padR, y(minY));
  ctx.stroke();

  ctx.font = "10px " + (cssVar("--font-mono") || "ui-monospace, monospace");
  ctx.fillStyle = cssVar("--ink-faint") || "#7a7364";
  ctx.fillText(maxY.toPrecision(3), 2, y(maxY) + 8);
  ctx.fillText(minY.toPrecision(3), 2, y(minY) + 4);
  ctx.fillText(xValues[0].toPrecision(3), padL - 4, h - 6);
  ctx.fillText(xValues[xValues.length - 1].toPrecision(3), w - padR - 34, h - 6);

  ctx.strokeStyle = CHART_COLORS[0];
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  xs.forEach((xv, i) => (i === 0 ? ctx.moveTo(x(xv), y(yValues[i])) : ctx.lineTo(x(xv), y(yValues[i]))));
  ctx.stroke();
  ctx.fillStyle = CHART_COLORS[0];
  xs.forEach((xv, i) => {
    ctx.beginPath();
    ctx.arc(x(xv), y(yValues[i]), 2.5, 0, 2 * Math.PI);
    ctx.fill();
  });
}

function buildXYPairView(pair) {
  const wrap = document.createElement("div");
  wrap.className = "chart-wrap";
  const useLogX = pair.xValues.every((v) => v > 0) && Math.max(...pair.xValues) / Math.min(...pair.xValues) > 100;
  const note = document.createElement("p");
  note.className = "hint";
  note.textContent = `${pair.path ? pair.path + ": " : ""}${pair.yKey} vs ${pair.xKey}, ${pair.xValues.length} points${useLogX ? " (log-scale x-axis)" : ""}:`;
  wrap.appendChild(note);
  const canvas = document.createElement("canvas");
  canvas.width = 560;
  canvas.height = 200;
  wrap.appendChild(canvas);
  drawXYChart(canvas, pair.xValues, pair.yValues, useLogX);
  return wrap;
}

function buildSmartView(data) {
  const root = document.createElement("div");
  if (data && typeof data === "object" && !Array.isArray(data)) {
    if (data.trajectories && typeof data.trajectories === "object") {
      root.appendChild(buildTrajectoryChart(data));
    } else {
      const labeledGroups = [];
      findLabeledSeriesGroups(data, "", 0, labeledGroups);
      const consumed = new Set(labeledGroups.flatMap((g) => g.series.map(([, v]) => v)));

      const xyPairs = [];
      findXYPairs(data, "", 0, xyPairs, consumed);

      const tables = [];
      findObjectArrayTables(data, "", 0, tables);

      const numericDicts = [];
      const dictExcluded = new Set();
      findNumericDicts(data, "", 0, numericDicts, dictExcluded);

      const scalars = [];
      const vectors = [];
      collectFields(data, "", 0, scalars, vectors, dictExcluded);
      if (scalars.length) root.appendChild(makeBadgeRow(scalars));
      for (const group of labeledGroups) root.appendChild(buildLabeledSeriesView(group));
      for (const pair of xyPairs) root.appendChild(buildXYPairView(pair));
      for (const [path, values] of vectors) {
        if (!consumed.has(values)) root.appendChild(buildVectorView(path, values));
      }
      for (const table of tables) root.appendChild(buildObjectArrayTable(table));
      for (const dict of numericDicts) root.appendChild(buildNumericDictTable(dict));
    }
  }
  root.appendChild(makeRawDetails(data));
  return root;
}

function computeAgreement(named) {
  const withTraj = named.filter((n) => n.data && n.data.trajectories);
  if (withTraj.length < 2) return null;
  const commonNames = Object.keys(withTraj[0].data.trajectories).filter((name) =>
    withTraj.every((n) => name in n.data.trajectories)
  );
  if (!commonNames.length) return { note: "no variable name is shared across every engine's output.", pairs: [] };
  const lengths = withTraj.map((n) => n.data.trajectories[commonNames[0]].length);
  if (new Set(lengths).size !== 1) {
    return { note: "engines reported different numbers of time points — can't line up final values.", pairs: [] };
  }
  const pairs = commonNames.slice(0, 8).map((name) => {
    const vals = withTraj.map((n) => n.data.trajectories[name][n.data.trajectories[name].length - 1]);
    const spread = Math.max(...vals) - Math.min(...vals);
    return [`Δ ${name}`, spread.toPrecision(4)];
  });
  return { note: null, pairs };
}

function buildCompareView(runs) {
  const root = document.createElement("div");
  const statusRow = document.createElement("div");
  statusRow.className = "badge-row";
  for (const run of runs) {
    const b = document.createElement("span");
    b.className = "badge " + (run.ok ? "badge-ok" : run.status === 409 ? "badge-skip" : "badge-error");
    b.textContent = `${run.name}: ${run.ok ? "ok" : run.status === 409 ? "not configured" : "error"}`;
    statusRow.appendChild(b);
  }
  root.appendChild(statusRow);

  const agreement = computeAgreement(runs.filter((r) => r.ok));
  if (agreement) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = agreement.note || "Spread across engines' final values for variables every engine reported (0 = perfect agreement):";
    root.appendChild(note);
    if (agreement.pairs.length) root.appendChild(makeBadgeRow(agreement.pairs));
  }

  for (const run of runs) {
    const heading = document.createElement("h3");
    heading.className = "compare-engine-heading";
    heading.textContent = run.name;
    root.appendChild(heading);
    if (run.ok) {
      root.appendChild(buildSmartView(run.data));
    } else {
      const pre = document.createElement("pre");
      pre.className = run.status === 409 ? "result-skip" : "result-error";
      pre.textContent = run.message;
      root.appendChild(pre);
    }
  }
  return root;
}

function buildResolveAllView(data) {
  const root = document.createElement("div");
  const row = document.createElement("div");
  row.className = "badge-row";
  const detailHost = document.createElement("div");
  detailHost.className = "chart-wrap";

  for (const [connector, record] of Object.entries(data)) {
    const isMatch = !(record && record.error);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "badge badge-button " + (isMatch ? "badge-ok" : "badge-skip");
    b.textContent = `${connector}: ${isMatch ? "match — click to view" : "no match / not configured"}`;
    b.addEventListener("click", () => {
      detailHost.innerHTML = "";
      const heading = document.createElement("h3");
      heading.className = "compare-engine-heading";
      heading.textContent = connector;
      detailHost.appendChild(heading);
      detailHost.appendChild(isMatch ? buildSmartView(record) : Object.assign(document.createElement("pre"), { className: "result-skip", textContent: record.error }));
    });
    row.appendChild(b);
  }
  root.appendChild(row);
  root.appendChild(detailHost);
  root.appendChild(makeRawDetails(data));
  return root;
}

function setupInventoryFilters() {
  for (const [filterId, listId] of [
    ["inventory-data-filter", "inventory-data"],
    ["inventory-sim-filter", "inventory-sim"],
    ["inventory-ai-filter", "inventory-ai"],
  ]) {
    const input = document.getElementById(filterId);
    const list = document.getElementById(listId);
    input.addEventListener("input", () => {
      const needle = input.value.trim().toLowerCase();
      for (const li of list.children) {
        li.style.display = li.textContent.toLowerCase().includes(needle) ? "" : "none";
      }
    });
  }
}

async function loadInventory() {
  const plugins = await fetchJSON("/api/plugins");

  document.getElementById("stat-data").textContent = plugins.data_connector.length;
  document.getElementById("stat-sim").textContent = plugins.simulation_adapter.length;
  document.getElementById("stat-ai").textContent = plugins.ai_model_adapter.length;

  const dataList = document.getElementById("inventory-data");
  for (const p of plugins.data_connector) {
    const li = document.createElement("li");
    li.textContent = p.name;
    li.title = p.description ? `${p.description}\n\n(${p.distribution})` : p.distribution;
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
    if (p.description) li.title = p.description;
    li.addEventListener("click", () => {
      simSelect.value = p.name;
      document.getElementById("sim-panel").scrollIntoView({ behavior: "smooth" });
    });
    simList.appendChild(li);
  }

  const byMode = new Map();
  for (const p of plugins.simulation_adapter) {
    const mode = p.input_mode || "toy_dict";
    if (!byMode.has(mode)) byMode.set(mode, []);
    byMode.get(mode).push(p.name);
  }
  const compareSelect = document.getElementById("compare-select");
  for (const [mode, names] of byMode.entries()) {
    const option = document.createElement("option");
    option.value = mode;
    option.dataset.names = names.join(",");
    option.textContent = `${mode} (${names.length} adapter${names.length === 1 ? "" : "s"}: ${names.join(", ")})`;
    compareSelect.appendChild(option);
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
    if (p.description) li.title = p.description;
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
    const label = `resolve_all("${curie}")`;
    const run = () =>
      renderResult(results, label, fetchJSON(`/api/data/resolve?curie=${encodeURIComponent(curie)}`), { mode: "resolve_all", rerun: run });
    withBusy(button, run);
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

  const runBtn = document.getElementById("ai-run-btn");
  runBtn.addEventListener("click", () => {
    let input;
    try {
      input = JSON.parse(textarea.value || "{}");
    } catch (err) {
      results.innerHTML = `<pre class="result-error">Invalid JSON input:\n${escapeHtml(err.message)}</pre>`;
      return;
    }
    const name = select.value;
    const label = `${name}.predict(...)`;
    const run = () =>
      renderResult(
        results,
        label,
        fetchJSON(`/api/ai/predict/${name}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input }),
        }),
        { rerun: run }
      );
    withBusy(runBtn, run);
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

  const runBtn = document.getElementById("sim-run-btn");
  runBtn.addEventListener("click", () => {
    let body;
    try {
      body = JSON.parse(textarea.value || "{}");
    } catch (err) {
      results.innerHTML = `<pre class="result-error">Invalid JSON input:\n${escapeHtml(err.message)}</pre>`;
      return;
    }
    const name = select.value;
    const label = `${name}.run(...)`;
    const run = () =>
      renderResult(
        results,
        label,
        fetchJSON(`/api/sim/run/${name}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
        { rerun: run }
      );
    withBusy(runBtn, run);
  });
}

function setupComparePanel() {
  const select = document.getElementById("compare-select");
  const textarea = document.getElementById("compare-input");
  const results = document.getElementById("compare-results");

  document.getElementById("compare-load-example-btn").addEventListener("click", async () => {
    const names = (select.selectedOptions[0]?.dataset.names || "").split(",").filter(Boolean);
    if (!names.length) return;
    const example = await fetchJSON(`/api/sim/example/${names[0]}`);
    textarea.value = JSON.stringify(example, null, 2);
  });

  const runBtn = document.getElementById("compare-run-btn");
  runBtn.addEventListener("click", () => {
    const names = (select.selectedOptions[0]?.dataset.names || "").split(",").filter(Boolean);
    if (!names.length) return;
    let body;
    try {
      body = JSON.parse(textarea.value || "{}");
    } catch (err) {
      results.innerHTML = `<pre class="result-error">Invalid JSON input:\n${escapeHtml(err.message)}</pre>`;
      return;
    }
    const label = `compare[${select.value}]: ${names.join(", ")}`;
    const run = async () => {
      results.innerHTML = `<p class="pending">Running ${label}...</p>`;
      const runs = await Promise.all(
        names.map(async (name) => {
          try {
            const data = await fetchJSON(`/api/sim/run/${name}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            });
            return { name, ok: true, data };
          } catch (err) {
            return { name, ok: false, status: err.status, message: err.message };
          }
        })
      );
      results.innerHTML = "";
      results.appendChild(buildCompareView(runs));
      pushHistory({ label, ok: true, viewBuilder: () => buildCompareView(runs), rerun: run });
    };
    withBusy(runBtn, run);
  });
}

async function runQuickstart(kind) {
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  if (kind === "data") {
    document.getElementById("data-curie").value = "uniprot:P04637";
    document.getElementById("data-search-btn").click();
    document.getElementById("data-panel").scrollIntoView({ behavior: "smooth" });
  } else if (kind === "ai") {
    document.getElementById("ai-select").value = "esmc";
    document.getElementById("ai-load-example-btn").click();
    await wait(500);
    document.getElementById("ai-run-btn").click();
    document.getElementById("ai-panel").scrollIntoView({ behavior: "smooth" });
  } else if (kind === "sim") {
    document.getElementById("sim-select").value = "cobrapy";
    document.getElementById("sim-load-example-btn").click();
    await wait(800);
    const textarea = document.getElementById("sim-input");
    try {
      const parsed = JSON.parse(textarea.value);
      parsed.config = Object.assign({}, parsed.config, { gene_knockouts: ["b3189"] });
      textarea.value = JSON.stringify(parsed, null, 2);
    } catch (err) {
      /* if the example didn't load in time, Run will just report the JSON error */
    }
    document.getElementById("sim-run-btn").click();
    document.getElementById("sim-panel").scrollIntoView({ behavior: "smooth" });
  } else if (kind === "compare") {
    document.getElementById("compare-select").value = "combine_archive";
    document.getElementById("compare-load-example-btn").click();
    await wait(500);
    document.getElementById("compare-run-btn").click();
    document.getElementById("compare-panel").scrollIntoView({ behavior: "smooth" });
  }
}

function setupQuickstart() {
  document.querySelectorAll("[data-quickstart]").forEach((btn) => {
    btn.addEventListener("click", () => runQuickstart(btn.dataset.quickstart));
  });
}

function setupThemeToggle() {
  const btn = document.getElementById("theme-toggle-btn");
  const apply = (theme) => {
    document.documentElement.dataset.theme = theme;
    btn.textContent = theme === "dark" ? "☾ Dark" : "☆ Light";
  };
  apply(document.documentElement.dataset.theme || "light");
  btn.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("cradle-explorer-theme", next);
    apply(next);
  });
}

function setupActiveNav() {
  const links = Array.from(document.querySelectorAll(".topnav a"));
  const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const link = byId.get(entry.target.id);
        if (!link) continue;
        link.classList.toggle("active", entry.isIntersecting);
      }
    },
    { rootMargin: "-40% 0px -50% 0px" }
  );
  for (const id of byId.keys()) {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  }
}

async function main() {
  await loadInventory();
  setupInventoryFilters();
  setupDataPanel();
  setupAiPanel();
  setupSimPanel();
  setupComparePanel();
  setupHistoryPanel();
  setupActiveNav();
  setupThemeToggle();
  setupQuickstart();
}

main();
