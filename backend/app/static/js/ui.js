import {
  normalizeRunConfiguration,
  state,
} from "./state.js";


export const $ = (
  selector
) => document.querySelector(selector);


export const $$ = (
  selector
) => Array.from(
  document.querySelectorAll(
    selector
  )
);


export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


export function formatNumber(
  value,
  maximumFractionDigits = 0,
) {
  if (
    value === null
    || value === undefined
    || Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "es-AR",
    {
      maximumFractionDigits,
    },
  ).format(Number(value));
}


export function formatCurrency(
  value
) {
  if (
    value === null
    || value === undefined
    || Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return new Intl.NumberFormat(
    "es-AR",
    {
      style: "currency",
      currency: "ARS",
      maximumFractionDigits: 0,
    },
  ).format(Number(value));
}


export function formatPercent(
  value
) {
  if (
    value === null
    || value === undefined
    || Number.isNaN(Number(value))
  ) {
    return "—";
  }

  const number = Number(value);

  return (
    `${number > 0 ? "+" : ""}`
    + `${number.toFixed(2)}%`
  );
}


export function formatDate(
  value
) {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);

  if (
    Number.isNaN(
      parsed.getTime()
    )
  ) {
    return String(value);
  }

  return new Intl.DateTimeFormat(
    "es-AR",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(parsed);
}


export function shortId(value) {
  if (!value) {
    return "—";
  }

  return (
    String(value).slice(0, 8)
    + "…"
  );
}


export function bytes(value) {
  const size = Number(value || 0);

  if (!size) {
    return "0 KB";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (
    size
    < 1024 * 1024
  ) {
    return (
      `${(size / 1024).toFixed(1)} KB`
    );
  }

  return (
    `${(
      size
      / (1024 * 1024)
    ).toFixed(1)} MB`
  );
}


export function toast(
  message,
  type = "default",
) {
  const element = $("#toast");

  element.textContent = message;
  element.className = "toast";

  if (type === "error") {
    element.classList.add(
      "is-error"
    );
  }

  requestAnimationFrame(
    () => element.classList.add(
      "is-visible"
    )
  );

  window.clearTimeout(
    toast.timer
  );

  toast.timer = window.setTimeout(
    () => {
      element.classList.remove(
        "is-visible"
      );
    },
    3600,
  );
}


export function showInlineStatus(
  element,
  message,
  type = "info",
) {
  element.textContent = message;
  element.className = (
    "inline-status"
  );

  if (type === "success") {
    element.classList.add(
      "is-success"
    );
  }

  if (type === "error") {
    element.classList.add(
      "is-error"
    );
  }

  if (type === "loading") {
    element.classList.add(
      "is-loading"
    );
  }
}


export function hideInlineStatus(
  element
) {
  element.className = (
    "inline-status is-hidden"
  );
  element.textContent = "";
}


const VIEW_BREADCRUMBS = {
  inicio: {
    primary: "Inicio",
    secondary: null,
  },
  "logistics-config": {
    primary: "DDA Logística",
    secondary: "Configuración",
  },
  "decision-dashboard": {
    primary: "DDA Logística",
    secondary: "Decisión",
  },
  traceability: {
    primary: "Trazabilidad",
    secondary: null,
  },
  settings: {
    primary: "Configuración",
    secondary: null,
  },
};


export function activateView(
  view
) {
  $$(".view").forEach(
    (panel) => {
      panel.classList.toggle(
        "is-active",
        panel.dataset.viewPanel
          === view,
      );
    }
  );

  $$(".nav-item[data-view]")
    .forEach(
      (button) => {
        const buttonView = (
          button.dataset.view
        );

        const active = (
          buttonView === view
          || (
            buttonView
              === "logistics-config"
            && view
              === "decision-dashboard"
          )
        );

        button.classList.toggle(
          "is-active",
          active,
        );
      }
    );

  const breadcrumb = (
    VIEW_BREADCRUMBS[view]
    || VIEW_BREADCRUMBS.inicio
  );

  $("#breadcrumb-primary")
    .textContent = (
      breadcrumb.primary
    );

  const secondary = (
    $("#breadcrumb-secondary")
  );
  const separator = (
    $(".breadcrumb-context-separator")
  );

  if (breadcrumb.secondary) {
    secondary.textContent = (
      breadcrumb.secondary
    );
    secondary.classList.remove(
      "is-hidden"
    );
    separator.classList.remove(
      "is-hidden"
    );
  } else {
    secondary.classList.add(
      "is-hidden"
    );
    separator.classList.add(
      "is-hidden"
    );
  }

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}


export function activateTraceTab(
  tab
) {
  $$(".trace-tab").forEach(
    (button) => {
      button.classList.toggle(
        "is-active",
        button.dataset.traceTab
          === tab,
      );
    }
  );

  $$(".trace-panel").forEach(
    (panel) => {
      panel.classList.toggle(
        "is-active",
        panel.dataset.tracePanel
          === tab,
      );
    }
  );
}


export function renderSystemStatus(
  supabaseOk,
  interpreter,
) {
  const element = (
    $("#system-status")
  );
  const dot = (
    element.querySelector(
      ".status-dot"
    )
  );

  if (
    supabaseOk
    && interpreter?.configured
  ) {
    dot.className = (
      "status-dot status-dot--live"
    );
    element.lastChild.textContent = (
      " Sistemas operativos"
    );
  } else if (supabaseOk) {
    dot.className = (
      "status-dot status-dot--pending"
    );
    element.lastChild.textContent = (
      " Core activo · IA pendiente"
    );
  } else {
    dot.className = (
      "status-dot status-dot--danger"
    );
    element.lastChild.textContent = (
      " Revisar servicios"
    );
  }

  $("#stat-ai").textContent = (
    interpreter?.configured
      ? "Disponible"
      : "Pendiente"
  );

  $("#stat-ai-detail").textContent = (
    interpreter?.configured
      ? (
        `${interpreter.provider}`
        + ` · ${interpreter.model}`
      )
      : "proveedor no configurado"
  );

  $("#settings-ai-status")
    .textContent = (
      interpreter?.configured
        ? "Disponible"
        : "No configurado"
    );

  $("#settings-ai-provider")
    .textContent = (
      interpreter?.provider
      || "—"
    );

  $("#settings-ai-model")
    .textContent = (
      interpreter?.model
      || "—"
    );

  $("#settings-ai-knowledge")
    .textContent = (
      interpreter?.knowledge_version
      || "—"
    );

  renderInterpreterMeta(
    interpreter
  );
}


export function renderHomeSummary(
  summary,
  runs,
) {
  $("#stat-datasets").textContent = (
    formatNumber(
      summary?.datasets ?? 0
    )
  );

  $("#stat-runs").textContent = (
    formatNumber(
      summary?.runs ?? 0
    )
  );

  const latest = (
    Array.isArray(runs)
    ? runs[0]
    : null
  );

  $("#latest-run-label")
    .textContent = (
      latest
        ? formatDate(
            latest.created_at
          )
        : "Sin ejecuciones"
    );
}


function translatedRunStatus(
  status
) {
  const value = String(
    status || ""
  ).toLowerCase();

  const labels = {
    completed: "Completada",
    running: "Procesando",
    queued: "En cola",
    error: "Error",
  };

  return (
    labels[value]
    || value
    || "Desconocido"
  );
}


function translatedDatasetStatus(
  status
) {
  const value = String(
    status || ""
  ).toLowerCase();

  const labels = {
    uploaded: "Validado",
    processing: "Procesando",
    processed: "Procesado",
    error: "Error",
  };

  return (
    labels[value]
    || value
    || "Desconocido"
  );
}


function statusBadge(
  status,
  kind = "run",
) {
  const value = String(
    status || ""
  ).toLowerCase();

  let modifier = "";

  if (
    value === "running"
    || value === "queued"
    || value === "processing"
  ) {
    modifier = (
      " status-badge--running"
    );
  }

  if (value === "error") {
    modifier = (
      " status-badge--error"
    );
  }

  const label = (
    kind === "dataset"
      ? translatedDatasetStatus(
          status
        )
      : translatedRunStatus(
          status
        )
  );

  return (
    `<span class="status-badge${modifier}">`
    + `${escapeHtml(label)}</span>`
  );
}


export function renderWorkspaceDatasets(
  datasets
) {
  const container = (
    $("#workspace-dataset-list")
  );

  if (!datasets.length) {
    container.innerHTML = (
      '<div class="empty-state empty-state--compact">'
      + "Todavía no hay datasets almacenados."
      + "</div>"
    );
    return;
  }

  container.innerHTML = (
    datasets
      .slice(0, 5)
      .map(
        (dataset) => {
          const active = (
            state.activeDataset?.id
            === dataset.id
          );

          return `
            <div class="dataset-row ${active ? "is-active" : ""}">
              <div class="dataset-row-icon">CSV</div>
              <div>
                <strong>${escapeHtml(dataset.original_filename)}</strong>
                <small>
                  ${formatNumber(dataset.row_count)} filas ·
                  ${formatNumber(dataset.column_count)} columnas ·
                  ${bytes(dataset.size_bytes)}
                </small>
              </div>
              <small>${formatDate(dataset.created_at)}</small>
              <button
                class="dataset-action"
                type="button"
                data-use-dataset="${escapeHtml(dataset.id)}"
              >
                ${active ? "Seleccionado" : "Usar dataset"}
              </button>
            </div>
          `;
        }
      )
      .join("")
  );
}


export function renderDatasetsTable(
  datasets
) {
  const body = (
    $("#datasets-table-body")
  );

  $("#datasets-count-label")
    .textContent = (
      `${datasets.length} dataset`
      + (
        datasets.length === 1
          ? ""
          : "s"
      )
      + " disponible"
      + (
        datasets.length === 1
          ? ""
          : "s"
      )
    );

  if (!datasets.length) {
    body.innerHTML = (
      '<tr><td colspan="8">'
      + "Todavía no hay datasets almacenados."
      + "</td></tr>"
    );
    return;
  }

  body.innerHTML = (
    datasets.map(
      (dataset) => `
        <tr>
          <td class="table-main">
            <strong>${escapeHtml(dataset.original_filename)}</strong>
            <small>${escapeHtml(dataset.id)}</small>
          </td>
          <td>${statusBadge(dataset.status, "dataset")}</td>
          <td>${formatNumber(dataset.row_count)}</td>
          <td>${formatNumber(dataset.column_count)}</td>
          <td>${bytes(dataset.size_bytes)}</td>
          <td><code>${escapeHtml((dataset.sha256 || "—").slice(0, 14))}${dataset.sha256 ? "…" : ""}</code></td>
          <td>${formatDate(dataset.created_at)}</td>
          <td>
            <button
              class="table-action"
              type="button"
              data-use-dataset="${escapeHtml(dataset.id)}"
            >
              Reutilizar
            </button>
          </td>
        </tr>
      `
    ).join("")
  );
}


function modeLabel(config) {
  return (
    config.mode === "custom"
      ? "Personalizado"
      : "Predefinido"
  );
}


function objectiveLabel(config) {
  if (
    config.objective
    === "min_trips"
  ) {
    return "Minimizar viajes";
  }

  if (
    config.objective
    === "custom"
  ) {
    return "Prioridades ponderadas";
  }

  return "Minimizar costo";
}


function weightLabel(config) {
  const cost = Math.round(
    Number(
      config.weights?.cost ?? 0
    ) * 100
  );
  const trips = Math.round(
    Number(
      config.weights?.trips ?? 0
    ) * 100
  );

  return (
    `Costo ${cost}% · `
    + `Viajes ${trips}%`
  );
}


export function renderRunsTable(
  runs,
  datasets,
) {
  const body = (
    $("#runs-table-body")
  );

  const datasetMap = new Map(
    datasets.map(
      (item) => [
        item.id,
        item,
      ]
    )
  );

  $("#runs-count-label")
    .textContent = (
      `${runs.length} corrida`
      + (
        runs.length === 1
          ? ""
          : "s"
      )
      + " reciente"
      + (
        runs.length === 1
          ? ""
          : "s"
      )
    );

  if (!runs.length) {
    body.innerHTML = (
      '<tr><td colspan="10">'
      + "Todavía no hay decisiones ejecutadas."
      + "</td></tr>"
    );
    return;
  }

  body.innerHTML = (
    runs.map(
      (run) => {
        const dataset = (
          datasetMap.get(
            run.dataset_id
          )
        );

        const config = (
          normalizeRunConfiguration(
            run
          )
        );

        return `
          <tr>
            <td class="table-main">
              <strong>${shortId(run.id)}</strong>
              <small>${escapeHtml(run.id)}</small>
            </td>
            <td>${escapeHtml(dataset?.original_filename || shortId(run.dataset_id))}</td>
            <td>${formatDate(run.created_at)}</td>
            <td>${modeLabel(config)}</td>
            <td>${objectiveLabel(config)}</td>
            <td>${weightLabel(config)}</td>
            <td>${statusBadge(run.status)}</td>
            <td>
              ${escapeHtml(run.engine_name || "—")}
              · v${escapeHtml(run.engine_version || "—")}
            </td>
            <td>
              ${run.duration_ms === null || run.duration_ms === undefined
                ? "—"
                : `${formatNumber(run.duration_ms)} ms`}
            </td>
            <td>
              <button
                class="table-action"
                type="button"
                data-open-run="${escapeHtml(run.id)}"
              >
                Abrir decisión
              </button>
            </td>
          </tr>
        `;
      }
    ).join("")
  );
}


export function renderActiveDataset(
  dataset
) {
  const card = (
    $("#active-dataset-card")
  );

  if (!dataset) {
    card.classList.add(
      "is-empty"
    );

    $("#active-dataset-name")
      .textContent = (
        "Ningún dataset seleccionado"
      );

    $("#active-dataset-meta")
      .textContent = (
        "Elegí un dataset existente "
        + "o cargá uno nuevo."
      );

    $("#active-dataset-status")
      .textContent = "—";

    $("#data-config-state")
      .innerHTML = (
        '<span class="status-dot status-dot--pending"></span>'
        + " Dataset pendiente"
      );

    $("#dataset-profile-panel")
      .classList.add(
        "is-hidden"
      );

    updateExecutionReadiness();
    return;
  }

  card.classList.remove(
    "is-empty"
  );

  $("#active-dataset-name")
    .textContent = (
      dataset.original_filename
    );

  $("#active-dataset-meta")
    .textContent = (
      `${formatNumber(dataset.row_count)} filas · `
      + `${formatNumber(dataset.column_count)} columnas · `
      + `${bytes(dataset.size_bytes)} · `
      + `${formatDate(dataset.created_at)}`
    );

  $("#active-dataset-status")
    .textContent = (
      translatedDatasetStatus(
        dataset.status
      )
    );

  $("#data-config-state")
    .innerHTML = (
      '<span class="status-dot status-dot--live"></span>'
      + " Dataset válido"
    );

  updateExecutionReadiness();
}


export function renderDatasetProfile(
  payload
) {
  const panel = (
    $("#dataset-profile-panel")
  );

  if (!payload) {
    panel.classList.add(
      "is-hidden"
    );
    return;
  }

  const dataset = payload.dataset;
  const validation = payload.validation;
  const profile = payload.profile;

  panel.classList.remove(
    "is-hidden"
  );

  $("#profile-dataset-title")
    .textContent = (
      dataset.original_filename
    );

  $("#profile-created")
    .textContent = (
      formatDate(
        dataset.created_at
      )
    );

  $("#profile-rows")
    .textContent = (
      formatNumber(
        validation.rows
      )
    );

  $("#profile-columns")
    .textContent = (
      formatNumber(
        validation.columns
      )
    );

  $("#profile-size")
    .textContent = (
      bytes(
        dataset.size_bytes
      )
    );

  $("#profile-schema")
    .textContent = (
      validation.schema
    );

  $("#profile-id")
    .textContent = (
      shortId(dataset.id)
    );

  $("#profile-shipments")
    .textContent = (
      formatNumber(
        profile.shipments
      )
    );

  $("#profile-units")
    .textContent = (
      formatNumber(
        profile.total_units
      )
    );

  $("#profile-weight")
    .textContent = (
      `${formatNumber(profile.total_weight_kg)} kg`
    );

  $("#profile-origins")
    .textContent = (
      formatNumber(
        profile.origins
      )
    );

  $("#profile-destinations")
    .textContent = (
      formatNumber(
        profile.destinations
      )
    );

  $("#profile-vehicles")
    .textContent = (
      formatNumber(
        profile.vehicle_types
      )
    );

  $("#profile-distance")
    .textContent = (
      `${formatNumber(profile.average_distance_km, 1)} km`
    );

  const dateRange = (
    profile.dispatch_date_range
  );

  $("#profile-date-range")
    .textContent = (
      dateRange?.from
      && dateRange?.to
        ? (
          `${dateRange.from} → `
          + `${dateRange.to}`
        )
        : "—"
    );

  $("#profile-hash")
    .textContent = (
      dataset.sha256 || "—"
    );

  const priorities = Object.entries(
    profile.priority_distribution
    || {}
  );

  $("#priority-distribution")
    .innerHTML = (
      priorities.length
        ? priorities
          .map(
            ([name, count]) => `
              <span class="priority-item">
                ${escapeHtml(name)}
                <strong>${formatNumber(count)}</strong>
              </span>
            `
          )
          .join("")
        : (
          '<span class="priority-item">'
          + "Sin datos de prioridad"
          + "</span>"
        )
    );

  renderPreview(
    payload.preview || []
  );
}


function renderPreview(rows) {
  const head = (
    $("#preview-table-head")
  );
  const body = (
    $("#preview-table-body")
  );

  if (!rows.length) {
    head.innerHTML = "";
    body.innerHTML = (
      '<tr><td>Sin registros para previsualizar.</td></tr>'
    );
    return;
  }

  const columns = Object.keys(
    rows[0]
  );

  head.innerHTML = (
    "<tr>"
    + columns
      .map(
        (column) => (
          `<th>${escapeHtml(column)}</th>`
        )
      )
      .join("")
    + "</tr>"
  );

  body.innerHTML = (
    rows.map(
      (row) => (
        "<tr>"
        + columns
          .map(
            (column) => (
              `<td>${escapeHtml(row[column])}</td>`
            )
          )
          .join("")
        + "</tr>"
      )
    ).join("")
  );
}


export function renderDecisionConfiguration() {
  $$(".decision-mode-card")
    .forEach(
      (card) => {
        const mode = (
          card.dataset.decisionMode
        );

        const objective = (
          card.dataset.objective
        );

        const selected = (
          mode === state.decisionMode
          && objective
            === state.objective
        );

        card.classList.toggle(
          "is-selected",
          selected,
        );
      }
    );

  const custom = (
    state.decisionMode
    === "custom"
  );

  $("#custom-sensitivity")
    .classList.toggle(
      "is-hidden",
      !custom,
    );

  $("#preset-sensitivity")
    .classList.toggle(
      "is-hidden",
      custom,
    );

  const costPercent = (
    Math.round(
      state.weights.cost * 100
    )
  );

  const tripsPercent = (
    100 - costPercent
  );

  $("#cost-weight-slider")
    .value = String(
      costPercent
    );

  $("#cost-weight-value")
    .textContent = (
      `${costPercent}%`
    );

  $("#trips-weight-value")
    .textContent = (
      `${tripsPercent}%`
    );

  $("#weight-bar-cost")
    .style.width = (
      `${costPercent}%`
    );

  $("#weight-bar-trips")
    .style.width = (
      `${tripsPercent}%`
    );

  $("#preset-weight-label")
    .textContent = (
      weightLabel({
        weights: state.weights,
      })
    );

  $("#sensitivity-config-copy")
    .textContent = (
      custom
        ? (
          "Ajustá la prioridad del costo. "
          + "Viajes se recalcula automáticamente "
          + "para mantener una suma de 100%."
        )
        : (
          "El modo predefinido seleccionado "
          + "utiliza una ponderación canónica."
        )
    );

  $("#weight-explanation")
    .textContent = (
      customWeightExplanation(
        costPercent,
        tripsPercent,
      )
    );

  updateExecutionReadiness();
}


function customWeightExplanation(
  cost,
  trips,
) {
  if (cost === 100) {
    return (
      "Esta configuración prioriza exclusivamente "
      + "el costo y reproduce el extremo de costo mínimo."
    );
  }

  if (trips === 100) {
    return (
      "Esta configuración prioriza exclusivamente "
      + "los viajes y reproduce el extremo de viajes mínimos."
    );
  }

  if (cost > trips) {
    return (
      "Esta configuración prioriza el ahorro económico, "
      + `manteniendo un ${trips}% de sensibilidad `
      + "sobre la cantidad de viajes."
    );
  }

  if (trips > cost) {
    return (
      "Esta configuración prioriza la reducción de viajes, "
      + `manteniendo un ${cost}% de sensibilidad `
      + "sobre el costo."
    );
  }

  return (
    "Esta configuración asigna el mismo peso "
    + "a costo y viajes."
  );
}


export function updateExecutionReadiness() {
  const button = (
    $("#run-decision")
  );

  const validDataset = Boolean(
    state.activeDataset
    && state.datasetProfile
  );

  const validWeights = (
    state.weights.cost >= 0
    && state.weights.cost <= 1
    && state.weights.trips >= 0
    && state.weights.trips <= 1
    && Math.abs(
      state.weights.cost
      + state.weights.trips
      - 1
    ) < 0.000001
  );

  const ready = (
    validDataset
    && validWeights
  );

  button.disabled = !ready;

  if (!validDataset) {
    $("#execution-summary-title")
      .textContent = (
        "Seleccioná un dataset para continuar"
      );

    $("#execution-summary-copy")
      .textContent = (
        "El motor permanecerá deshabilitado "
        + "hasta contar con datos válidos."
      );
    return;
  }

  if (!validWeights) {
    $("#execution-summary-title")
      .textContent = (
        "Revisá la ponderación"
      );

    $("#execution-summary-copy")
      .textContent = (
        "Los pesos deben estar entre 0 y 100% "
        + "y sumar exactamente 100%."
      );
    return;
  }

  $("#execution-summary-title")
    .textContent = (
      state.decisionMode
        === "custom"
        ? "Configuración personalizada lista"
        : objectiveLabel({
            objective: state.objective,
          })
    );

  $("#execution-summary-copy")
    .textContent = (
      `${state.activeDataset.original_filename} · `
      + weightLabel({
          weights: state.weights,
        })
      + " · cálculo determinístico"
    );
}


function scenarioLabel(key) {
  const labels = {
    baseline: "Situación actual",
    min_cost: "Costo mínimo",
    min_trips: "Viajes mínimos",
    custom: "Configuración elegida",
  };

  return (
    labels[key]
    || key
  );
}


function scenarioForRun(run) {
  const result = (
    run?.result_json
  );

  if (!result) {
    return null;
  }

  return (
    result.scenarios?.[
      result.recommended_scenario
    ]
    || null
  );
}


function indexAssignments(
  scenario
) {
  return new Map(
    (
      scenario?.assignments
      || []
    ).map(
      (item) => [
        item.shipment_id,
        item,
      ]
    )
  );
}


export function assignmentDifferenceCount(
  first,
  second,
) {
  const firstMap = (
    indexAssignments(first)
  );
  const secondMap = (
    indexAssignments(second)
  );

  const ids = new Set([
    ...firstMap.keys(),
    ...secondMap.keys(),
  ]);

  let count = 0;

  ids.forEach(
    (id) => {
      if (
        firstMap.get(id)?.vehicle_type
        !== secondMap.get(id)?.vehicle_type
      ) {
        count += 1;
      }
    }
  );

  return count;
}


function topAssignmentChanges(
  result,
  limit = 7,
) {
  const baseline = (
    result?.scenarios?.baseline
  );

  const selected = (
    result?.scenarios?.[
      result.recommended_scenario
    ]
  );

  const baseMap = (
    indexAssignments(baseline)
  );

  return (
    selected?.assignments
    || []
  )
    .map(
      (item) => {
        const base = (
          baseMap.get(
            item.shipment_id
          )
        );

        if (!base) {
          return null;
        }

        return {
          shipment_id: (
            item.shipment_id
          ),
          origin: item.origin,
          destination: (
            item.destination
          ),
          baselineVehicle: (
            base.vehicle_type
          ),
          selectedVehicle: (
            item.vehicle_type
          ),
          costDelta: (
            Number(item.total_cost)
            - Number(base.total_cost)
          ),
          tripsDelta: (
            Number(item.required_trips)
            - Number(base.required_trips)
          ),
        };
      }
    )
    .filter(Boolean)
    .filter(
      (item) => (
        item.baselineVehicle
          !== item.selectedVehicle
        || item.costDelta !== 0
        || item.tripsDelta !== 0
      )
    )
    .sort(
      (a, b) => (
        Math.abs(b.costDelta)
        - Math.abs(a.costDelta)
      )
    )
    .slice(0, limit);
}


export function renderDashboard(
  run,
  profilePayload,
) {
  const result = (
    run?.result_json
  );

  if (!result) {
    return;
  }

  const config = (
    normalizeRunConfiguration(
      run
    )
  );

  const selectedKey = (
    result.recommended_scenario
  );

  const selected = (
    scenarioForRun(run)
  );

  const baseline = (
    result.scenarios.baseline
  );

  const metrics = (
    selected.metrics
  );

  const delta = (
    selected.delta_vs_baseline
    || {}
  );

  $("#run-context-dataset")
    .textContent = (
      state.activeDataset
        ?.original_filename
      || shortId(run.dataset_id)
    );

  $("#run-context-date")
    .textContent = (
      formatDate(
        run.finished_at
        || run.created_at
      )
    );

  $("#run-context-id")
    .textContent = (
      shortId(run.id)
    );

  $("#run-context-engine")
    .textContent = (
      `${run.engine_name || result.engine?.name || "—"}`
      + ` · v${run.engine_version || result.engine?.version || "—"}`
    );

  $("#run-context-mode")
    .textContent = (
      modeLabel(config)
    );

  $("#run-context-weights")
    .textContent = (
      weightLabel(config)
    );

  $("#dashboard-recommendation-title")
    .textContent = (
      scenarioLabel(selectedKey)
    );

  $("#dashboard-recommendation-copy")
    .textContent = (
      config.mode === "custom"
        ? (
          "Resultado del modelo para "
          + weightLabel(config)
          + "."
        )
        : (
          "Resultado del modelo para "
          + objectiveLabel(config)
          + "."
        )
    );

  $("#dashboard-recommendation-delta")
    .textContent = (
      formatPercent(
        delta.cost_pct
      )
    );

  $("#dashboard-kpi-cost")
    .textContent = (
      formatCurrency(
        metrics.total_cost
      )
    );

  $("#dashboard-kpi-cost-delta")
    .textContent = (
      `${formatPercent(delta.cost_pct)} vs situación actual · `
      + formatCurrency(
          baseline.metrics.total_cost
        )
    );

  $("#dashboard-kpi-trips")
    .textContent = (
      formatNumber(
        metrics.total_trips
      )
    );

  $("#dashboard-kpi-trips-delta")
    .textContent = (
      `${formatPercent(delta.trips_pct)} vs situación actual · `
      + formatNumber(
          baseline.metrics.total_trips
        )
    );

  $("#dashboard-kpi-distance")
    .textContent = (
      `${formatNumber(metrics.total_distance_km)} km`
    );

  $("#dashboard-kpi-distance-delta")
    .textContent = (
      `${formatPercent(delta.distance_pct)} vs situación actual`
    );

  $("#dashboard-kpi-shipments")
    .textContent = (
      formatNumber(
        metrics.shipments
      )
    );

  $("#dashboard-kpi-changes")
    .textContent = (
      `${assignmentDifferenceCount(baseline, selected)} `
      + "despachos cambian de vehículo"
    );

  renderDashboardDataContext(
    profilePayload
  );

  renderSensitivity(
    result,
    config,
  );

  renderDrivers(result);

  $("#assumptions-list")
    .innerHTML = (
      (
        result.model_assumptions
        || []
      )
        .map(
          (item) => (
            `<li>${escapeHtml(item)}</li>`
          )
        )
        .join("")
    );

  renderTechnicalEvidence(
    run
  );

  $("#download-json")
    .disabled = false;

  $("#export-decision")
    .disabled = !state.explanation;
}


function renderDashboardDataContext(
  payload
) {
  const container = (
    $("#dashboard-data-context")
  );

  if (!payload?.profile) {
    container.innerHTML = (
      '<div class="context-metric">'
      + "<span>Perfil</span>"
      + "<strong>No disponible</strong>"
      + "</div>"
    );
    return;
  }

  const p = payload.profile;
  const range = (
    p.dispatch_date_range
  );

  const metrics = [
    [
      "Despachos",
      formatNumber(p.shipments),
    ],
    [
      "Unidades",
      formatNumber(p.total_units),
    ],
    [
      "Peso",
      `${formatNumber(p.total_weight_kg)} kg`,
    ],
    [
      "Orígenes",
      formatNumber(p.origins),
    ],
    [
      "Destinos",
      formatNumber(p.destinations),
    ],
    [
      "Vehículos",
      formatNumber(p.vehicle_types),
    ],
    [
      "Distancia media",
      `${formatNumber(p.average_distance_km, 1)} km`,
    ],
    [
      "Ventana",
      (
        range?.from
        && range?.to
          ? `${range.from} → ${range.to}`
          : "—"
      ),
    ],
  ];

  container.innerHTML = (
    metrics.map(
      ([label, value]) => `
        <div class="context-metric">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `
    ).join("")
  );
}


function renderSensitivity(
  result,
  config,
) {
  const baseline = (
    result.scenarios.baseline
  );
  const minCost = (
    result.scenarios.min_cost
  );
  const minTrips = (
    result.scenarios.min_trips
  );
  const selected = (
    result.scenarios[
      result.recommended_scenario
    ]
  );

  $("#baseline-strip")
    .innerHTML = `
      <div class="baseline-card">
        <div>
          <strong>Situación actual</strong>
          <small>Asignación proveniente del CSV · referencia operativa</small>
        </div>
        <div class="baseline-metric">
          <span>Costo</span>
          <strong>${formatCurrency(baseline.metrics.total_cost)}</strong>
        </div>
        <div class="baseline-metric">
          <span>Viajes</span>
          <strong>${formatNumber(baseline.metrics.total_trips)}</strong>
        </div>
        <div class="baseline-metric">
          <span>Distancia</span>
          <strong>${formatNumber(baseline.metrics.total_distance_km)} km</strong>
        </div>
      </div>
    `;

  const selectedWeights = (
    weightLabel(config)
  );

  const selectedTitle = (
    config.mode === "custom"
      ? "Configuración elegida"
      : objectiveLabel(config)
  );

  const cards = [
    {
      key: "selected",
      title: selectedTitle,
      weights: selectedWeights,
      scenario: selected,
      selected: true,
      differences: 0,
    },
    {
      key: "min_cost",
      title: "Extremo costo",
      weights: "Costo 100% · Viajes 0%",
      scenario: minCost,
      selected: false,
      differences: (
        assignmentDifferenceCount(
          selected,
          minCost,
        )
      ),
    },
    {
      key: "min_trips",
      title: "Extremo viajes",
      weights: "Costo 0% · Viajes 100%",
      scenario: minTrips,
      selected: false,
      differences: (
        assignmentDifferenceCount(
          selected,
          minTrips,
        )
      ),
    },
  ];

  $("#sensitivity-grid")
    .innerHTML = (
      cards.map(
        (card) => {
          const d = (
            card.scenario
              .delta_vs_baseline
            || {}
          );

          return `
            <article class="sensitivity-card ${card.selected ? "is-selected" : ""}">
              <span class="sensitivity-weight">${escapeHtml(card.weights)}</span>
              <h3>${escapeHtml(card.title)}</h3>
              <p>
                ${card.selected
                  ? "Configuración utilizada en esta corrida."
                  : "Escenario extremo utilizado como referencia de sensibilidad."}
              </p>
              <div class="sensitivity-metrics">
                <div class="sensitivity-metric">
                  <span>Costo</span>
                  <strong>${formatCurrency(card.scenario.metrics.total_cost)}</strong>
                </div>
                <div class="sensitivity-metric">
                  <span>Viajes</span>
                  <strong>${formatNumber(card.scenario.metrics.total_trips)}</strong>
                </div>
                <div class="sensitivity-metric">
                  <span>Distancia</span>
                  <strong>${formatNumber(card.scenario.metrics.total_distance_km)} km</strong>
                </div>
                <div class="sensitivity-metric">
                  <span>Δ costo vs actual</span>
                  <strong>${formatPercent(d.cost_pct)}</strong>
                </div>
                <div class="sensitivity-metric">
                  <span>Δ viajes vs actual</span>
                  <strong>${formatPercent(d.trips_pct)}</strong>
                </div>
                <div class="sensitivity-metric">
                  <span>Asignaciones distintas</span>
                  <strong>${formatNumber(card.differences)}</strong>
                </div>
              </div>
            </article>
          `;
        }
      ).join("")
    );

  const sensitivity = (
    result.sensitivity
  );

  $("#sensitivity-note")
    .textContent = (
      sensitivity?.message
      || (
        "La corrida histórica no contiene "
        + "metadatos de sensibilidad de engine 0.2."
      )
    );
}


function renderDrivers(result) {
  const container = (
    $("#dashboard-driver-list")
  );
  const changes = (
    topAssignmentChanges(
      result
    )
  );

  if (!changes.length) {
    container.innerHTML = (
      '<div class="empty-state empty-state--compact">'
      + "La configuración no genera cambios materiales de asignación frente a la situación actual."
      + "</div>"
    );
    return;
  }

  container.innerHTML = (
    changes.map(
      (item) => `
        <div class="driver-item">
          <div>
            <strong>${escapeHtml(item.shipment_id)}</strong>
            <small>${escapeHtml(item.origin)} → ${escapeHtml(item.destination)}</small>
          </div>
          <div class="driver-change">
            ${escapeHtml(item.baselineVehicle)}
            →
            <strong>${escapeHtml(item.selectedVehicle)}</strong>
          </div>
          <div class="driver-change">
            Viajes:
            ${item.tripsDelta > 0 ? "+" : ""}
            ${formatNumber(item.tripsDelta)}
          </div>
          <div class="driver-impact">
            <small>Impacto estimado en costo</small>
            <strong>${formatCurrency(item.costDelta)}</strong>
          </div>
        </div>
      `
    ).join("")
  );
}


export function renderInterpreterMeta(
  interpreter
) {
  const meta = (
    $("#ai-dashboard-meta")
  );
  const generate = (
    $("#generate-explanation")
  );
  const ask = (
    $("#ask-decision")
  );

  if (!interpreter?.configured) {
    meta.textContent = (
      "Intérprete IA no configurado"
    );
    generate.disabled = true;
    ask.disabled = true;
    return;
  }

  meta.textContent = (
    `${interpreter.provider} · `
    + `${interpreter.model} · `
    + `Knowledge ${interpreter.knowledge_version}`
  );

  generate.disabled = (
    !state.activeRun
  );

  ask.disabled = (
    !state.activeRun
  );
}


function listHtml(items) {
  const values = (
    Array.isArray(items)
      ? items
      : []
  );

  if (!values.length) {
    return (
      "<p>No se identificaron elementos "
      + "materiales para esta sección.</p>"
    );
  }

  return (
    "<ul>"
    + values
      .map(
        (item) => (
          `<li>${escapeHtml(item)}</li>`
        )
      )
      .join("")
    + "</ul>"
  );
}


export function renderExplanation(
  explanation
) {
  if (!explanation) {
    $("#executive-insight")
      .classList.add(
        "is-hidden"
      );

    $("#export-decision")
      .disabled = true;

    return;
  }

  const container = (
    $("#executive-insight")
  );

  container.innerHTML = `
    <div class="insight-hero">
      <span class="section-kicker">Resumen ejecutivo</span>
      <h3>${escapeHtml(explanation.recommendation)}</h3>
      <p>${escapeHtml(explanation.executive_summary)}</p>
    </div>
    <div class="insight-grid">
      <div class="insight-column">
        <div class="insight-section">
          <h4>Por qué aparece esta recomendación</h4>
          <p>${escapeHtml(explanation.why_recommended)}</p>
        </div>
        <div class="insight-section">
          <h4>Principales drivers</h4>
          ${listHtml(explanation.key_drivers)}
        </div>
        <div class="insight-section">
          <h4>Trade-offs</h4>
          ${listHtml(explanation.tradeoffs)}
        </div>
      </div>
      <div class="insight-column">
        <div class="insight-section">
          <h4>Impacto de negocio</h4>
          <div class="insight-impact">
            <div>
              <span>Costo</span>
              <strong>${escapeHtml(explanation.business_impact?.cost)}</strong>
            </div>
            <div>
              <span>Viajes</span>
              <strong>${escapeHtml(explanation.business_impact?.trips)}</strong>
            </div>
            <div>
              <span>Distancia</span>
              <strong>${escapeHtml(explanation.business_impact?.distance)}</strong>
            </div>
          </div>
        </div>
        <div class="insight-section">
          <h4>Supuestos</h4>
          ${listHtml(explanation.assumptions)}
        </div>
        <div class="insight-section">
          <h4>Limitaciones</h4>
          ${listHtml(explanation.caveats)}
        </div>
      </div>
    </div>
  `;

  container.classList.remove(
    "is-hidden"
  );

  $("#export-decision")
    .disabled = false;
}


export function resetChat(
  messages = []
) {
  const thread = (
    $("#chat-thread")
  );

  thread.innerHTML = "";

  if (!messages.length) {
    appendChatMessage(
      "assistant",
      "Esta conversación está anclada a la corrida activa. Podés preguntar por drivers, sensibilidad, trade-offs y supuestos."
    );
    return;
  }

  messages.forEach(
    (message) => {
      appendChatMessage(
        message.role,
        message.content,
      );
    }
  );
}


export function appendChatMessage(
  role,
  content,
) {
  const thread = (
    $("#chat-thread")
  );

  const wrapper = (
    document.createElement(
      "div"
    )
  );

  if (role === "user") {
    wrapper.className = (
      "user-message"
    );

    wrapper.innerHTML = `
      <div>
        <p>${escapeHtml(content)}</p>
      </div>
    `;
  } else {
    wrapper.className = (
      "assistant-message"
    );

    wrapper.innerHTML = `
      <div class="message-avatar">D</div>
      <div>
        <strong>Dation Interpreter</strong>
        <p>${escapeHtml(content)}</p>
      </div>
    `;
  }

  thread.appendChild(
    wrapper
  );

  thread.scrollTop = (
    thread.scrollHeight
  );
}


export function renderTechnicalEvidence(
  run
) {
  const empty = (
    $("#evidence-empty")
  );
  const content = (
    $("#evidence-content")
  );

  if (!run) {
    empty.classList.remove(
      "is-hidden"
    );
    content.classList.add(
      "is-hidden"
    );
    return;
  }

  empty.classList.add(
    "is-hidden"
  );
  content.classList.remove(
    "is-hidden"
  );

  $("#trace-dataset-id")
    .textContent = (
      run.dataset_id || "—"
    );

  $("#trace-run-id")
    .textContent = (
      run.id || "—"
    );

  $("#trace-engine")
    .textContent = (
      run.engine_name
      || run.result_json?.engine?.name
      || "—"
    );

  $("#trace-engine-version")
    .textContent = (
      run.engine_version
      || run.result_json?.engine?.version
      || "—"
    );

  $("#trace-duration")
    .textContent = (
      run.duration_ms === null
      || run.duration_ms === undefined
        ? "—"
        : `${formatNumber(run.duration_ms)} ms`
    );

  $("#trace-status")
    .textContent = (
      translatedRunStatus(
        run.status
      )
    );

  $("#configuration-json")
    .textContent = (
      JSON.stringify(
        normalizeRunConfiguration(
          run
        ),
        null,
        2,
      )
    );

  $("#assumptions-json")
    .textContent = (
      JSON.stringify(
        run.result_json
          ?.model_assumptions
        || [],
        null,
        2,
      )
    );

  $("#raw-run-json")
    .textContent = (
      JSON.stringify(
        run.result_json || {},
        null,
        2,
      )
    );
}


export function buildDecisionMarkdown(
  run,
  dataset,
  profilePayload,
  explanation,
) {
  const config = (
    normalizeRunConfiguration(
      run
    )
  );

  const result = (
    run.result_json || {}
  );

  const selected = (
    result.scenarios?.[
      result.recommended_scenario
    ]
  );

  const baseline = (
    result.scenarios?.baseline
  );

  const sensitivity = (
    result.sensitivity || {}
  );

  const lines = [
    "# Dation — Decisión logística",
    "",
    `- Fecha: ${formatDate(run.finished_at || run.created_at)}`,
    `- Dataset: ${dataset?.original_filename || run.dataset_id}`,
    `- Run ID: ${run.id}`,
    `- Motor: ${run.engine_name || result.engine?.name || "—"} v${run.engine_version || result.engine?.version || "—"}`,
    `- Modo: ${modeLabel(config)}`,
    `- Objetivo: ${objectiveLabel(config)}`,
    `- Ponderación: ${weightLabel(config)}`,
    "",
    "## Recomendación del modelo",
    "",
    `Escenario recomendado para la configuración seleccionada: **${scenarioLabel(result.recommended_scenario)}**.`,
    "",
    `- Costo total: ${formatCurrency(selected?.metrics?.total_cost)}`,
    `- Viajes: ${formatNumber(selected?.metrics?.total_trips)}`,
    `- Distancia: ${formatNumber(selected?.metrics?.total_distance_km)} km`,
    `- Δ costo vs situación actual: ${formatPercent(selected?.delta_vs_baseline?.cost_pct)}`,
    `- Δ viajes vs situación actual: ${formatPercent(selected?.delta_vs_baseline?.trips_pct)}`,
    "",
    "## Situación actual",
    "",
    `- Costo: ${formatCurrency(baseline?.metrics?.total_cost)}`,
    `- Viajes: ${formatNumber(baseline?.metrics?.total_trips)}`,
    `- Distancia: ${formatNumber(baseline?.metrics?.total_distance_km)} km`,
    "",
    "## Sensibilidad",
    "",
    sensitivity.message || "La corrida no contiene un resumen de sensibilidad.",
    "",
  ];

  if (profilePayload?.profile) {
    const p = (
      profilePayload.profile
    );

    lines.push(
      "## Contexto de los datos",
      "",
      `- Despachos: ${formatNumber(p.shipments)}`,
      `- Unidades: ${formatNumber(p.total_units)}`,
      `- Peso total: ${formatNumber(p.total_weight_kg)} kg`,
      `- Orígenes: ${formatNumber(p.origins)}`,
      `- Destinos: ${formatNumber(p.destinations)}`,
      `- Tipos de vehículo: ${formatNumber(p.vehicle_types)}`,
      "",
    );
  }

  lines.push(
    "## Resumen ejecutivo IA",
    "",
    explanation
      ? explanation.executive_summary
      : "No generado.",
    "",
    "## Supuestos y limitaciones",
    "",
  );

  (
    result.model_assumptions || []
  ).forEach(
    (item) => {
      lines.push(
        `- ${item}`
      );
    }
  );

  return (
    lines.join("\n")
  );
}
