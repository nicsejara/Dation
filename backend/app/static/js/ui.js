import { state } from "./state.js";

export const $ = (selector) => document.querySelector(selector);
export const $$ = (selector) => Array.from(document.querySelectorAll(selector));

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatNumber(value, maximumFractionDigits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat("es-AR", {
    maximumFractionDigits,
  }).format(Number(value));
}

export function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }

  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number.toFixed(2)}%`;
}

export function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("es-AR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function shortId(value) {
  if (!value) return "—";
  return `${String(value).slice(0, 8)}…`;
}

export function bytes(value) {
  const size = Number(value || 0);
  if (!size) return "0 KB";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function toast(message, type = "default") {
  const element = $("#toast");
  element.textContent = message;
  element.className = "toast";
  if (type === "error") element.classList.add("is-error");

  requestAnimationFrame(() => element.classList.add("is-visible"));

  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    element.classList.remove("is-visible");
  }, 3400);
}

export function showInlineStatus(element, message, type = "info") {
  element.textContent = message;
  element.className = "inline-status";

  if (type === "success") element.classList.add("is-success");
  if (type === "error") element.classList.add("is-error");
}

export function hideInlineStatus(element) {
  element.className = "inline-status is-hidden";
  element.textContent = "";
}

const VIEW_TITLES = {
  overview: ["Overview", "Logistics DDA"],
  workspace: ["Decision Workspace", "Logistics DDA"],
  datasets: ["Datasets", "Data library"],
  history: ["Decision History", "Run ledger"],
  settings: ["Settings", "System status"],
};

export function activateView(view) {
  $$(".view").forEach((panel) => {
    panel.classList.toggle(
      "is-active",
      panel.dataset.viewPanel === view
    );
  });

  $$(".nav-item[data-view]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });

  const [primary, secondary] = VIEW_TITLES[view] || VIEW_TITLES.overview;
  $("#breadcrumb-primary").textContent = primary;
  $("#breadcrumb-secondary").textContent = secondary;

  window.scrollTo({ top: 0, behavior: "smooth" });
}

export function renderSystemStatus(supabaseOk, interpreter) {
  const element = $("#system-status");
  const dot = element.querySelector(".status-dot");

  if (supabaseOk && interpreter?.configured) {
    dot.className = "status-dot status-dot--live";
    element.lastChild.textContent = " Systems operational";
  } else if (supabaseOk) {
    dot.className = "status-dot status-dot--pending";
    element.lastChild.textContent = " Core online · AI pending";
  } else {
    dot.className = "status-dot status-dot--danger";
    element.lastChild.textContent = " Service check required";
  }

  $("#stat-ai").textContent = interpreter?.configured ? "Ready" : "Setup";
  $("#stat-ai-detail").textContent = interpreter?.configured
    ? `${interpreter.provider} · ${interpreter.model}`
    : "provider not configured";

  $("#settings-ai-status").textContent = interpreter?.configured ? "Ready" : "Not configured";
  $("#settings-ai-provider").textContent = interpreter?.provider || "—";
  $("#settings-ai-model").textContent = interpreter?.model || "—";
  $("#settings-ai-knowledge").textContent = interpreter?.knowledge_version || "—";
}

export function renderOverviewStats(summary) {
  $("#stat-datasets").textContent = formatNumber(summary?.datasets ?? 0);
  $("#stat-runs").textContent = formatNumber(summary?.runs ?? 0);
}

function runStatusBadge(status) {
  const normalized = String(status || "").toLowerCase();
  let modifier = "";

  if (normalized === "running" || normalized === "queued") {
    modifier = " status-badge--running";
  } else if (normalized === "error") {
    modifier = " status-badge--error";
  }

  return `<span class="status-badge${modifier}">${escapeHtml(normalized || "unknown")}</span>`;
}

function datasetStatusBadge(status) {
  const normalized = String(status || "").toLowerCase();

  if (normalized === "error") {
    return '<span class="status-badge status-badge--error">error</span>';
  }

  if (normalized === "processing") {
    return '<span class="status-badge status-badge--running">processing</span>';
  }

  return `<span class="status-badge">${escapeHtml(normalized || "uploaded")}</span>`;
}

export function renderOverviewRecentRuns(runs, datasets) {
  const container = $("#overview-recent-runs");
  const datasetMap = new Map(datasets.map((item) => [item.id, item]));

  if (!runs.length) {
    container.innerHTML = '<div class="empty-state empty-state--compact">No decision runs yet.</div>';
    return;
  }

  container.innerHTML = runs.slice(0, 5).map((run) => {
    const dataset = datasetMap.get(run.dataset_id);
    const objective = run.configuration_json?.objective === "min_trips"
      ? "Minimize trips"
      : "Minimize cost";

    return `
      <div class="activity-item">
        <div class="activity-icon">R</div>
        <div>
          <strong>${escapeHtml(objective)}</strong>
          <small>${escapeHtml(dataset?.original_filename || shortId(run.dataset_id))} · ${formatDate(run.created_at)}</small>
        </div>
        ${runStatusBadge(run.status)}
      </div>
    `;
  }).join("");
}

export function renderWorkspaceDatasetList(datasets) {
  const container = $("#workspace-dataset-list");

  if (!datasets.length) {
    container.innerHTML = '<div class="empty-state empty-state--compact">No datasets available yet.</div>';
    return;
  }

  container.innerHTML = datasets.slice(0, 5).map((dataset) => {
    const active = state.activeDataset?.id === dataset.id;

    return `
      <div class="dataset-row ${active ? "is-active" : ""}">
        <div class="dataset-row-icon">CSV</div>
        <div>
          <strong>${escapeHtml(dataset.original_filename)}</strong>
          <small>${formatNumber(dataset.row_count)} rows · ${formatNumber(dataset.column_count)} columns · ${bytes(dataset.size_bytes)}</small>
        </div>
        <small>${formatDate(dataset.created_at)}</small>
        <button class="dataset-action" type="button" data-use-dataset="${escapeHtml(dataset.id)}">
          ${active ? "Selected" : "Use dataset"}
        </button>
      </div>
    `;
  }).join("");
}

export function renderDatasetsTable(datasets) {
  const body = $("#datasets-table-body");
  $("#datasets-count-label").textContent = `${datasets.length} dataset${datasets.length === 1 ? "" : "s"} available`;

  if (!datasets.length) {
    body.innerHTML = '<tr><td colspan="6">No datasets stored yet.</td></tr>';
    return;
  }

  body.innerHTML = datasets.map((dataset) => `
    <tr>
      <td class="table-main">
        <strong>${escapeHtml(dataset.original_filename)}</strong>
        <small>${escapeHtml(dataset.id)}</small>
      </td>
      <td>${datasetStatusBadge(dataset.status)}</td>
      <td>${formatNumber(dataset.row_count)}</td>
      <td>${formatNumber(dataset.column_count)}</td>
      <td>${formatDate(dataset.created_at)}</td>
      <td>
        <button class="table-action" type="button" data-use-dataset="${escapeHtml(dataset.id)}">
          Use in workspace
        </button>
      </td>
    </tr>
  `).join("");
}

export function renderRunsTable(runs, datasets) {
  const body = $("#runs-table-body");
  const datasetMap = new Map(datasets.map((item) => [item.id, item]));
  $("#runs-count-label").textContent = `${runs.length} recent run${runs.length === 1 ? "" : "s"}`;

  if (!runs.length) {
    body.innerHTML = '<tr><td colspan="8">No decision runs yet.</td></tr>';
    return;
  }

  body.innerHTML = runs.map((run) => {
    const dataset = datasetMap.get(run.dataset_id);
    const objective = run.configuration_json?.objective === "min_trips"
      ? "Minimize trips"
      : "Minimize cost";

    return `
      <tr>
        <td class="table-main">
          <strong>${shortId(run.id)}</strong>
          <small>${escapeHtml(run.id)}</small>
        </td>
        <td>${escapeHtml(dataset?.original_filename || shortId(run.dataset_id))}</td>
        <td>${objective}</td>
        <td>${runStatusBadge(run.status)}</td>
        <td>${escapeHtml(run.engine_name || "—")} · v${escapeHtml(run.engine_version || "—")}</td>
        <td>${run.duration_ms === null || run.duration_ms === undefined ? "—" : `${formatNumber(run.duration_ms)} ms`}</td>
        <td>${formatDate(run.created_at)}</td>
        <td>
          <button class="table-action" type="button" data-open-run="${escapeHtml(run.id)}">
            Open
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

export function renderActiveDataset(dataset) {
  const card = $("#active-dataset-card");
  const decisionStage = $("#stage-decision");
  const button = $("#run-decision");

  if (!dataset) {
    card.classList.add("is-empty");
    $("#active-dataset-name").textContent = "No dataset selected";
    $("#active-dataset-meta").textContent = "Select an existing dataset or upload a new file.";
    $("#active-dataset-status").textContent = "—";

    $("#data-stage-state").innerHTML =
      '<span class="status-dot status-dot--pending"></span> Waiting for dataset';

    decisionStage.classList.add("stage--locked");
    decisionStage.classList.remove("stage--ready");
    $("#decision-stage-state").innerHTML =
      '<span class="status-dot status-dot--muted"></span> Select a dataset first';

    $("#run-ready-title").textContent = "Dataset required";
    $("#run-ready-copy").textContent = "Select a dataset before executing the decision engine.";
    button.disabled = true;
    return;
  }

  card.classList.remove("is-empty");
  $("#active-dataset-name").textContent = dataset.original_filename;
  $("#active-dataset-meta").textContent =
    `${formatNumber(dataset.row_count)} rows · ${formatNumber(dataset.column_count)} columns · ${bytes(dataset.size_bytes)} · uploaded ${formatDate(dataset.created_at)}`;
  $("#active-dataset-status").textContent = dataset.status || "uploaded";

  $("#data-stage-state").innerHTML =
    '<span class="status-dot status-dot--live"></span> Dataset ready';

  decisionStage.classList.remove("stage--locked");
  decisionStage.classList.add("stage--ready");

  $("#decision-stage-state").innerHTML =
    '<span class="status-dot status-dot--live"></span> Ready to run';

  $("#run-ready-title").textContent = "Decision engine ready";
  $("#run-ready-copy").textContent =
    `The run will use ${dataset.original_filename} as immutable source evidence.`;

  button.disabled = false;
}

export function renderObjective(objective) {
  $$("#objective-selector .choice-card").forEach((card) => {
    card.classList.toggle(
      "is-selected",
      card.dataset.objective === objective
    );
  });
}

function scenarioName(key, scenario) {
  if (key === "baseline") return "Current baseline";
  if (key === "min_cost") return "Minimum total cost";
  if (key === "min_trips") return "Minimum trips";
  return scenario?.name || key;
}

function getRecommended(result) {
  return result?.scenarios?.[result.recommended_scenario] || null;
}

function topAssignmentChanges(result, limit = 5) {
  const baseline = result?.scenarios?.baseline?.assignments || [];
  const recommended = getRecommended(result)?.assignments || [];

  const baseMap = new Map(baseline.map((item) => [item.shipment_id, item]));

  return recommended
    .map((item) => {
      const base = baseMap.get(item.shipment_id);
      if (!base) return null;

      const costDelta = Number(item.total_cost) - Number(base.total_cost);
      const tripsDelta = Number(item.required_trips) - Number(base.required_trips);

      return {
        shipment_id: item.shipment_id,
        origin: item.origin,
        destination: item.destination,
        baselineVehicle: base.vehicle_type,
        recommendedVehicle: item.vehicle_type,
        costDelta,
        tripsDelta,
      };
    })
    .filter(Boolean)
    .filter((item) =>
      item.baselineVehicle !== item.recommendedVehicle ||
      item.costDelta !== 0 ||
      item.tripsDelta !== 0
    )
    .sort((a, b) => Math.abs(b.costDelta) - Math.abs(a.costDelta))
    .slice(0, limit);
}

export function renderRun(run) {
  const result = run?.result_json;

  if (!result) return;

  const recommendedKey = result.recommended_scenario;
  const recommended = getRecommended(result);
  const baseline = result.scenarios.baseline;
  const metrics = recommended.metrics;
  const delta = recommended.delta_vs_baseline || {};

  $("#stage-results").classList.remove("stage--locked");
  $("#stage-results").classList.add("stage--complete");
  $("#result-stage-state").innerHTML =
    '<span class="status-dot status-dot--live"></span> Decision calculated';

  $("#result-empty").classList.add("is-hidden");
  $("#result-content").classList.remove("is-hidden");

  $("#recommendation-title").textContent =
    scenarioName(recommendedKey, recommended);

  $("#recommendation-subtitle").textContent =
    recommendedKey === "min_cost"
      ? "Selected because this run prioritizes total estimated cost."
      : "Selected because this run prioritizes the fewest required trips.";

  $("#recommendation-delta").textContent = formatPercent(delta.cost_pct);

  $("#kpi-cost").textContent = formatCurrency(metrics.total_cost);
  $("#kpi-cost-delta").textContent =
    `${formatPercent(delta.cost_pct)} vs baseline ${formatCurrency(baseline.metrics.total_cost)}`;

  $("#kpi-trips").textContent = formatNumber(metrics.total_trips);
  $("#kpi-trips-delta").textContent =
    `${formatPercent(delta.trips_pct)} vs baseline ${formatNumber(baseline.metrics.total_trips)}`;

  $("#kpi-distance").textContent =
    `${formatNumber(metrics.total_distance_km)} km`;
  $("#kpi-distance-delta").textContent =
    `${formatPercent(delta.distance_pct)} vs baseline`;

  $("#kpi-shipments").textContent = formatNumber(metrics.shipments);

  const scenarioOrder = ["baseline", "min_cost", "min_trips"];
  $("#scenario-table-body").innerHTML = scenarioOrder.map((key) => {
    const scenario = result.scenarios[key];
    const d = scenario.delta_vs_baseline || {};
    const recommendedRow = key === recommendedKey;

    return `
      <tr class="${recommendedRow ? "is-recommended" : ""}">
        <td>
          <div class="scenario-name">
            ${escapeHtml(scenarioName(key, scenario))}
            ${recommendedRow ? '<span class="mini-badge">recommended</span>' : ""}
          </div>
        </td>
        <td>${formatCurrency(scenario.metrics.total_cost)}</td>
        <td>${formatNumber(scenario.metrics.total_trips)}</td>
        <td>${formatNumber(scenario.metrics.total_distance_km)} km</td>
        <td class="${Number(d.cost_pct || 0) < 0 ? "metric-positive" : Number(d.cost_pct || 0) > 0 ? "metric-negative" : ""}">
          ${formatPercent(d.cost_pct)}
        </td>
        <td class="${Number(d.trips_pct || 0) < 0 ? "metric-positive" : Number(d.trips_pct || 0) > 0 ? "metric-negative" : ""}">
          ${formatPercent(d.trips_pct)}
        </td>
      </tr>
    `;
  }).join("");

  const changes = topAssignmentChanges(result);
  $("#driver-list").innerHTML = changes.length
    ? changes.map((item) => `
        <div class="driver-item">
          <div>
            <strong>${escapeHtml(item.shipment_id)}</strong>
            <small>${escapeHtml(item.origin)} → ${escapeHtml(item.destination)}</small>
          </div>
          <div class="driver-change">
            ${escapeHtml(item.baselineVehicle)} → <strong>${escapeHtml(item.recommendedVehicle)}</strong>
          </div>
          <div class="driver-change">
            Trips: ${item.tripsDelta > 0 ? "+" : ""}${formatNumber(item.tripsDelta)}
          </div>
          <div class="driver-impact">
            <small>Estimated cost impact</small>
            <strong>${formatCurrency(item.costDelta)}</strong>
          </div>
        </div>
      `).join("")
    : '<div class="empty-state empty-state--compact">No material assignment changes versus baseline.</div>';

  $("#stage-understand").classList.remove("stage--locked");
  $("#stage-understand").classList.add("stage--ready");
  $("#ai-stage-state").innerHTML =
    '<span class="status-dot status-dot--live"></span> Ready to interpret';
  $("#ai-empty").classList.add("is-hidden");
  $("#ai-content").classList.remove("is-hidden");

  $("#stage-trace").classList.remove("stage--locked");
  $("#stage-trace").classList.add("stage--complete");
  $("#trace-stage-state").innerHTML =
    '<span class="status-dot status-dot--live"></span> Evidence available';
  $("#trace-empty").classList.add("is-hidden");
  $("#trace-content").classList.remove("is-hidden");

  $("#trace-dataset-id").textContent = run.dataset_id;
  $("#trace-run-id").textContent = run.id;
  $("#trace-engine").textContent = run.engine_name || result.engine?.name || "—";
  $("#trace-engine-version").textContent = run.engine_version || result.engine?.version || "—";
  $("#trace-duration").textContent =
    run.duration_ms === null || run.duration_ms === undefined
      ? "—"
      : `${formatNumber(run.duration_ms)} ms`;
  $("#trace-status").textContent = run.status || "—";
  $("#raw-run-json").textContent = JSON.stringify(run, null, 2);

  updateWorkflowFromState();
}

function list(items) {
  const values = Array.isArray(items) ? items : [];
  if (!values.length) return '<p>No material items identified for this section.</p>';

  return `<ul>${values.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

export function renderExplanation(payload) {
  const e = payload?.explanation;
  if (!e) return;

  const container = $("#executive-insight");
  container.innerHTML = `
    <div class="insight-hero">
      <span class="section-kicker">Executive insight</span>
      <h3>${escapeHtml(e.recommendation)}</h3>
      <p>${escapeHtml(e.executive_summary)}</p>
    </div>
    <div class="insight-grid">
      <div class="insight-column">
        <div class="insight-section">
          <h4>Why this scenario</h4>
          <p>${escapeHtml(e.why_recommended)}</p>
        </div>
        <div class="insight-section">
          <h4>Key drivers</h4>
          ${list(e.key_drivers)}
        </div>
        <div class="insight-section">
          <h4>Trade-offs</h4>
          ${list(e.tradeoffs)}
        </div>
      </div>
      <div class="insight-column">
        <div class="insight-section">
          <h4>Business impact</h4>
          <div class="insight-impact">
            <div><span>Cost</span><strong>${escapeHtml(e.business_impact?.cost)}</strong></div>
            <div><span>Trips</span><strong>${escapeHtml(e.business_impact?.trips)}</strong></div>
            <div><span>Distance</span><strong>${escapeHtml(e.business_impact?.distance)}</strong></div>
          </div>
        </div>
        <div class="insight-section">
          <h4>Assumptions</h4>
          ${list(e.assumptions)}
        </div>
        <div class="insight-section">
          <h4>Limits to keep in mind</h4>
          ${list(e.caveats)}
        </div>
      </div>
    </div>
  `;

  container.classList.remove("is-hidden");
}

export function renderInterpreterMeta(interpreter) {
  const meta = $("#ai-meta");
  const provider = $("#ai-provider");
  const button = $("#generate-explanation");
  const ask = $("#ask-decision");

  if (!interpreter?.configured) {
    provider.textContent = "Decision Interpreter unavailable";
    meta.textContent = "LLM_API_KEY is not configured.";
    button.disabled = true;
    ask.disabled = true;
    return;
  }

  provider.textContent = "Dation Decision Interpreter";
  meta.textContent =
    `${interpreter.provider} · ${interpreter.model} · Knowledge ${interpreter.knowledge_version}`;

  button.disabled = !state.activeRun;
  ask.disabled = !state.activeRun;
}

export function appendChatMessage(role, content) {
  const thread = $("#chat-thread");
  const wrapper = document.createElement("div");

  if (role === "user") {
    wrapper.className = "user-message";
    wrapper.innerHTML = `
      <div><p>${escapeHtml(content)}</p></div>
    `;
  } else {
    wrapper.className = "assistant-message";
    wrapper.innerHTML = `
      <div class="message-avatar">D</div>
      <div>
        <strong>Dation Interpreter</strong>
        <p>${escapeHtml(content)}</p>
      </div>
    `;
  }

  thread.appendChild(wrapper);
  thread.scrollTop = thread.scrollHeight;
}

export function clearRunPresentation() {
  $("#stage-results").classList.add("stage--locked");
  $("#stage-results").classList.remove("stage--complete");
  $("#result-stage-state").innerHTML =
    '<span class="status-dot status-dot--muted"></span> No run yet';
  $("#result-empty").classList.remove("is-hidden");
  $("#result-content").classList.add("is-hidden");

  $("#stage-understand").classList.add("stage--locked");
  $("#stage-understand").classList.remove("stage--ready");
  $("#ai-stage-state").innerHTML =
    '<span class="status-dot status-dot--muted"></span> Waiting for result';
  $("#ai-empty").classList.remove("is-hidden");
  $("#ai-content").classList.add("is-hidden");
  $("#executive-insight").classList.add("is-hidden");

  $("#stage-trace").classList.add("stage--locked");
  $("#stage-trace").classList.remove("stage--complete");
  $("#trace-stage-state").innerHTML =
    '<span class="status-dot status-dot--muted"></span> No run selected';
  $("#trace-empty").classList.remove("is-hidden");
  $("#trace-content").classList.add("is-hidden");

  updateWorkflowFromState();
}

export function updateWorkflowFromState() {
  const steps = $$(".workflow-step");

  steps.forEach((step, index) => {
    step.classList.remove("is-active", "is-complete");

    const number = index + 1;
    let complete = false;
    let active = false;

    if (number === 1) {
      complete = Boolean(state.activeDataset);
      active = !state.activeDataset;
    } else if (number === 2) {
      complete = Boolean(state.activeRun);
      active = Boolean(state.activeDataset) && !state.activeRun;
    } else if (number === 3) {
      complete = Boolean(state.activeRun);
      active = false;
    } else if (number === 4) {
      complete = Boolean(state.activeRun);
      active = false;
    } else if (number === 5) {
      complete = Boolean(state.activeRun);
      active = false;
    }

    if (complete) step.classList.add("is-complete");
    if (active) step.classList.add("is-active");
  });
}
