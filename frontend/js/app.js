const state = {
  groups: [],
  config: {},
  targets: [],
};

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, props = {}, children = []) => {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  });
  children.forEach((c) => node.appendChild(c));
  return node;
};

// ---------------------------------------------------------------- targets

function parseTargetsFromText(text) {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"));
}

function refreshTargetsCount() {
  const text = $("#targets-input").value;
  state.targets = parseTargetsFromText(text);
  $("#targets-count").textContent = `${state.targets.length} dominio${state.targets.length === 1 ? "" : "s"}`;
}

$("#targets-input").addEventListener("input", refreshTargetsCount);

$("#targets-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  const current = $("#targets-input").value;
  const merged = current.trim() ? current.trim() + "\n" + text : text;
  $("#targets-input").value = merged;
  refreshTargetsCount();
});

// ---------------------------------------------------------------- param form

function buildLiveCaption(param, value) {
  const opt = (param.options || []).find((o) => o.value === value);
  return opt ? opt.help : "";
}

function renderControl(param) {
  const current = state.config[param.id];

  if (param.type === "bool") {
    const input = el("input", { type: "checkbox" });
    input.checked = !!current;
    input.addEventListener("change", () => {
      state.config[param.id] = input.checked;
    });
    return el("label", { class: "switch" }, [input, el("span", { class: "switch-track" })]);
  }

  if (param.type === "select") {
    const select = el("select");
    (param.options || []).forEach((o) => {
      const opt = el("option", { value: o.value, text: o.label });
      if (o.value === current) opt.selected = true;
      select.appendChild(opt);
    });
    const caption = el("p", { class: "param-live-caption", text: buildLiveCaption(param, current) });
    select.addEventListener("change", () => {
      state.config[param.id] = select.value;
      caption.textContent = buildLiveCaption(param, select.value);
    });
    return { control: select, caption };
  }

  // int
  const input = el("input", {
    type: "number",
    value: current,
    min: param.min ?? "",
    max: param.max ?? "",
  });
  input.addEventListener("change", () => {
    state.config[param.id] = Number(input.value);
  });
  return input;
}

function renderParam(param) {
  const controlResult = renderControl(param);
  const isSelect = param.type === "select";
  const controlNode = isSelect ? controlResult.control : controlResult;

  const controlWrap = el("div", {
    class: param.type === "bool" ? "param-control param-control-bool" : "param-control",
  }, [controlNode]);

  const infoToggle = el("button", { class: "info-toggle", type: "button", text: "i", "aria-expanded": "false" });

  const infoPanel = el("div", { class: "param-info" }, [
    el("p", { text: param.help }),
    el("p", { class: "recommend", text: param.recommend }),
  ]);
  infoPanel.hidden = true;

  infoToggle.addEventListener("click", () => {
    const open = infoPanel.hidden;
    infoPanel.hidden = !open;
    infoToggle.setAttribute("aria-expanded", String(open));
  });

  const main = el("div", { class: "param-main" }, [
    el("span", { class: "param-label", text: param.label }),
    controlWrap,
    infoToggle,
  ]);

  const row = el("div", { class: "param-row" }, [main]);
  if (isSelect) row.appendChild(controlResult.caption);
  row.appendChild(infoPanel);
  return row;
}

function renderParamGroups() {
  const container = $("#param-groups");
  container.innerHTML = "";
  state.groups.forEach((group) => {
    const groupEl = el("div", { class: "param-group" }, [
      el("div", { class: "param-group-head", text: group.label }),
      el("div", { class: "param-group-desc", text: group.description }),
    ]);
    group.params.forEach((p) => groupEl.appendChild(renderParam(p)));
    container.appendChild(groupEl);
  });
}

// ---------------------------------------------------------------- launch

async function loadParams() {
  const res = await fetch("/api/params");
  const data = await res.json();
  state.groups = data.groups;
  state.config = { ...data.defaults };
  renderParamGroups();
}

$("#start-btn").addEventListener("click", async () => {
  refreshTargetsCount();
  const statusEl = $("#launch-status");
  if (state.targets.length === 0) {
    statusEl.textContent = "Añade al menos un dominio antes de lanzar.";
    return;
  }
  $("#start-btn").disabled = true;
  statusEl.textContent = "Lanzando lote…";

  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ targets: state.targets, config: state.config }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "error al lanzar el lote");
    statusEl.textContent = `Lote ${data.run_ts} lanzado (${data.targets.length} dominios).`;
    refreshJobs();
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    $("#start-btn").disabled = false;
  }
});

// ---------------------------------------------------------------- jobs list

const STATUS_LABEL = {
  pending: "en cola",
  running: "escaneando",
  done: "completado",
  ok: "ok",
  fail: "con fails",
  warn: "con warnings",
  error: "error",
  timeout: "timeout",
};

// scanner.run_scan() termina un dominio con status "ok"/"fail"/"warn"/
// "error"/"timeout" (nunca "done"). "done" solo aparece cuando el job
// se reconstruye desde disco tras un reinicio del backend (jobs.py
// get_job), donde no se puede distinguir el resultado exacto. Ambos
// grupos cuentan como "terminado" para el contador N/N.
const TERMINAL_STATUSES = new Set(["done", "ok", "fail", "warn", "error", "timeout"]);

async function fetchSummary(runTs, safeName) {
  try {
    const res = await fetch(`/api/reports/${runTs}/${safeName}/summary`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function riskPills(counts) {
  if (!counts) return [];
  const order = [
    ["High", "high"],
    ["Medium", "medium"],
    ["Low", "low"],
    ["Informational", "info"],
  ];
  return order
    .filter(([key]) => counts[key])
    .map(([key, cls]) => el("span", { class: `risk-pill ${cls}`, text: `${key[0]}:${counts[key]}` }));
}

async function renderJobTargets(job, container) {
  container.innerHTML = "";
  const entries = Object.values(job.targets || {});
  if (entries.length === 0) {
    container.appendChild(el("p", { class: "empty", text: "Sin detalle de dominios (lote leído desde disco)." }));
    return;
  }

  for (const t of entries) {
    const statusCls = t.status || "pending";
    const right = el("div", { class: "target-right" }, [
      el("span", { class: `status-pill ${statusCls}`, text: STATUS_LABEL[statusCls] || statusCls }),
    ]);

    const row = el("div", { class: "target-row" }, [
      el("span", { class: "target-name", text: t.target || t.safe_name }),
      right,
    ]);
    container.appendChild(row);

    if (TERMINAL_STATUSES.has(t.status) && t.safe_name) {
      const summary = await fetchSummary(job.run_ts, t.safe_name);
      riskPills(summary && summary.counts).forEach((p) => right.insertBefore(p, right.firstChild));
    }
    if (t.html_report) {
      right.appendChild(el("a", { class: "report-link", href: t.html_report, target: "_blank", text: "informe" }));
    }
    if (t.log_file) {
      // El log se genera siempre, incluso cuando el escaneo falla antes
      // de producir un informe HTML/JSON (p. ej. "error" o "timeout").
      right.appendChild(el("a", { class: "report-link", href: t.log_file, target: "_blank", text: "log" }));
    }
  }
}

async function refreshJobs() {
  const res = await fetch("/api/jobs");
  const jobsData = await res.json();
  const list = $("#jobs-list");

  if (jobsData.length === 0) {
    list.innerHTML = "";
    list.appendChild(el("p", { class: "empty", text: "Todavía no se ha lanzado ningún lote." }));
    return;
  }

  list.innerHTML = "";
  jobsData.forEach((job) => {
    const entries = Object.values(job.targets || {});
    const done = entries.filter((t) => TERMINAL_STATUSES.has(t.status)).length;
    const total = entries.length || "?";

    const targetsEl = el("div", { class: "job-targets" });
    const head = el("div", { class: "job-head" }, [
      el("span", { text: job.run_ts }),
      el("span", { text: `${done}/${total}` }),
    ]);
    head.addEventListener("click", async () => {
      const nowOpen = !targetsEl.classList.contains("open");
      targetsEl.classList.toggle("open", nowOpen);
      if (nowOpen) await renderJobTargets(job, targetsEl);
    });

    list.appendChild(el("div", { class: "job-card" }, [head, targetsEl]));
  });
}

// ---------------------------------------------------------------- boot

(async function init() {
  await loadParams();
  await refreshJobs();
  setInterval(refreshJobs, 4000);
})();
