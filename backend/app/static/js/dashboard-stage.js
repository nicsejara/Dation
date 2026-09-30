(function () {
  "use strict";

  var STORAGE_KEY = (
    "dation.logistics.execution.v1"
  );

  var state = {
    context: null,
    pollTimer: null,
    pollAttempts: 0
  };

  function $(selector) {
    return document.querySelector(
      selector
    );
  }

  function escapeHtml(value) {
    return String(
      value == null ? "" : value
    )
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatNumber(
    value,
    digits
  ) {
    digits = (
      digits == null
        ? 0
        : digits
    );

    if (
      value === null
      || value === undefined
      || Number.isNaN(
        Number(value)
      )
    ) {
      return "—";
    }

    return new Intl.NumberFormat(
      "es-AR",
      {
        maximumFractionDigits: digits
      }
    ).format(
      Number(value)
    );
  }

  function formatCurrency(value) {
    if (
      value === null
      || value === undefined
      || Number.isNaN(
        Number(value)
      )
    ) {
      return "—";
    }

    return new Intl.NumberFormat(
      "es-AR",
      {
        style: "currency",
        currency: "ARS",
        maximumFractionDigits: 0
      }
    ).format(
      Number(value)
    );
  }

  function formatPercent(value) {
    if (
      value === null
      || value === undefined
      || Number.isNaN(
        Number(value)
      )
    ) {
      return "—";
    }

    var number = Number(value);
    var prefix = (
      number > 0 ? "+" : ""
    );

    return (
      prefix
      + number.toFixed(1)
      + "%"
    );
  }

  function shortId(value) {
    if (!value) {
      return "—";
    }

    return (
      String(value).slice(0, 8)
      + "…"
    );
  }

  function saveContext(context) {
    state.context = context;
    window.dationDashboardContext = context;

    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(context)
      );
    } catch (error) {
      // Session persistence is best effort.
    }
  }

  function loadContext() {
    try {
      var raw = sessionStorage.getItem(
        STORAGE_KEY
      );

      return raw
        ? JSON.parse(raw)
        : null;
    } catch (error) {
      return null;
    }
  }

  function runFromUrl() {
    try {
      return (
        new URLSearchParams(
          window.location.search
        ).get("run")
      );
    } catch (error) {
      return null;
    }
  }

  function setRunInUrl(runId) {
    if (!runId) {
      return;
    }

    var url = new URL(
      window.location.href
    );

    url.searchParams.set(
      "run",
      runId
    );

    window.history.replaceState(
      null,
      "",
      url.pathname
      + url.search
      + url.hash
    );
  }

  function clearPoll() {
    if (state.pollTimer) {
      window.clearTimeout(
        state.pollTimer
      );
      state.pollTimer = null;
    }
  }

  function schedulePoll(delay) {
    clearPoll();

    state.pollTimer = (
      window.setTimeout(
        pollCurrentRun,
        delay
      )
    );
  }

  function setExecutionButtons(
    options
  ) {
    options = options || {};

    var cancel = (
      $("#dashboard-cancel-wait")
    );
    var retryStatus = (
      $("#dashboard-retry-status")
    );
    var retryRun = (
      $("#dashboard-retry-run")
    );

    if (cancel) {
      cancel.classList.toggle(
        "is-hidden",
        !options.cancel
      );
    }

    if (retryStatus) {
      retryStatus.classList.toggle(
        "is-hidden",
        !options.retryStatus
      );
    }

    if (retryRun) {
      retryRun.classList.toggle(
        "is-hidden",
        !options.retryRun
      );
    }
  }

  function showExecutionState(
    mode,
    title,
    copy
  ) {
    var shell = (
      $("#dashboard-execution-state")
    );
    var content = (
      $("#dashboard-content")
    );
    var progress = (
      $("#dashboard-progress")
    );

    if (!shell || !content) {
      return;
    }

    shell.classList.remove(
      "is-hidden",
      "is-error",
      "is-timeout",
      "is-cancelled"
    );

    content.classList.add(
      "is-hidden"
    );

    if (mode && mode !== "running") {
      shell.classList.add(
        "is-" + mode
      );
    }

    var titleNode = (
      $("#dashboard-execution-title")
    );
    var copyNode = (
      $("#dashboard-execution-copy")
    );

    if (titleNode) {
      titleNode.textContent = title;
    }

    if (copyNode) {
      copyNode.textContent = copy;
    }

    if (progress) {
      progress.classList.toggle(
        "is-hidden",
        mode !== "running"
      );

      progress.setAttribute(
        "aria-valuetext",
        mode === "running"
          ? "Procesando"
          : title
      );
    }

    var runNode = (
      $("#dashboard-execution-run")
    );

    if (runNode) {
      runNode.textContent = (
        state.context
        && state.context.runId
          ? "Run " + shortId(
              state.context.runId
            )
          : "—"
      );
    }
  }

  function showRunning() {
    showExecutionState(
      "running",
      "Ejecutando decisión…",
      (
        "El motor está evaluando las "
        + "alternativas y persistiendo "
        + "la evidencia de la corrida."
      )
    );

    setExecutionButtons({
      cancel: true,
      retryStatus: false,
      retryRun: false
    });
  }

  function showError(message) {
    showExecutionState(
      "error",
      "No se pudo completar la decisión",
      message
      || (
        "La ejecución terminó con un error. "
        + "Podés verificar el estado persistido "
        + "o iniciar una nueva corrida."
      )
    );

    setExecutionButtons({
      cancel: false,
      retryStatus: Boolean(
        state.context
        && state.context.runId
      ),
      retryRun: true
    });
  }

  function showTimeout() {
    showExecutionState(
      "timeout",
      "La ejecución superó el tiempo de espera",
      (
        "La interfaz dejó de esperar la respuesta, "
        + "pero la corrida puede continuar en el backend. "
        + "Podés verificar su estado sin lanzar otra ejecución."
      )
    );

    setExecutionButtons({
      cancel: false,
      retryStatus: true,
      retryRun: true
    });
  }

  function showCancelled() {
    showExecutionState(
      "cancelled",
      "Espera detenida",
      (
        "Detuviste la espera en el navegador. "
        + "Esto no garantiza la cancelación del cálculo "
        + "en el backend porque el MVP todavía no expone "
        + "un endpoint de cancelación."
      )
    );

    setExecutionButtons({
      cancel: false,
      retryStatus: true,
      retryRun: true
    });
  }

  async function requestJson(url) {
    var response = await fetch(
      url,
      {
        credentials: "same-origin"
      }
    );

    var contentType = (
      response.headers.get(
        "content-type"
      )
      || ""
    );

    var payload = (
      contentType.includes(
        "application/json"
      )
        ? await response.json()
        : await response.text()
    );

    if (!response.ok) {
      var error = new Error(
        typeof payload === "object"
        && payload
          ? (
            payload.detail
            || JSON.stringify(payload)
          )
          : payload
      );

      error.status = response.status;
      throw error;
    }

    return payload;
  }

  async function recoverRun(run) {
    var context = (
      state.context || {}
    );

    var profile = context.profile;
    var dataset = context.dataset;

    if (!profile || !dataset) {
      var profilePayload = (
        await requestJson(
          "/api/datasets/"
          + encodeURIComponent(
              run.dataset_id
            )
          + "/profile"
        )
      );

      profile = profilePayload;
      dataset = profilePayload.dataset;
    }

    window.dationDashboardCompleted(
      run,
      dataset,
      profile
    );

    if (
      typeof window
        .dationConsumeDecisionRun
      === "function"
    ) {
      try {
        await window
          .dationConsumeDecisionRun(
            run,
            dataset,
            profile
          );
      } catch (error) {
        console.warn(
          "El Dashboard ya fue renderizado, pero falló una sincronización secundaria del workspace.",
          error
        );
      }

      return;
    }

    window.dispatchEvent(
      new CustomEvent(
        "dation:run-ready",
        {
          detail: {
            run: run,
            dataset: dataset,
            profile: profile
          }
        }
      )
    );
  }

  async function pollCurrentRun() {
    var context = state.context;

    if (
      !context
      || !context.runId
    ) {
      return;
    }

    state.pollAttempts += 1;

    try {
      var run = await requestJson(
        "/api/runs/"
        + encodeURIComponent(
            context.runId
          )
      );

      if (run.status === "completed") {
        clearPoll();
        await recoverRun(run);
        return;
      }

      if (run.status === "error") {
        clearPoll();

        saveContext(
          Object.assign(
            {},
            context,
            {
              status: "error"
            }
          )
        );

        showError(
          run.error_message
          || (
            "El motor registró un error "
            + "durante la ejecución."
          )
        );
        return;
      }

      showRunning();
      schedulePoll(1400);
    } catch (error) {
      if (
        error.status === 404
        && state.pollAttempts < 20
      ) {
        schedulePoll(900);
        return;
      }

      if (
        state.pollAttempts < 60
      ) {
        schedulePoll(1800);
        return;
      }

      showError(
        "No se pudo recuperar el estado "
        + "persistido de la corrida."
      );
    }
  }

  function formatDate(value) {
    if (!value) {
      return "—";
    }

    var parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
      return String(value);
    }

    return new Intl.DateTimeFormat(
      "es-AR",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }
    ).format(parsed);
  }

  function setText(id, value) {
    var node = document.getElementById(id);

    if (node) {
      node.textContent = value;
    }
  }

  function runConfiguration(run) {
    return (
      run.configuration_json
      || (
        run.result_json
        && run.result_json.configuration
      )
      || {
        mode: "preset",
        objective: "min_cost",
        weights: {
          cost: 1,
          trips: 0
        }
      }
    );
  }

  function modeLabel(config) {
    return (
      config.mode === "custom"
        ? "Personalizado"
        : "Predefinido"
    );
  }

  function weightLabel(config) {
    var weights = (
      config.weights || {}
    );

    return (
      "Costo "
      + Math.round(
        Number(weights.cost || 0)
        * 100
      )
      + "% · Viajes "
      + Math.round(
        Number(weights.trips || 0)
        * 100
      )
      + "%"
    );
  }

  function scenarioLabel(key) {
    if (key === "min_trips") {
      return "Viajes mínimos";
    }

    if (key === "custom") {
      return "Configuración personalizada";
    }

    if (key === "baseline") {
      return "Situación actual";
    }

    return "Costo mínimo";
  }

  function recommendationCopy(
    run,
    config
  ) {
    var result = run.result_json || {};
    var sensitivity = (
      result.sensitivity || {}
    );

    if (config.mode !== "custom") {
      return (
        "Resultado del motor para el objetivo "
        + scenarioLabel(
            result.recommended_scenario
          )
        + "."
      );
    }

    var base = (
      "Resultado de la configuración personalizada "
      + weightLabel(config)
      + "."
    );

    if (
      sensitivity.matches_scenario
      === "both_extremes"
    ) {
      return (
        base
        + " En este dataset la asignación coincide con los extremos "
        + "de costo mínimo y viajes mínimos; esto es un resultado de "
        + "sensibilidad, no un cambio del objetivo configurado."
      );
    }

    if (
      sensitivity.matches_scenario
      === "min_cost"
    ) {
      return (
        base
        + " La asignación coincide con el extremo de costo mínimo, "
        + "pero la decisión evaluada sigue siendo la configuración personalizada."
      );
    }

    if (
      sensitivity.matches_scenario
      === "min_trips"
    ) {
      return (
        base
        + " La asignación coincide con el extremo de viajes mínimos, "
        + "pero la decisión evaluada sigue siendo la configuración personalizada."
      );
    }

    return (
      base
      + " La asignación resultante es distinta de ambos extremos."
    );
  }

  function assignmentMap(scenario) {
    var map = new Map();

    (
      scenario
      && scenario.assignments
      || []
    ).forEach(function (item) {
      map.set(
        item.shipment_id,
        item
      );
    });

    return map;
  }

  function assignmentDifferenceCount(
    first,
    second
  ) {
    var firstMap = assignmentMap(first);
    var secondMap = assignmentMap(second);
    var ids = new Set(
      Array.from(firstMap.keys())
        .concat(
          Array.from(secondMap.keys())
        )
    );

    var count = 0;

    ids.forEach(function (id) {
      var firstItem = firstMap.get(id);
      var secondItem = secondMap.get(id);

      if (
        (
          firstItem
          && firstItem.vehicle_type
        )
        !== (
          secondItem
          && secondItem.vehicle_type
        )
      ) {
        count += 1;
      }
    });

    return count;
  }

  function renderCoreContext(
    profilePayload
  ) {
    var container = (
      $("#dashboard-data-context")
    );

    if (!container) {
      return;
    }

    var profile = (
      profilePayload
      && profilePayload.profile
    );

    if (!profile) {
      container.innerHTML = (
        '<div class="context-metric">'
        + "<span>Perfil</span>"
        + "<strong>No disponible</strong>"
        + "</div>"
      );
      return;
    }

    var range = (
      profile.dispatch_date_range
      || {}
    );

    var metrics = [
      ["Despachos", profile.shipments],
      ["Unidades", profile.total_units],
      [
        "Peso",
        formatNumber(
          profile.total_weight_kg
        ) + " kg"
      ],
      ["Orígenes", profile.origins],
      ["Destinos", profile.destinations],
      [
        "Vehículos",
        profile.vehicle_types
      ],
      [
        "Distancia media",
        formatNumber(
          profile.average_distance_km,
          1
        ) + " km"
      ],
      [
        "Ventana",
        (
          range.from
          && range.to
            ? (
              range.from
              + " → "
              + range.to
            )
            : "—"
        )
      ]
    ];

    container.innerHTML = (
      metrics.map(function (item) {
        return (
          '<div class="context-metric">'
          + "<span>"
          + escapeHtml(item[0])
          + "</span>"
          + "<strong>"
          + escapeHtml(
              formatNumber(item[1])
              === "—"
                ? item[1]
                : item[1]
            )
          + "</strong>"
          + "</div>"
        );
      }).join("")
    );
  }

  function renderCoreDrivers(result) {
    var container = (
      $("#dashboard-driver-list")
    );

    if (!container) {
      return;
    }

    var baseline = (
      result.scenarios
      && result.scenarios.baseline
    );

    var selected = (
      result.scenarios
      && result.scenarios[
        result.recommended_scenario
      ]
    );

    var baseMap = assignmentMap(
      baseline
    );

    var changes = (
      selected
      && selected.assignments
      || []
    )
      .map(function (item) {
        var base = baseMap.get(
          item.shipment_id
        );

        if (!base) {
          return null;
        }

        return {
          shipment_id: item.shipment_id,
          origin: item.origin,
          destination: item.destination,
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
          )
        };
      })
      .filter(Boolean)
      .filter(function (item) {
        return (
          item.baselineVehicle
            !== item.selectedVehicle
          || item.costDelta !== 0
          || item.tripsDelta !== 0
        );
      })
      .sort(function (a, b) {
        return (
          Math.abs(b.costDelta)
          - Math.abs(a.costDelta)
        );
      })
      .slice(0, 7);

    if (!changes.length) {
      container.innerHTML = (
        '<div class="empty-state empty-state--compact">'
        + "La configuración no genera cambios materiales de asignación frente a la situación actual."
        + "</div>"
      );
      return;
    }

    container.innerHTML = (
      changes.map(function (item) {
        return (
          '<div class="driver-item">'
          + "<div><strong>"
          + escapeHtml(item.shipment_id)
          + "</strong><small>"
          + escapeHtml(item.origin)
          + " → "
          + escapeHtml(item.destination)
          + "</small></div>"
          + '<div class="driver-change">'
          + escapeHtml(
              item.baselineVehicle
            )
          + " → <strong>"
          + escapeHtml(
              item.selectedVehicle
            )
          + "</strong></div>"
          + '<div class="driver-change">'
          + "Viajes: "
          + (
            item.tripsDelta > 0
              ? "+"
              : ""
          )
          + formatNumber(
              item.tripsDelta
            )
          + "</div>"
          + '<div class="driver-impact">'
          + "<small>Impacto estimado en costo</small>"
          + "<strong>"
          + formatCurrency(
              item.costDelta
            )
          + "</strong></div>"
          + "</div>"
        );
      }).join("")
    );
  }

  function renderCoreSensitivity(
    result,
    config
  ) {
    var baseline = (
      result.scenarios.baseline
    );
    var selected = (
      result.scenarios[
        result.recommended_scenario
      ]
    );
    var minCost = (
      result.scenarios.min_cost
    );
    var minTrips = (
      result.scenarios.min_trips
    );

    var baselineNode = (
      $("#baseline-strip")
    );

    if (baselineNode && baseline) {
      baselineNode.innerHTML = (
        '<div class="baseline-card">'
        + "<div><strong>Situación actual</strong>"
        + "<small>Asignación proveniente del CSV · referencia operativa</small></div>"
        + '<div class="baseline-metric"><span>Costo</span><strong>'
        + formatCurrency(
            baseline.metrics.total_cost
          )
        + "</strong></div>"
        + '<div class="baseline-metric"><span>Viajes</span><strong>'
        + formatNumber(
            baseline.metrics.total_trips
          )
        + "</strong></div>"
        + '<div class="baseline-metric"><span>Distancia</span><strong>'
        + formatNumber(
            baseline.metrics.total_distance_km
          )
        + " km</strong></div>"
        + "</div>"
      );
    }

    var cards = [
      {
        title: "Configuración elegida",
        weights: weightLabel(config),
        scenario: selected,
        selected: true,
        differences: 0
      },
      {
        title: "Extremo costo",
        weights: "Costo 100% · Viajes 0%",
        scenario: minCost,
        selected: false,
        differences: (
          assignmentDifferenceCount(
            selected,
            minCost
          )
        )
      },
      {
        title: "Extremo viajes",
        weights: "Costo 0% · Viajes 100%",
        scenario: minTrips,
        selected: false,
        differences: (
          assignmentDifferenceCount(
            selected,
            minTrips
          )
        )
      }
    ];

    var grid = $("#sensitivity-grid");

    if (grid) {
      grid.innerHTML = (
        cards
          .filter(function (card) {
            return Boolean(card.scenario);
          })
          .map(function (card) {
            var delta = (
              card.scenario
                .delta_vs_baseline
              || {}
            );

            return (
              '<article class="sensitivity-card '
              + (
                card.selected
                  ? "is-selected"
                  : ""
              )
              + '">'
              + '<span class="sensitivity-weight">'
              + escapeHtml(card.weights)
              + "</span>"
              + "<h3>"
              + escapeHtml(card.title)
              + "</h3>"
              + "<p>"
              + (
                card.selected
                  ? "Configuración utilizada en esta corrida."
                  : "Escenario extremo utilizado como referencia."
              )
              + "</p>"
              + '<div class="sensitivity-metrics">'
              + '<div class="sensitivity-metric"><span>Costo</span><strong>'
              + formatCurrency(
                  card.scenario
                    .metrics.total_cost
                )
              + "</strong></div>"
              + '<div class="sensitivity-metric"><span>Viajes</span><strong>'
              + formatNumber(
                  card.scenario
                    .metrics.total_trips
                )
              + "</strong></div>"
              + '<div class="sensitivity-metric"><span>Distancia</span><strong>'
              + formatNumber(
                  card.scenario
                    .metrics
                    .total_distance_km
                )
              + " km</strong></div>"
              + '<div class="sensitivity-metric"><span>Δ costo vs actual</span><strong>'
              + formatPercent(
                  delta.cost_pct
                )
              + "</strong></div>"
              + '<div class="sensitivity-metric"><span>Δ viajes vs actual</span><strong>'
              + formatPercent(
                  delta.trips_pct
                )
              + "</strong></div>"
              + '<div class="sensitivity-metric"><span>Asignaciones distintas</span><strong>'
              + formatNumber(
                  card.differences
                )
              + "</strong></div>"
              + "</div></article>"
            );
          }).join("")
      );
    }

    setText(
      "sensitivity-note",
      (
        result.sensitivity
        && result.sensitivity.message
      )
      || (
        "La corrida no contiene un resumen de sensibilidad."
      )
    );
  }

  function renderCoreDashboard(
    run,
    dataset,
    profile
  ) {
    var result = run.result_json;
    var selected = selectedScenario(run);
    var baseline = (
      result
      && result.scenarios
      && result.scenarios.baseline
    );

    if (
      !result
      || !selected
      || !baseline
    ) {
      throw new Error(
        "La corrida completada no contiene un DecisionResult válido."
      );
    }

    var config = runConfiguration(run);
    var metrics = selected.metrics || {};
    var delta = (
      selected.delta_vs_baseline
      || {}
    );

    setText(
      "run-context-dataset",
      (
        dataset
        && dataset.original_filename
      )
      || shortId(run.dataset_id)
    );
    setText(
      "run-context-date",
      formatDate(
        run.finished_at
        || run.created_at
      )
    );
    setText(
      "run-context-id",
      shortId(run.id)
    );
    setText(
      "run-context-engine",
      (
        run.engine_name
        || (
          result.engine
          && result.engine.name
        )
        || "—"
      )
      + " · v"
      + (
        run.engine_version
        || (
          result.engine
          && result.engine.version
        )
        || "—"
      )
    );
    setText(
      "run-context-mode",
      modeLabel(config)
    );
    setText(
      "run-context-weights",
      weightLabel(config)
    );

    setText(
      "dashboard-recommendation-title",
      scenarioLabel(
        result.recommended_scenario
      )
    );
    setText(
      "dashboard-recommendation-copy",
      recommendationCopy(
        run,
        config
      )
    );
    setText(
      "dashboard-recommendation-delta",
      formatPercent(delta.cost_pct)
    );

    setText(
      "dashboard-kpi-cost",
      formatCurrency(
        metrics.total_cost
      )
    );
    setText(
      "dashboard-kpi-cost-delta",
      (
        formatPercent(
          delta.cost_pct
        )
        + " vs situación actual · "
        + formatCurrency(
            baseline.metrics
              .total_cost
          )
      )
    );
    setText(
      "dashboard-kpi-trips",
      formatNumber(
        metrics.total_trips
      )
    );
    setText(
      "dashboard-kpi-trips-delta",
      (
        formatPercent(
          delta.trips_pct
        )
        + " vs situación actual · "
        + formatNumber(
            baseline.metrics
              .total_trips
          )
      )
    );
    setText(
      "dashboard-kpi-distance",
      (
        formatNumber(
          metrics.total_distance_km
        )
        + " km"
      )
    );
    setText(
      "dashboard-kpi-distance-delta",
      (
        formatPercent(
          delta.distance_pct
        )
        + " vs situación actual"
      )
    );
    setText(
      "dashboard-kpi-shipments",
      formatNumber(
        metrics.shipments
      )
    );
    setText(
      "dashboard-kpi-changes",
      (
        assignmentDifferenceCount(
          baseline,
          selected
        )
        + " despachos cambian de vehículo"
      )
    );

    renderCoreContext(profile);
    renderCoreDrivers(result);
    renderCoreSensitivity(
      result,
      config
    );

    var assumptions = (
      $("#assumptions-list")
    );

    if (assumptions) {
      assumptions.innerHTML = (
        (
          result.model_assumptions
          || []
        ).map(function (item) {
          return (
            "<li>"
            + escapeHtml(item)
            + "</li>"
          );
        }).join("")
      );
    }

    var download = $("#download-json");

    if (download) {
      download.disabled = false;
    }
  }

  function selectedScenario(run) {
    var result = (
      run && run.result_json
    );

    if (!result) {
      return null;
    }

    return (
      result.scenarios
      && result.scenarios[
        result.recommended_scenario
      ]
    );
  }

  function metricDefinitions() {
    return [
      {
        key: "total_cost",
        label: "Costo total",
        format: formatCurrency
      },
      {
        key: "total_trips",
        label: "Viajes",
        format: function (value) {
          return formatNumber(value);
        }
      },
      {
        key: "total_distance_km",
        label: "Distancia",
        format: function (value) {
          return (
            formatNumber(value)
            + " km"
          );
        }
      }
    ];
  }

  function improvementClass(
    selected,
    reference
  ) {
    if (
      selected === reference
      || reference === null
      || reference === undefined
    ) {
      return "is-neutral";
    }

    return (
      selected < reference
        ? "is-improvement"
        : "is-worse"
    );
  }

  function renderImpactChart(run) {
    var container = (
      $("#dashboard-impact-chart")
    );

    if (!container) {
      return;
    }

    var result = run.result_json;
    var selected = (
      selectedScenario(run)
    );
    var baseline = (
      result.scenarios.baseline
    );

    if (!selected || !baseline) {
      container.innerHTML = (
        '<div class="dashboard-chart-empty">'
        + "Sin datos para graficar."
        + "</div>"
      );
      return;
    }

    var rows = metricDefinitions()
      .map(function (metric) {
        var selectedValue = (
          Number(
            selected.metrics[
              metric.key
            ]
          )
        );

        var baselineValue = (
          Number(
            baseline.metrics[
              metric.key
            ]
          )
        );

        var maximum = Math.max(
          selectedValue,
          baselineValue,
          1
        );

        var selectedWidth = (
          selectedValue / maximum
        ) * 100;

        var baselineWidth = (
          baselineValue / maximum
        ) * 100;

        return (
          '<div class="impact-chart-row">'
          + '<div class="impact-chart-row__label">'
          + escapeHtml(metric.label)
          + "</div>"
          + '<div class="impact-chart-row__bars">'
          + '<div class="impact-chart-bar impact-chart-bar--baseline" '
          + 'style="width:'
          + baselineWidth.toFixed(1)
          + '%"><span>Actual</span></div>'
          + '<div class="impact-chart-bar impact-chart-bar--selected" '
          + 'style="width:'
          + selectedWidth.toFixed(1)
          + '%"><span>Decisión</span></div>'
          + "</div>"
          + '<div class="impact-chart-row__value">'
          + escapeHtml(
              metric.format(
                selectedValue
              )
            )
          + "</div>"
          + "</div>"
        );
      })
      .join("");

    container.innerHTML = rows;
  }

  function renderKpiTracks(run) {
    var selected = selectedScenario(run);
    var baseline = (
      run.result_json
      && run.result_json.scenarios
      && run.result_json.scenarios.baseline
    );

    if (!selected || !baseline) {
      return;
    }

    [
      {
        id: "dashboard-kpi-cost-track",
        key: "total_cost"
      },
      {
        id: "dashboard-kpi-trips-track",
        key: "total_trips"
      },
      {
        id: "dashboard-kpi-distance-track",
        key: "total_distance_km"
      }
    ].forEach(function (item) {
      var node = document.getElementById(
        item.id
      );

      if (!node) {
        return;
      }

      var selectedValue = Number(
        selected.metrics[item.key]
      );

      var baselineValue = Number(
        baseline.metrics[item.key]
      );

      var ratio = (
        baselineValue
          ? (
            selectedValue
            / baselineValue
          )
          : 1
      );

      var width = Math.max(
        4,
        Math.min(
          100,
          ratio * 100
        )
      );

      node.innerHTML = (
        '<span class="'
        + improvementClass(
            selectedValue,
            baselineValue
          )
        + '" style="width:'
        + width.toFixed(1)
        + '%"></span>'
      );
    });
  }

  function referenceOptions(
    result
  ) {
    var selectedKey = (
      result.recommended_scenario
    );

    var select = (
      $("#dashboard-comparison-select")
    );

    if (!select) {
      return;
    }

    Array.from(
      select.options
    ).forEach(function (option) {
      option.disabled = (
        option.value === selectedKey
      );
    });

    if (
      select.value === selectedKey
    ) {
      select.value = "baseline";
    }
  }

  function renderComparison(
    run,
    referenceKey
  ) {
    var result = run.result_json;
    var selected = selectedScenario(run);
    var reference = (
      result.scenarios[
        referenceKey
      ]
    );

    var tableBody = (
      $("#dashboard-comparison-table-body")
    );

    var chart = (
      $("#dashboard-comparison-chart")
    );

    if (
      !selected
      || !reference
      || !tableBody
      || !chart
    ) {
      return;
    }

    var definitions = (
      metricDefinitions()
    );

    tableBody.innerHTML = (
      definitions
        .map(function (metric) {
          var selectedValue = Number(
            selected.metrics[
              metric.key
            ]
          );

          var referenceValue = Number(
            reference.metrics[
              metric.key
            ]
          );

          var difference = (
            selectedValue
            - referenceValue
          );

          var variation = (
            referenceValue
              ? (
                difference
                / referenceValue
                * 100
              )
              : null
          );

          var klass = (
            improvementClass(
              selectedValue,
              referenceValue
            )
          );

          var differenceLabel = (
            metric.key === "total_cost"
              ? formatCurrency(
                  difference
                )
              : metric.key
                === "total_distance_km"
                ? (
                  formatNumber(
                    difference,
                    1
                  )
                  + " km"
                )
                : formatNumber(
                    difference
                  )
          );

          return (
            "<tr>"
            + "<th>"
            + escapeHtml(metric.label)
            + "</th>"
            + "<td>"
            + escapeHtml(
                metric.format(
                  selectedValue
                )
              )
            + "</td>"
            + "<td>"
            + escapeHtml(
                metric.format(
                  referenceValue
                )
              )
            + "</td>"
            + '<td class="'
            + klass
            + '">'
            + escapeHtml(
                differenceLabel
              )
            + "</td>"
            + '<td class="'
            + klass
            + '">'
            + (
              variation === null
                ? "—"
                : formatPercent(
                    variation
                  )
            )
            + "</td>"
            + "</tr>"
          );
        })
        .join("")
    );

    chart.innerHTML = (
      definitions
        .map(function (metric) {
          var selectedValue = Number(
            selected.metrics[
              metric.key
            ]
          );

          var referenceValue = Number(
            reference.metrics[
              metric.key
            ]
          );

          var selectedIndex = (
            referenceValue
              ? (
                selectedValue
                / referenceValue
                * 100
              )
              : 100
          );

          var displayWidth = Math.min(
            180,
            Math.max(
              2,
              selectedIndex
            )
          );

          return (
            '<div class="comparison-chart-row">'
            + "<span>"
            + escapeHtml(metric.label)
            + "</span>"
            + '<div class="comparison-chart-bars">'
            + '<div class="comparison-chart-reference" style="width:100%"></div>'
            + '<div class="comparison-chart-selected" style="width:'
            + displayWidth.toFixed(1)
            + '%"></div>'
            + "</div>"
            + "<strong>"
            + selectedIndex.toFixed(0)
            + "</strong>"
            + "</div>"
          );
        })
        .join("")
    );
  }

  function applyDeltaStyles(run) {
    var selected = selectedScenario(run);

    if (!selected) {
      return;
    }

    var delta = (
      selected.delta_vs_baseline
      || {}
    );

    [
      {
        id: "dashboard-kpi-cost-delta",
        value: delta.cost_pct
      },
      {
        id: "dashboard-kpi-trips-delta",
        value: delta.trips_pct
      },
      {
        id: "dashboard-kpi-distance-delta",
        value: delta.distance_pct
      },
      {
        id: "dashboard-recommendation-delta",
        value: delta.cost_pct
      }
    ].forEach(function (item) {
      var node = document.getElementById(
        item.id
      );

      if (!node) {
        return;
      }

      node.classList.remove(
        "is-improvement",
        "is-worse",
        "is-neutral"
      );

      var numeric = Number(
        item.value
      );

      if (Number.isNaN(numeric)) {
        node.classList.add(
          "is-neutral"
        );
      } else if (numeric < 0) {
        node.classList.add(
          "is-improvement"
        );
      } else if (numeric > 0) {
        node.classList.add(
          "is-worse"
        );
      } else {
        node.classList.add(
          "is-neutral"
        );
      }
    });
  }

  function renderEnhancedDashboard(run) {
    if (
      !run
      || !run.result_json
    ) {
      return;
    }

    referenceOptions(
      run.result_json
    );

    renderImpactChart(run);
    renderKpiTracks(run);
    applyDeltaStyles(run);

    var select = (
      $("#dashboard-comparison-select")
    );

    renderComparison(
      run,
      select
        ? select.value
        : "baseline"
    );
  }

  function bindComparison() {
    var select = (
      $("#dashboard-comparison-select")
    );

    if (!select) {
      return;
    }

    select.addEventListener(
      "change",
      function () {
        if (
          state.context
          && state.context.run
        ) {
          renderComparison(
            state.context.run,
            select.value
          );
        }
      }
    );
  }

  window.dationDashboardStart = function (
    context
  ) {
    var normalized = Object.assign(
      {},
      context,
      {
        status: "running"
      }
    );

    saveContext(normalized);
    setRunInUrl(normalized.runId);
    state.pollAttempts = 0;

    if (
      typeof window.dationNavigate
      === "function"
    ) {
      window.dationNavigate(
        "decision-dashboard"
      );
    }

    showRunning();
    schedulePoll(900);
  };

  window.dationDashboardCompleted = function (
    run,
    dataset,
    profile
  ) {
    clearPoll();

    var context = Object.assign(
      {},
      state.context || {},
      {
        runId: run.id,
        run: run,
        dataset: dataset,
        profile: profile,
        status: "completed",
        finishedAt: (
          run.finished_at
          || new Date().toISOString()
        )
      }
    );

    saveContext(context);
    setRunInUrl(run.id);
    updateLatestDecisionCta(run);

    var shell = (
      $("#dashboard-execution-state")
    );
    var content = (
      $("#dashboard-content")
    );

    if (shell) {
      shell.classList.add(
        "is-hidden"
      );
    }

    if (content) {
      content.classList.remove(
        "is-hidden"
      );
    }

    try {
      renderCoreDashboard(
        run,
        dataset,
        profile
      );

      renderEnhancedDashboard(run);

      window.dispatchEvent(
        new CustomEvent(
          "dation:dashboard-completed",
          {
            detail: {
              run: run,
              dataset: dataset,
              profile: profile,
              context: context
            }
          }
        )
      );
    } catch (error) {
      showError(
        "La corrida terminó correctamente, pero no se pudo renderizar el resultado: "
        + error.message
      );
    }
  };

  window.dationDashboardExecutionError = function (
    runId,
    message
  ) {
    if (
      state.context
      && runId
      && state.context.runId !== runId
    ) {
      return;
    }

    saveContext(
      Object.assign(
        {},
        state.context || {},
        {
          runId: runId,
          status: "error",
          error: message
        }
      )
    );

    showError(message);
  };

  window.dationDashboardTimeout = function (
    runId
  ) {
    if (
      state.context
      && runId
      && state.context.runId !== runId
    ) {
      return;
    }

    saveContext(
      Object.assign(
        {},
        state.context || {},
        {
          runId: runId,
          status: "timeout"
        }
      )
    );

    showTimeout();
    schedulePoll(2500);
  };

  function retryStatus() {
    if (
      !state.context
      || !state.context.runId
    ) {
      return;
    }

    state.pollAttempts = 0;
    showRunning();
    pollCurrentRun();
  }

  function retryRun() {
    if (
      !state.context
      || !state.context.configuration
      || typeof window
        .dationRetryDecision
        !== "function"
    ) {
      return;
    }

    window.dationRetryDecision(
      state.context.configuration
    );
  }

  function cancelWait() {
    clearPoll();

    if (
      typeof window
        .dationCancelDecisionWait
      === "function"
    ) {
      window.dationCancelDecisionWait();
    }

    saveContext(
      Object.assign(
        {},
        state.context || {},
        {
          status: "cancelled"
        }
      )
    );

    showCancelled();
  }

  async function restoreExecution() {
    var stored = loadContext();
    var urlRunId = runFromUrl();

    if (!stored && !urlRunId) {
      return;
    }

    if (!stored) {
      stored = {
        runId: urlRunId,
        status: "running"
      };
    }

    if (urlRunId) {
      stored = Object.assign(
        {},
        stored,
        {
          runId: urlRunId
        }
      );
    }

    saveContext(stored);

    if (
      typeof window.dationNavigate
      === "function"
    ) {
      window.dationNavigate(
        "decision-dashboard"
      );
    }

    if (
      stored.status === "completed"
      && stored.run
      && stored.run.id === stored.runId
    ) {
      window.dationDashboardCompleted(
        stored.run,
        stored.dataset,
        stored.profile
      );
      return;
    }

    /*
     * Siempre verificamos el run persistido si existe un run_id.
     * Esto permite recuperar una corrida aunque la sesión anterior
     * haya quedado en timeout, error visual o "espera detenida".
     */
    if (stored.runId) {
      showRunning();
      state.pollAttempts = 0;
      pollCurrentRun();
    }
  }

  function latestDecisionButton() {
    return $("#open-latest-logistics-decision");
  }

  function latestDecisionMeta() {
    return $("#latest-logistics-meta");
  }

  function updateLatestDecisionCta(
    run
  ) {
    var button = latestDecisionButton();
    var meta = latestDecisionMeta();

    if (!button || !meta) {
      return;
    }

    if (!run) {
      button.disabled = true;
      meta.textContent = (
        "Todavía no hay decisiones completadas para analizar."
      );

      if (
        typeof window
          .dationSetDashboardReady
        === "function"
      ) {
        window.dationSetDashboardReady(
          false
        );
      }

      return;
    }

    button.disabled = false;

    if (
      typeof window
        .dationSetDashboardReady
      === "function"
    ) {
      window.dationSetDashboardReady(
        true
      );
    }
    button.dataset.runId = run.id;
    meta.textContent = (
      "Última corrida completada · "
      + shortId(run.id)
      + " · "
      + formatDate(
          run.finished_at
          || run.created_at
        )
    );
  }

  async function findLatestCompletedRun() {
    var payload = await requestJson(
      "/api/runs?limit=30"
    );

    var items = (
      payload
      && Array.isArray(payload.items)
        ? payload.items
        : []
    );

    return (
      items.find(function (run) {
        return (
          run.status === "completed"
        );
      })
      || null
    );
  }

  async function refreshLatestDecisionCta() {
    try {
      var latest = await findLatestCompletedRun();
      updateLatestDecisionCta(latest);
      return latest;
    } catch (error) {
      var meta = latestDecisionMeta();

      if (meta) {
        meta.textContent = (
          "No se pudo consultar la última decisión."
        );
      }

      return null;
    }
  }

  async function openLatestDecision() {
    var button = latestDecisionButton();

    if (button) {
      button.disabled = true;
      button.textContent = "Abriendo última decisión…";
    }

    try {
      var latestSummary = (
        await findLatestCompletedRun()
      );

      if (!latestSummary) {
        updateLatestDecisionCta(null);
        return;
      }

      var latest = await requestJson(
        "/api/runs/"
        + encodeURIComponent(
            latestSummary.id
          )
      );

      saveContext({
        runId: latest.id,
        run: latest,
        status: "completed",
        finishedAt: (
          latest.finished_at
          || latest.created_at
        )
      });

      setRunInUrl(latest.id);

      if (
        typeof window.dationNavigate
        === "function"
      ) {
        window.dationNavigate(
          "decision-dashboard"
        );
      }

      await recoverRun(latest);
      updateLatestDecisionCta(latest);
    } catch (error) {
      showError(
        "No se pudo abrir la última decisión: "
        + error.message
      );
    } finally {
      if (button) {
        button.textContent = (
          "Analizar mi última decisión ↗"
        );
      }
    }
  }

  window.dationOpenLatestDecision = (
    openLatestDecision
  );

  function bindControls() {
    var retryStatusButton = (
      $("#dashboard-retry-status")
    );
    var retryRunButton = (
      $("#dashboard-retry-run")
    );
    var cancelButton = (
      $("#dashboard-cancel-wait")
    );

    if (retryStatusButton) {
      retryStatusButton.addEventListener(
        "click",
        retryStatus
      );
    }

    if (retryRunButton) {
      retryRunButton.addEventListener(
        "click",
        retryRun
      );
    }

    if (cancelButton) {
      cancelButton.addEventListener(
        "click",
        cancelWait
      );
    }

    var latestButton = latestDecisionButton();

    if (latestButton) {
      latestButton.addEventListener(
        "click",
        openLatestDecision
      );
    }

    bindComparison();
  }

  function boot() {
    bindControls();
    refreshLatestDecisionCta();
    restoreExecution();
  }

  if (
    document.readyState
    === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      {
        once: true
      }
    );
  } else {
    boot();
  }
})();