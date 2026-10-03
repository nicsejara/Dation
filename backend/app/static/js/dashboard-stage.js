(function () {
  "use strict";

  var F = (
    window.DationDashboardFormatters
  );

  var S = (
    window.DationDashboardSelectors
  );

  if (!F || !S) {
    console.error(
      "Dation Dashboard no pudo iniciar: faltan formatters o selectors."
    );
    return;
  }

  var STORAGE_KEY = (
    "dation.logistics.execution.v1"
  );

  var state = {
    context: null,
    pollTimer: null,
    pollAttempts: 0,
    detailRows: [],
    detailPage: 1,
    detailPageSize: 12
  };

  function $(selector) {
    return document.querySelector(
      selector
    );
  }

  function $$(selector) {
    return Array.from(
      document.querySelectorAll(
        selector
      )
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

  function setText(id, value) {
    var node = document.getElementById(
      id
    );

    if (node) {
      node.textContent = (
        value == null
          ? "—"
          : String(value)
      );
    }
  }

  function saveContext(context) {
    state.context = context;
    window.dationDashboardContext = (
      context
    );

    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(context)
      );
    } catch (error) {
      // Persistencia best effort.
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
          : (
            payload
            || response.statusText
          )
      );

      error.status = response.status;
      throw error;
    }

    return payload;
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

    if (
      mode
      && mode !== "running"
    ) {
      shell.classList.add(
        "is-" + mode
      );
    }

    setText(
      "dashboard-execution-title",
      title
    );

    setText(
      "dashboard-execution-copy",
      copy
    );

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

    setText(
      "dashboard-execution-run",
      (
        state.context
        && state.context.runId
          ? (
            "Corrida en proceso"
          )
          : "—"
      )
    );
  }

  function showRunning() {
    showExecutionState(
      "running",
      "Ejecutando decisión…",
      (
        "El motor está evaluando alternativas "
        + "de asignación y persistiendo la corrida."
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
      (
        message
        || (
          "La ejecución terminó con un error. "
          + "Podés verificar el estado o reintentar."
        )
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
        "La interfaz dejó de esperar, pero la corrida "
        + "puede seguir procesándose en el backend."
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
        "La espera del navegador fue detenida. "
        + "La corrida puede seguir en el backend."
      )
    );

    setExecutionButtons({
      cancel: false,
      retryStatus: true,
      retryRun: true
    });
  }

  function showDashboard() {
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
  }

  function runConfiguration(run) {
    return (
      run
      && (
        run.configuration_json
        || (
          run.result_json
          && run.result_json
            .configuration
        )
      )
    )
    || {
      mode: "preset",
      objective: "min_cost",
      weights: {
        cost: 1,
        trips: 0
      }
    };
  }

  function percentageImpact(
    value,
    positiveVerb,
    negativeVerb,
    neutralText
  ) {
    var number = F.finite(value);

    if (number === null) {
      return "sin variación disponible";
    }

    if (number > 0) {
      return (
        positiveVerb
        + " "
        + F.formatPercent(
            number,
            {
              signed: false
            }
          )
      );
    }

    if (number < 0) {
      return (
        negativeVerb
        + " "
        + F.formatPercent(
            Math.abs(number),
            {
              signed: false
            }
          )
      );
    }

    return neutralText;
  }

  function renderExecutionDetails(
    run,
    dataset
  ) {
    var result = (
      run.result_json || {}
    );

    setText(
      "details-dataset",
      (
        dataset
        && dataset.original_filename
      )
      || "—"
    );

    setText(
      "details-date",
      F.formatDate(
        run.finished_at
        || run.created_at
      )
    );

    setText(
      "details-engine",
      (
        (
          run.engine_name
          || (
            result.engine
            && result.engine.name
          )
          || "Motor logístico"
        )
        + " · "
        + (
          run.engine_version
          || (
            result.engine
            && result.engine.version
          )
          || "—"
        )
      )
    );

    setText(
      "details-run-id",
      run.id || "—"
    );
  }

  function objectiveChip(config) {
    return (
      "Objetivo: "
      + F.objectiveLabel(config)
      + " · Prioridad "
      + F.weightLabel(config)
    );
  }

  function renderHero(
    run,
    dataset
  ) {
    var result = run.result_json;
    document.body.classList.remove('dispatch-result');
    var legacyNotice = document.getElementById('dispatch-legacy-notice');
    if (!legacyNotice) { legacyNotice = document.createElement('p'); legacyNotice.id = 'dispatch-legacy-notice'; legacyNotice.textContent = 'Corrida con motor anterior: asignación por despacho, sin planificación de flota.'; document.querySelector('[data-view-panel="decision-dashboard"]').prepend(legacyNotice); }
    var selected = (
      S.selectedScenario(run)
    );
    var current = (
      S.currentScenario(run)
    );
    var config = (
      runConfiguration(run)
    );
    var hero = (
      S.heroDecision(
        current,
        selected,
        result
      )
    );
    var gain = (
      S.savings(
        current,
        selected
      )
    );

    setText(
      "dashboard-objective-chip",
      objectiveChip(config)
    );

    setText(
      "dashboard-recommendation-title",
      hero.title
    );

    var costMessage = percentageImpact(
      gain.cost.pct,
      "reduce el costo",
      "aumenta el costo",
      "mantiene el costo"
    );

    var tripsMessage = (
      percentageImpact(
        gain.trips.pct,
        "reduce los viajes",
        "aumenta los viajes",
        "mantiene los viajes"
      )
    );

    setText(
      "dashboard-recommendation-copy",
      (
        costMessage.charAt(0)
          .toUpperCase()
        + costMessage.slice(1)
        + " y "
        + tripsMessage
        + ", con "
        + F.formatNumber(
            selected.metrics
              .total_trips
          )
        + " viajes y "
        + F.formatKm(
            selected.metrics
              .total_distance_km
          )
        + "."
      )
    );

    var savingLabel = (
      $(".decision-savings-card span")
    );

    if (gain.cost.absolute > 0) {
      if (savingLabel) {
        savingLabel.textContent = (
          "Ahorro estimado"
        );
      }

      setText(
        "dashboard-savings-value",
        F.formatCurrency(
          gain.cost.absolute
        )
      );

      setText(
        "dashboard-savings-percent",
        (
          F.formatPercent(
            -Math.abs(
              gain.cost.pct
            )
          )
          + " vs. asignación actual"
        )
      );
    } else if (
      gain.cost.absolute < 0
    ) {
      if (savingLabel) {
        savingLabel.textContent = (
          "Costo adicional estimado"
        );
      }

      setText(
        "dashboard-savings-value",
        F.formatCurrency(
          Math.abs(
            gain.cost.absolute
          )
        )
      );

      setText(
        "dashboard-savings-percent",
        (
          F.formatPercent(
            Math.abs(
              gain.cost.pct
            )
          )
          + " vs. asignación actual"
        )
      );
    } else {
      if (savingLabel) {
        savingLabel.textContent = (
          "Variación de costo"
        );
      }

      setText(
        "dashboard-savings-value",
        F.formatCurrency(0)
      );

      setText(
        "dashboard-savings-percent",
        "Sin cambio vs. asignación actual"
      );
    }

    var chips = (
      $("#dashboard-meta-chips")
    );

    if (chips) {
      chips.innerHTML = [
        [
          "Dataset",
          (
            dataset
            && dataset.original_filename
          )
          || "—"
        ],
        [
          "Configuración",
          (
            config.mode === "custom"
              ? "Personalizada"
              : "Predefinida"
          )
        ],
        [
          "Prioridades",
          F.weightLabel(config)
        ],
        [
          "Ejecución",
          F.formatDate(
            run.finished_at
            || run.created_at
          )
        ]
      ]
        .map(function (item) {
          return (
            '<span class="decision-meta-chip">'
            + "<small>"
            + escapeHtml(item[0])
            + "</small>"
            + "<strong>"
            + escapeHtml(item[1])
            + "</strong>"
            + "</span>"
          );
        })
        .join("");
    }

    renderAssignmentChart(
      current,
      selected
    );
  }

  function distributionMap(
    scenario
  ) {
    var map = new Map();

    S.assignmentDistribution(
      scenario
    ).forEach(function (item) {
      map.set(
        item.vehicle_type,
        item
      );
    });

    return map;
  }

  function orderedVehicles(
    current,
    selected
  ) {
    var values = new Set();

    S.assignmentDistribution(
      current
    ).forEach(function (item) {
      values.add(item.vehicle_type);
    });

    S.assignmentDistribution(
      selected
    ).forEach(function (item) {
      values.add(item.vehicle_type);
    });

    return Array.from(values)
      .sort(function (a, b) {
        return (
          F.vehicleLabel(a)
            .localeCompare(
              F.vehicleLabel(b)
            )
        );
      });
  }

  function renderStackedBar(
    label,
    scenario,
    vehicles,
    role
  ) {
    var distribution = (
      distributionMap(scenario)
    );

    var total = (
      scenario
      && scenario.metrics
      && Number(
        scenario.metrics.shipments
      )
    )
    || 1;

    var segments = (
      vehicles.map(
        function (
          vehicle,
          index
        ) {
          var item = (
            distribution.get(vehicle)
            || {
              shipments: 0
            }
          );

          var width = (
            Number(
              item.shipments || 0
            )
            / total
          ) * 100;

          return (
            '<div class="assignment-segment '
            + "assignment-segment--"
            + role
            + " assignment-segment--tone-"
            + (
              index % 3
            )
            + '" style="width:'
            + width.toFixed(3)
            + '%" title="'
            + escapeHtml(
                F.vehicleLabel(vehicle)
                + ": "
                + F.formatNumber(
                    item.shipments
                  )
                + " despachos"
              )
            + '">'
            + (
              width >= 9
                ? (
                  "<span>"
                  + escapeHtml(
                      F.vehicleLabel(vehicle)
                    )
                  + " · "
                  + F.formatNumber(
                      item.shipments
                    )
                  + "</span>"
                )
                : ""
            )
            + "</div>"
          );
        }
      ).join("")
    );

    return (
      '<div class="assignment-row">'
      + '<div class="assignment-row__label">'
      + escapeHtml(label)
      + "</div>"
      + '<div class="assignment-row__bar">'
      + segments
      + "</div>"
      + '<strong class="assignment-row__total">'
      + F.formatNumber(total)
      + "</strong>"
      + "</div>"
    );
  }

  function renderAssignmentChart(
    current,
    selected
  ) {
    var chart = (
      $("#dashboard-assignment-chart")
    );
    var detail = (
      $(
        "#dashboard-assignment-vehicle-details"
      )
    );

    if (!chart || !detail) {
      return;
    }

    var vehicles = orderedVehicles(
      current,
      selected
    );

    chart.innerHTML = (
      renderStackedBar(
        "Asignación actual",
        current,
        vehicles,
        "current"
      )
      + renderStackedBar(
        "Decisión recomendada",
        selected,
        vehicles,
        "decision"
      )
    );

    var currentMap = (
      distributionMap(current)
    );
    var selectedMap = (
      distributionMap(selected)
    );

    detail.innerHTML = (
      vehicles.map(function (vehicle) {
        var before = (
          currentMap.get(vehicle)
          || {
            shipments: 0,
            trips: 0,
            units: 0
          }
        );

        var after = (
          selectedMap.get(vehicle)
          || {
            shipments: 0,
            trips: 0,
            units: 0
          }
        );

        return (
          '<div class="assignment-vehicle-row">'
          + "<strong>"
          + escapeHtml(
              F.vehicleLabel(vehicle)
            )
          + "</strong>"
          + "<span>"
          + F.formatNumber(
              after.shipments
            )
          + " despachos</span>"
          + "<span>"
          + F.formatNumber(
              after.trips
            )
          + " viajes</span>"
          + "<span>"
          + F.formatNumber(
              after.units
            )
          + " unidades</span>"
          + "<small>Antes: "
          + F.formatNumber(
              before.shipments
            )
          + " despachos</small>"
          + "</div>"
        );
      }).join("")
    );
  }

  function metricFormatter(key, value) {
    if (key === "cost") {
      return F.formatCurrency(value);
    }

    if (key === "distance") {
      return F.formatKm(value);
    }

    return F.formatNumber(value);
  }

  function chartMetricFormatter(
    key,
    value
  ) {
    if (key === "cost") {
      return F.formatCurrencyCompact(
        value
      );
    }

    return metricFormatter(
      key,
      value
    );
  }

  function metricDeltaFormatter(
    key,
    value
  ) {
    var number = F.finite(value);

    if (number === null) {
      return "—";
    }

    var prefix = (
      number > 0
        ? "+"
        : number < 0
          ? "−"
          : ""
    );

    var absolute = Math.abs(number);

    if (key === "cost") {
      return (
        prefix
        + F.formatCurrency(
            absolute
          )
      );
    }

    if (key === "distance") {
      return (
        prefix
        + F.formatKm(
            absolute
          )
      );
    }

    return (
      prefix
      + F.formatNumber(
          absolute
        )
    );
  }

  function improvementClass(
    saving
  ) {
    var value = F.finite(saving);

    if (value === null || value === 0) {
      return "is-neutral";
    }

    return (
      value > 0
        ? "is-improvement"
        : "is-worse"
    );
  }

  function kpiDefinition(key) {
    var definitions = {
      cost: (
        "Costo total = costo variable + "
        + "costo fijo de todos los viajes."
      ),
      trips: (
        "Viajes requeridos según peso total "
        + "y capacidad del vehículo asignado."
      ),
      distance: (
        "Distancia total modelada considerando "
        + "ida y regreso por viaje."
      ),
      reassigned: (
        "Despachos cuyo tipo de camión cambia "
        + "respecto de la asignación actual."
      )
    };

    return definitions[key] || "";
  }

  function renderKpis(
    current,
    selected
  ) {
    var container = (
      $("#dashboard-kpi-grid")
    );

    if (!container) {
      return;
    }

    container.innerHTML = (
      S.kpis(
        current,
        selected
      )
        .map(function (item) {
          var max = Math.max(
            Math.abs(
              Number(
                item.current || 0
              )
            ),
            Math.abs(
              Number(
                item.decision || 0
              )
            ),
            1
          );

          var currentWidth = (
            Math.abs(
              Number(
                item.current || 0
              )
            )
            / max
          ) * 100;

          var decisionWidth = (
            Math.abs(
              Number(
                item.decision || 0
              )
            )
            / max
          ) * 100;

          var saving = (
            Number(
              item.current || 0
            )
            - Number(
              item.decision || 0
            )
          );

          if (item.key === "reassigned") {
            saving = 0;
          }

          var deltaClass = (
            item.key === "reassigned"
              ? "is-neutral"
              : improvementClass(
                  item.absolute
                )
          );

          var deltaText;

          if (item.key === "reassigned") {
            deltaText = (
              F.formatNumber(
                item.decision
              )
              + " de "
              + F.formatNumber(
                  selected.metrics
                    .shipments
                )
              + " despachos"
            );
          } else {
            var savingValue = Number(
              item.absolute || 0
            );

            var arrow = (
              savingValue > 0
                ? "↓ "
                : savingValue < 0
                  ? "↑ "
                  : "→ "
            );

            deltaText = (
              arrow
              + metricFormatter(
                  item.key,
                  Math.abs(
                    savingValue
                  )
                )
              + " · "
              + F.formatPercent(
                  -Number(
                    item.pct || 0
                  )
                )
            );
          }

          return (
            '<article class="decision-kpi-card" title="'
            + escapeHtml(
                kpiDefinition(
                  item.key
                )
              )
            + '">'
            + '<div class="decision-kpi-card__label">'
            + "<span>"
            + escapeHtml(item.label)
            + "</span>"
            + '<button class="kpi-info" type="button" aria-label="'
            + escapeHtml(
                kpiDefinition(
                  item.key
                )
              )
            + '">i</button>'
            + "</div>"
            + '<strong class="decision-kpi-card__value">'
            + escapeHtml(
                metricFormatter(
                  item.key,
                  item.decision
                )
              )
            + "</strong>"
            + '<div class="decision-kpi-card__current">'
            + "Asignación actual: "
            + "<span>"
            + escapeHtml(
                metricFormatter(
                  item.key,
                  item.current
                )
              )
            + "</span>"
            + "</div>"
            + '<div class="decision-kpi-card__delta '
            + deltaClass
            + '">'
            + escapeHtml(deltaText)
            + "</div>"
            + '<div class="kpi-mini-bars" aria-hidden="true">'
            + '<span class="kpi-mini-bar kpi-mini-bar--current" style="width:'
            + currentWidth.toFixed(2)
            + '%"></span>'
            + '<span class="kpi-mini-bar kpi-mini-bar--decision" style="width:'
            + decisionWidth.toFixed(2)
            + '%"></span>'
            + "</div>"
            + "</article>"
          );
        }).join("")
    );
  }

  function renderComparison(
    run,
    referenceKey
  ) {
    var result = run.result_json;
    var selected = (
      S.selectedScenario(run)
    );
    var reference = (
      result.scenarios[
        referenceKey
      ]
    );
    var stateNode = (
      $("#dashboard-comparison-state")
    );
    var layout = (
      $(".dashboard-comparison-layout")
    );
    var chart = (
      $("#dashboard-comparison-chart")
    );
    var table = (
      $("#dashboard-comparison-table-body")
    );

    if (
      !selected
      || !reference
      || !stateNode
      || !layout
      || !chart
      || !table
    ) {
      return;
    }

    var same = (
      S.scenariosEquivalent(
        selected,
        reference
      )
    );

    stateNode.classList.toggle(
      "is-hidden",
      !same
    );

    if (same) {
      stateNode.innerHTML = (
        "<strong>Sin diferencias operativas</strong>"
        + "<span>Este escenario produce la misma asignación "
        + "que la decisión recomendada. No hay diferencias que mostrar.</span>"
      );

      layout.classList.add(
        "is-hidden"
      );
    } else {
      stateNode.innerHTML = "";
      layout.classList.remove(
        "is-hidden"
      );
    }

    var metrics = [
      {
        key: "cost",
        source: "total_cost",
        label: "Costo total"
      },
      {
        key: "trips",
        source: "total_trips",
        label: "Viajes"
      },
      {
        key: "distance",
        source: "total_distance_km",
        label: "Distancia"
      }
    ];

    chart.innerHTML = (
      metrics.map(function (metric) {
        var decisionValue = Number(
          selected.metrics[
            metric.source
          ]
        );

        var referenceValue = Number(
          reference.metrics[
            metric.source
          ]
        );

        var maximum = Math.max(
          Math.abs(decisionValue),
          Math.abs(referenceValue),
          1
        );

        return (
          '<div class="real-comparison-metric">'
          + '<div class="real-comparison-metric__head">'
          + "<strong>"
          + escapeHtml(metric.label)
          + "</strong>"
          + "<span>"
          + escapeHtml(
              chartMetricFormatter(
                metric.key,
                decisionValue
              )
            )
          + " vs "
          + escapeHtml(
              chartMetricFormatter(
                metric.key,
                referenceValue
              )
            )
          + "</span>"
          + "</div>"
          + '<div class="real-comparison-bar">'
          + "<span>Decisión</span>"
          + '<div><i class="is-decision" style="width:'
          + (
            decisionValue
            / maximum
            * 100
          ).toFixed(2)
          + '%"></i></div>'
          + "</div>"
          + '<div class="real-comparison-bar">'
          + "<span>Comparada</span>"
          + '<div><i class="is-current" style="width:'
          + (
            referenceValue
            / maximum
            * 100
          ).toFixed(2)
          + '%"></i></div>'
          + "</div>"
          + "</div>"
        );
      }).join("")
    );

    table.innerHTML = (
      metrics.map(function (metric) {
        var decisionValue = Number(
          selected.metrics[
            metric.source
          ]
        );

        var referenceValue = Number(
          reference.metrics[
            metric.source
          ]
        );

        var difference = (
          decisionValue
          - referenceValue
        );

        var variation = (
          referenceValue === 0
            ? null
            : (
              difference
              / referenceValue
            ) * 100
        );

        var semantic = (
          difference < 0
            ? "is-improvement"
            : difference > 0
              ? "is-worse"
              : "is-neutral"
        );

        return (
          "<tr>"
          + "<th>"
          + escapeHtml(metric.label)
          + "</th>"
          + '<td class="numeric">'
          + escapeHtml(
              metricFormatter(
                metric.key,
                decisionValue
              )
            )
          + "</td>"
          + '<td class="numeric">'
          + escapeHtml(
              metricFormatter(
                metric.key,
                referenceValue
              )
            )
          + "</td>"
          + '<td class="numeric '
          + semantic
          + '">'
          + escapeHtml(
              metricDeltaFormatter(
                metric.key,
                difference
              )
            )
          + "</td>"
          + '<td class="numeric '
          + semantic
          + '">'
          + escapeHtml(
              F.formatPercent(
                variation
              )
            )
          + "</td>"
          + "</tr>"
        );
      }).join("")
    );

    setText(
      "dashboard-comparison-assignments",
      (
        F.formatNumber(
          S.assignmentDifferenceCount(
            selected,
            reference
          )
        )
        + " de "
        + F.formatNumber(
            selected.metrics
              .shipments
          )
      )
    );
  }

  function populateComparison(
    run
  ) {
    var result = run.result_json;
    var select = (
      $("#dashboard-comparison-select")
    );

    if (!select) {
      return;
    }

    var options = [
      ["baseline", "Asignación actual"],
      ["min_cost", "Costo mínimo"],
      ["min_trips", "Viajes mínimos"]
    ];

    select.innerHTML = (
      options
        .filter(function (option) {
          return Boolean(
            result.scenarios[
              option[0]
            ]
          );
        })
        .map(function (option) {
          return (
            '<option value="'
            + option[0]
            + '">'
            + escapeHtml(option[1])
            + "</option>"
          );
        }).join("")
    );

    var defaultKey = (
      S.chooseDefaultReference(
        result
      )
    );

    select.value = defaultKey;

    renderComparison(
      run,
      defaultKey
    );
  }

  function renderDrivers(
    run
  ) {
    var result = run.result_json;
    var current = (
      S.currentScenario(run)
    );
    var selected = (
      S.selectedScenario(run)
    );

    var details = (
      S.reassignmentDetails(
        current,
        selected,
        result
      )
    );

    state.detailRows = details;
    state.detailPage = 1;

    setText(
      "dashboard-drivers-summary",
      (
        F.formatNumber(
          details.length
        )
        + " de "
        + F.formatNumber(
            selected.metrics
              .shipments
          )
        + " despachos cambian de camión. "
        + F.formatNumber(
            Number(
              selected.metrics.shipments
            ) - details.length
          )
        + " se mantienen."
      )
    );

    var button = (
      $("#open-reassignment-detail")
    );

    if (button) {
      button.textContent = (
        details.length
          ? (
            "Ver las "
            + F.formatNumber(
                details.length
              )
            + " reasignaciones"
          )
          : "Ver detalle"
      );

      button.disabled = (
        details.length === 0
      );
    }

    var matrix = (
      $("#dashboard-flow-matrix")
    );

    if (matrix) {
      var flows = (
        S.reassignmentMatrix(
          current,
          selected,
          result
        )
      );

      matrix.innerHTML = (
        flows.length
          ? flows.map(
            function (flow) {
              return (
                '<div class="flow-card">'
                + '<div class="flow-card__route">'
                + "<span>"
                + escapeHtml(
                    F.vehicleLabel(
                      flow.from_vehicle
                    )
                  )
                + "</span>"
                + '<i aria-hidden="true">→</i>'
                + "<span>"
                + escapeHtml(
                    F.vehicleLabel(
                      flow.to_vehicle
                    )
                  )
                + "</span>"
                + "</div>"
                + "<strong>"
                + F.formatNumber(
                    flow.shipments
                  )
                + " despachos</strong>"
                + "<small>"
                + F.formatNumber(
                    flow.trips_avoided
                  )
                + " viajes evitados · "
                + F.formatCurrency(
                    flow.cost_saving
                  )
                + " de impacto</small>"
                + "</div>"
              );
            }
          ).join("")
          : (
            '<div class="empty-state">'
            + "<strong>Sin reasignaciones</strong>"
            + "<span>La decisión mantiene los mismos "
            + "tipos de camión informados en la asignación actual.</span>"
            + "</div>"
          )
      );
    }

    var corridorBody = (
      $("#dashboard-corridor-table-body")
    );

    if (corridorBody) {
      var corridors = (
        S.corridorGroups(
          current,
          selected,
          result
        )
      );

      corridorBody.innerHTML = (
        corridors.length
          ? corridors
            .slice(0, 5)
            .map(function (row) {
              var transition = (
                row.dominant_transition
                  .split("→")
              );

              return (
                "<tr>"
                + "<th>"
                + escapeHtml(
                    row.corridor
                  )
                + "</th>"
                + '<td class="numeric">'
                + F.formatNumber(
                    row.shipments
                  )
                + "</td>"
                + "<td>"
                + escapeHtml(
                    F.vehicleLabel(
                      transition[0]
                    )
                    + " → "
                    + F.vehicleLabel(
                        transition[1]
                      )
                  )
                + "</td>"
                + '<td class="numeric">'
                + F.formatNumber(
                    row.trips_avoided
                  )
                + "</td>"
                + '<td class="numeric '
                + improvementClass(
                    row.cost_saving
                  )
                + '">'
                + F.formatCurrency(
                    row.cost_saving
                  )
                + "</td>"
                + "</tr>"
              );
            }).join("")
          : (
            '<tr><td colspan="5">'
            + "No hay corredores con reasignaciones."
            + "</td></tr>"
          )
      );
    }

    populateDetailFilters(
      details
    );

    renderReassignmentDetail();
  }

  function populateDetailFilters(
    rows
  ) {
    function populate(
      selector,
      values,
      allLabel,
      formatter
    ) {
      var select = $(selector);

      if (!select) {
        return;
      }

      select.innerHTML = (
        '<option value="">'
        + escapeHtml(allLabel)
        + "</option>"
        + values.map(function (value) {
          return (
            '<option value="'
            + escapeHtml(value)
            + '">'
            + escapeHtml(
                formatter
                  ? formatter(value)
                  : value
              )
            + "</option>"
          );
        }).join("")
      );
    }

    var vehicles = Array.from(
      new Set(
        rows.map(function (row) {
          return row.to_vehicle;
        })
      )
    ).sort();

    var origins = Array.from(
      new Set(
        rows.map(function (row) {
          return row.origin;
        })
      )
    ).sort();

    var destinations = Array.from(
      new Set(
        rows.map(function (row) {
          return row.destination;
        })
      )
    ).sort();

    populate(
      "#reassignment-vehicle-filter",
      vehicles,
      "Todos los camiones",
      F.vehicleLabel
    );

    populate(
      "#reassignment-origin-filter",
      origins,
      "Todos los orígenes"
    );

    populate(
      "#reassignment-destination-filter",
      destinations,
      "Todos los destinos"
    );
  }

  function filteredDetailRows() {
    var search = (
      $("#reassignment-search")
    );
    var vehicle = (
      $("#reassignment-vehicle-filter")
    );
    var origin = (
      $("#reassignment-origin-filter")
    );
    var destination = (
      $("#reassignment-destination-filter")
    );
    var sort = (
      $("#reassignment-sort")
    );

    var query = (
      search
        ? search.value
          .trim()
          .toLowerCase()
        : ""
    );

    var vehicleValue = (
      vehicle ? vehicle.value : ""
    );
    var originValue = (
      origin ? origin.value : ""
    );
    var destinationValue = (
      destination
        ? destination.value
        : ""
    );

    var rows = state.detailRows
      .filter(function (row) {
        if (
          vehicleValue
          && row.to_vehicle
            !== vehicleValue
        ) {
          return false;
        }

        if (
          originValue
          && row.origin !== originValue
        ) {
          return false;
        }

        if (
          destinationValue
          && row.destination
            !== destinationValue
        ) {
          return false;
        }

        if (!query) {
          return true;
        }

        return [
          row.shipment_id,
          row.product,
          row.origin,
          row.destination,
          row.from_vehicle,
          row.to_vehicle
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      });

    var mode = (
      sort
        ? sort.value
        : "impact_desc"
    );

    return rows.sort(
      function (a, b) {
        if (mode === "trips_desc") {
          return (
            b.trips_avoided
            - a.trips_avoided
          );
        }

        if (mode === "corridor_asc") {
          return (
            (
              a.origin
              + " "
              + a.destination
            ).localeCompare(
              b.origin
              + " "
              + b.destination
            )
          );
        }

        return (
          Math.abs(b.cost_saving)
          - Math.abs(a.cost_saving)
        );
      }
    );
  }

  function renderReassignmentDetail() {
    var rows = (
      filteredDetailRows()
    );

    var pages = Math.max(
      1,
      Math.ceil(
        rows.length
        / state.detailPageSize
      )
    );

    state.detailPage = Math.min(
      Math.max(
        state.detailPage,
        1
      ),
      pages
    );

    var start = (
      (
        state.detailPage
        - 1
      )
      * state.detailPageSize
    );

    var pageRows = rows.slice(
      start,
      start
      + state.detailPageSize
    );

    var body = (
      $("#reassignment-detail-body")
    );

    if (body) {
      body.innerHTML = (
        pageRows.length
          ? pageRows.map(
            function (row) {
              return (
                "<tr>"
                + "<th>"
                + escapeHtml(
                    row.shipment_id
                  )
                + "</th>"
                + "<td>"
                + escapeHtml(
                    row.origin
                    + " → "
                    + row.destination
                  )
                + "</td>"
                + "<td>"
                + escapeHtml(
                    F.vehicleLabel(
                      row.from_vehicle
                    )
                  )
                + "</td>"
                + "<td>"
                + escapeHtml(
                    F.vehicleLabel(
                      row.to_vehicle
                    )
                  )
                + "</td>"
                + '<td class="numeric">'
                + F.formatNumber(
                    row.trips_avoided
                  )
                + "</td>"
                + '<td class="numeric '
                + improvementClass(
                    row.cost_saving
                  )
                + '">'
                + F.formatCurrency(
                    row.cost_saving
                  )
                + "</td>"
                + "</tr>"
              );
            }
          ).join("")
          : (
            '<tr><td colspan="6">'
            + "No hay resultados para los filtros seleccionados."
            + "</td></tr>"
          )
      );
    }

    setText(
      "reassignment-dialog-copy",
      (
        F.formatNumber(
          rows.length
        )
        + " reasignaciones encontradas"
      )
    );

    setText(
      "reassignment-page",
      (
        "Página "
        + state.detailPage
        + " de "
        + pages
      )
    );

    var prev = (
      $("#reassignment-prev")
    );
    var next = (
      $("#reassignment-next")
    );

    if (prev) {
      prev.disabled = (
        state.detailPage <= 1
      );
    }

    if (next) {
      next.disabled = (
        state.detailPage >= pages
      );
    }
  }

  function openReassignmentDetail() {
    var dialog = (
      $("#reassignment-dialog")
    );

    if (!dialog) {
      return;
    }

    dialog.classList.remove(
      "is-hidden"
    );

    document.body.classList.add(
      "has-overlay"
    );

    var search = (
      $("#reassignment-search")
    );

    if (search) {
      window.setTimeout(
        function () {
          search.focus();
        },
        40
      );
    }
  }

  function closeReassignmentDetail() {
    var dialog = (
      $("#reassignment-dialog")
    );

    if (dialog) {
      dialog.classList.add(
        "is-hidden"
      );
    }

    document.body.classList.remove(
      "has-overlay"
    );
  }

  function csvCell(value) {
    return (
      '"'
      + String(
          value == null
            ? ""
            : value
        )
        .replaceAll('"', '""')
      + '"'
    );
  }

  function downloadBlob(
    filename,
    content,
    type
  ) {
    var blob = new Blob(
      [content],
      {
        type: type
      }
    );

    var url = URL.createObjectURL(
      blob
    );

    var anchor = (
      document.createElement("a")
    );

    anchor.href = url;
    anchor.download = filename;

    document.body.appendChild(
      anchor
    );

    anchor.click();
    anchor.remove();

    window.setTimeout(
      function () {
        URL.revokeObjectURL(url);
      },
      0
    );
  }

  function exportReassignments() {
    var rows = (
      filteredDetailRows()
    );

    var header = [
      "shipment_id",
      "origin",
      "destination",
      "current_vehicle",
      "recommended_vehicle",
      "trips_avoided",
      "cost_impact"
    ];

    var lines = [
      header.map(csvCell).join(",")
    ];

    rows.forEach(function (row) {
      lines.push(
        [
          row.shipment_id,
          row.origin,
          row.destination,
          F.vehicleLabel(
            row.from_vehicle
          ),
          F.vehicleLabel(
            row.to_vehicle
          ),
          row.trips_avoided,
          row.cost_saving
        ]
          .map(csvCell)
          .join(",")
      );
    });

    downloadBlob(
      "dation-reasignaciones.csv",
      lines.join("\n"),
      "text/csv;charset=utf-8"
    );
  }

  function renderSensitivity(run) {
    var container = (
      $("#dashboard-sensitivity-content")
    );

    if (!container) {
      return;
    }

    var result = run.result_json;
    var selected = (
      S.selectedScenario(run)
    );

    var summary = (
      S.sensitivitySummary(
        result
      )
    );

    if (summary.robust) {
      container.innerHTML = (
        '<div class="sensitivity-robust">'
        + '<div class="sensitivity-robust__icon">✓</div>'
        + "<div>"
        + "<span>Decisión robusta</span>"
        + "<strong>No cambia aunque se priorice costo o viajes</strong>"
        + "<p>Los extremos 100 % costo y 100 % viajes "
        + "producen la misma asignación de camiones que la decisión recomendada.</p>"
        + "</div>"
        + "</div>"
      );

      return;
    }

    var unique = [];

    summary.available.forEach(
      function (item) {
        var duplicate = unique.some(
          function (existing) {
            return (
              S.scenariosEquivalent(
                existing.scenario,
                item.scenario
              )
            );
          }
        );

        if (!duplicate) {
          unique.push(item);
        }
      }
    );

    container.innerHTML = (
      '<div class="sensitivity-comparison-grid">'
      + unique.map(function (item) {
        var scenario = item.scenario;
        var difference = (
          S.assignmentDifferenceCount(
            selected,
            scenario
          )
        );

        return (
          '<article class="sensitivity-comparison-card '
          + (
            item.same
              ? "is-same"
              : ""
          )
          + '">'
          + "<span>"
          + escapeHtml(
              F.scenarioLabel(
                item.key
              )
            )
          + "</span>"
          + "<strong>"
          + F.formatNumber(
              scenario.metrics
                .total_trips
            )
          + " viajes · "
          + F.formatCurrency(
              scenario.metrics
                .total_cost
            )
          + "</strong>"
          + "<p>"
          + (
            item.same
              ? "Misma asignación que la decisión recomendada."
              : (
                F.formatNumber(
                  difference
                )
                + " despachos cambian respecto de la decisión recomendada."
              )
          )
          + "</p>"
          + "</article>"
        );
      }).join("")
      + "</div>"
    );
  }

  function renderSectionSafely(
    sectionId,
    renderer
  ) {
    var section = document.getElementById(
      sectionId
    );

    if (!section) {
      return;
    }

    var previous = section.querySelector(
      ".dashboard-section-error"
    );

    if (previous) {
      previous.remove();
    }

    try {
      renderer();
    } catch (error) {
      console.error(
        "Error al renderizar "
        + sectionId,
        error
      );

      var notice = (
        document.createElement("div")
      );

      notice.className = (
        "dashboard-section-error"
      );

      var message = (
        document.createElement("span")
      );

      message.textContent = (
        "No se pudo mostrar esta sección. "
        + "El resto de la decisión sigue disponible."
      );

      var retry = (
        document.createElement("button")
      );

      retry.type = "button";
      retry.className = (
        "button button--secondary"
      );
      retry.textContent = "Reintentar";

      retry.addEventListener(
        "click",
        function () {
          renderSectionSafely(
            sectionId,
            renderer
          );
        }
      );

      notice.appendChild(message);
      notice.appendChild(retry);
      section.prepend(notice);
    }
  }


  function renderDashboard(
    run,
    dataset,
    profile
  ) {
    if (
      !run
      || !run.result_json
    ) {
      showError(
        "La corrida no contiene un DecisionResult válido."
      );
      return;
    }

    var selected = (
      S.selectedScenario(run)
    );
    var current = (
      S.currentScenario(run)
    );

    if (!selected || !current) {
      showError(
        "La corrida no contiene los escenarios necesarios para construir el Dashboard."
      );
      return;
    }

    showDashboard();

    renderExecutionDetails(
      run,
      dataset
    );

    renderSectionSafely(
      "dashboard-decision",
      function () {
        renderHero(
          run,
          dataset
        );
      }
    );

    renderSectionSafely(
      "dashboard-kpis",
      function () {
        renderKpis(
          current,
          selected
        );
      }
    );

    renderSectionSafely(
      "dashboard-comparator",
      function () {
        populateComparison(run);
      }
    );

    renderSectionSafely(
      "dashboard-drivers",
      function () {
        renderDrivers(run);
      }
    );

    renderSectionSafely(
      "dashboard-sensitivity",
      function () {
        renderSensitivity(run);
      }
    );


    var exportButton = (
      $("#export-decision")
    );

    if (exportButton) {
      exportButton.disabled = false;
    }

    if (
      typeof window
        .dationSetDashboardReady
      === "function"
    ) {
      window.dationSetDashboardReady(
        true
      );
    }
  }

  async function recoverRun(run) {
    if (run.result_json && ['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(run.result_json.schema_version)) {
      if (window.DationDispatch && typeof window.DationDispatch.show === "function") {
        window.DationDispatch.show(run);
      } else {
        var dispatch = await import('/static/js/dispatch/workspace.mjs?v=decision-map-nodal-v1');
        dispatch.show(run);
      }
      return;
    }
    document.body.classList.remove('dispatch-result');
    var context = (
      state.context || {}
    );

    var dataset = context.dataset;
    var profile = context.profile;

    if (!dataset || !profile) {
      var payload = await requestJson(
        "/api/datasets/"
        + encodeURIComponent(
            run.dataset_id
          )
        + "/profile"
      );

      dataset = payload.dataset;
      profile = payload;
    }

    var completed = Object.assign(
      {},
      context,
      {
        runId: run.id,
        run: run,
        dataset: dataset,
        profile: profile,
        configuration: (
          runConfiguration(run)
        ),
        status: "completed",
        finishedAt: (
          run.finished_at
          || run.created_at
        )
      }
    );

    saveContext(completed);
    setRunInUrl(run.id);

    if (
      typeof window.dationNavigate
      === "function"
    ) {
      window.dationNavigate(
        "decision-dashboard"
      );
    }

    renderDashboard(
      run,
      dataset,
      profile
    );

    updateLatestDecisionCta(
      run
    );

    window.dispatchEvent(
      new CustomEvent(
        "dation:dashboard-completed",
        {
          detail: {
            run: run,
            dataset: dataset,
            profile: profile,
            context: completed
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
          || "El motor registró un error durante la ejecución."
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
        "No se pudo recuperar el estado persistido de la corrida."
      );
    }
  }

  async function retryStatus() {
    if (
      !state.context
      || !state.context.runId
    ) {
      return;
    }

    state.pollAttempts = 0;
    showRunning();
    await pollCurrentRun();
  }

  async function retryRun() {
    if (
      state.context
      && state.context.configuration
      && typeof window
        .dationRetryDecision
        === "function"
    ) {
      showRunning();

      await window.dationRetryDecision(
        state.context.configuration
      );
      return;
    }

    if (
      typeof window.dationNavigate
      === "function"
    ) {
      window.dationNavigate(
        "logistics-config"
      );
    }
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

    if (state.context) {
      saveContext(
        Object.assign(
          {},
          state.context,
          {
            status: "cancelled"
          }
        )
      );
    }

    showCancelled();
  }

  function latestDecisionButton() {
    return (
      $("#open-latest-logistics-decision")
    );
  }

  function latestDecisionMeta() {
    return (
      $("#latest-logistics-meta")
    );
  }

  function landingHasData() {
    try {
      var saved = JSON.parse(
        sessionStorage.getItem(
          "dation.dispatch.workspace.v4"
        )
        || "{}"
      );

      return Boolean(
        saved
        && saved.orders
        && saved.fleet
      );
    } catch (error) {
      return false;
    }
  }

  function formatLandingDecisionDate(value) {
    if (!value) {
      return "";
    }

    var parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
      return F.formatDate(value);
    }

    return new Intl.DateTimeFormat(
      "es-AR",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      }
    ).format(parsed);
  }

  function updateLatestDecisionCta(run) {
    var button = (
      latestDecisionButton()
    );
    var meta = (
      latestDecisionMeta()
    );

    if (!button || !meta) {
      return;
    }

    if (!run) {
      button.disabled = false;
      button.dataset.mode = "example";
      delete button.dataset.runId;
      button.textContent = "Ver un ejemplo de resultado ↘";
      meta.textContent = (
        "Todavía no hay decisiones completadas · podés explorar un resultado de ejemplo."
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
    button.dataset.mode = "latest";
    button.dataset.runId = run.id;
    button.textContent = "Analizar mi última decisión ↗";
    meta.textContent = (
      "Última decisión · "
      + formatLandingDecisionDate(
          run.finished_at
          || run.created_at
        )
    );

    if (
      typeof window
        .dationSetDashboardReady
      === "function"
    ) {
      window.dationSetDashboardReady(
        true
      );
    }
  }

  async function findLatestCompletedRun() {
    var payload = await requestJson(
      "/api/runs?limit=30"
    );

    var items = (
      payload
      && Array.isArray(
        payload.items
      )
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
      var latest = (
        await findLatestCompletedRun()
      );

      updateLatestDecisionCta(
        latest
      );

      return latest;
    } catch (error) {
      var meta = (
        latestDecisionMeta()
      );

      if (meta) {
        meta.textContent = (
          "No se pudo consultar la última decisión."
        );
      }

      return null;
    }
  }

  async function openLatestDecision() {
    var button = (
      latestDecisionButton()
    );

    if (
      button
      && button.dataset.mode === "example"
    ) {
      var example = document.getElementById(
        "dda-logistics-example-result"
      );

      if (example) {
        example.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      }

      return;
    }

    if (button) {
      button.disabled = true;
      button.textContent = (
        "Abriendo última decisión…"
      );
    }

    try {
      var summary = (
        await findLatestCompletedRun()
      );

      if (!summary) {
        updateLatestDecisionCta(
          null
        );
        return;
      }

      var run = await requestJson(
        "/api/runs/"
        + encodeURIComponent(
            summary.id
          )
      );

      saveContext({
        runId: run.id,
        run: run,
        status: "completed",
        finishedAt: (
          run.finished_at
          || run.created_at
        )
      });

      setRunInUrl(run.id);

      await recoverRun(run);
    } catch (error) {
      showError(
        "No se pudo abrir la última decisión: "
        + error.message
      );
    } finally {
      if (
        button
        && button.dataset.mode !== "example"
      ) {
        button.textContent = (
          "Analizar mi última decisión ↗"
        );
        button.disabled = false;
      }
    }
  }

  function downloadDecisionTxt(run) {
    if (
      !run
      || !run.result_json
    ) {
      return false;
    }

    downloadBlob(
      (
        "dation-decision-"
        + String(run.id).slice(0, 8)
        + ".txt"
      ),
      JSON.stringify(
        run.result_json,
        null,
        2
      ),
      "text/plain;charset=utf-8"
    );

    return true;
  }

  async function exportCurrentDecision() {
    var context = (
      state.context
      || loadContext()
      || {}
    );

    var run = context.run;
    var button = $("#export-decision");

    try {
      var runId = (
        context.runId
        || runFromUrl()
      );

      if (
        !run
        || !run.result_json
      ) {
        if (!runId) {
          throw new Error(
            "No hay una decisión activa para exportar."
          );
        }

        run = await requestJson(
          "/api/runs/"
          + encodeURIComponent(
              runId
            )
        );
      }

      if (button) {
        button.disabled = true;
        button.textContent = "Preparando…";
      }

      if (
        run.result_json
        && [
          "assignment_v1",
          "scheduling_v1",
          "dispatch_v1",
          "dispatch_v2"
        ].includes(
          run.result_json.schema_version
        )
      ) {
        var exporter = await import(
          "/static/js/dispatch/export.mjs?v=decision-map-nodal-v1"
        );
        exporter.exportDecision(
          run.result_json
        );
      } else if (
        !downloadDecisionTxt(run)
      ) {
        throw new Error(
          "La corrida no contiene un resultado exportable."
        );
      }

      if (button) {
        button.textContent = "✓ Exportado";
        window.setTimeout(
          function () {
            button.textContent = "Exportar";
            button.disabled = false;
          },
          1200
        );
      }
    } catch (error) {
      console.error(
        "Error al exportar decisión.",
        error
      );

      if (button) {
        button.disabled = false;
        button.textContent = "Error al exportar";
        window.setTimeout(
          function () {
            button.textContent = "Exportar";
          },
          1500
        );
      }
    }
  }

  function copyRunId() {
    var runId = (
      state.context
      && state.context.runId
    );

    if (!runId) {
      return;
    }

    if (
      navigator.clipboard
      && navigator.clipboard.writeText
    ) {
      navigator.clipboard.writeText(
        runId
      ).then(function () {
        var button = $("#copy-run-id");

        if (!button) {
          return;
        }

        button.textContent = "Copiado";

        window.setTimeout(
          function () {
            button.textContent = "Copiar ID";
          },
          1200
        );
      });
    }
  }

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
    var exportButton = (
      $("#export-decision")
    );
    var reexecute = (
      $("#dashboard-reexecute")
    );
    var copyRun = (
      $("#copy-run-id")
    );
    var comparison = (
      $("#dashboard-comparison-select")
    );
    var detailOpen = (
      $("#open-reassignment-detail")
    );
    var detailClose = (
      $("#close-reassignment-detail")
    );
    var detailSearch = (
      $("#reassignment-search")
    );
    var detailVehicle = (
      $("#reassignment-vehicle-filter")
    );
    var detailOrigin = (
      $("#reassignment-origin-filter")
    );
    var detailDestination = (
      $("#reassignment-destination-filter")
    );
    var detailSort = (
      $("#reassignment-sort")
    );
    var detailPrev = (
      $("#reassignment-prev")
    );
    var detailNext = (
      $("#reassignment-next")
    );
    var detailExport = (
      $("#export-reassignments")
    );
    var latestButton = (
      latestDecisionButton()
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

    if (exportButton) {
      exportButton.addEventListener(
        "click",
        exportCurrentDecision
      );
    }

    if (reexecute) {
      reexecute.addEventListener(
        "click",
        function () {
          if (
            typeof window
              .dationNavigate
              === "function"
          ) {
            window.dationNavigate(
              "logistics-config"
            );
          }
        }
      );
    }

    if (copyRun) {
      copyRun.addEventListener(
        "click",
        copyRunId
      );
    }

    if (comparison) {
      comparison.addEventListener(
        "change",
        function () {
          if (
            state.context
            && state.context.run
          ) {
            renderComparison(
              state.context.run,
              comparison.value
            );
          }
        }
      );
    }

    if (detailOpen) {
      detailOpen.addEventListener(
        "click",
        openReassignmentDetail
      );
    }

    if (detailClose) {
      detailClose.addEventListener(
        "click",
        closeReassignmentDetail
      );
    }

    if (detailSearch) {
      detailSearch.addEventListener(
        "input",
        function () {
          state.detailPage = 1;
          renderReassignmentDetail();
        }
      );
    }

    if (detailVehicle) {
      detailVehicle.addEventListener(
        "change",
        function () {
          state.detailPage = 1;
          renderReassignmentDetail();
        }
      );
    }

    [
      detailOrigin,
      detailDestination,
      detailSort
    ].forEach(function (control) {
      if (!control) {
        return;
      }

      control.addEventListener(
        "change",
        function () {
          state.detailPage = 1;
          renderReassignmentDetail();
        }
      );
    });

    if (detailPrev) {
      detailPrev.addEventListener(
        "click",
        function () {
          state.detailPage -= 1;
          renderReassignmentDetail();
        }
      );
    }

    if (detailNext) {
      detailNext.addEventListener(
        "click",
        function () {
          state.detailPage += 1;
          renderReassignmentDetail();
        }
      );
    }

    if (detailExport) {
      detailExport.addEventListener(
        "click",
        exportReassignments
      );
    }

    if (latestButton) {
      latestButton.addEventListener(
        "click",
        openLatestDecision
      );
    }

    document.addEventListener(
      "keydown",
      function (event) {
        if (
          event.key === "Escape"
          && !$("#reassignment-dialog")
            .classList.contains(
              "is-hidden"
            )
        ) {
          closeReassignmentDetail();
        }
      }
    );
  }

  async function restoreExecution() {
    if (['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(new URLSearchParams(location.search).get('dda'))) return;
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
      && stored.run.id
        === stored.runId
      && stored.run.result_json
    ) {
      try {
        await recoverRun(
          stored.run
        );
        return;
      } catch (error) {
        // Fallback a backend.
      }
    }

    if (stored.runId) {
      state.pollAttempts = 0;
      showRunning();
      pollCurrentRun();
    }
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
    setRunInUrl(
      normalized.runId
    );
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
  };

  window.dationDashboardCompleted = function (
    run,
    dataset,
    profile
  ) {
    var context = {
      runId: run.id,
      run: run,
      dataset: dataset,
      profile: profile,
      configuration: (
        runConfiguration(run)
      ),
      status: "completed",
      finishedAt: (
        run.finished_at
        || run.created_at
      )
    };

    clearPoll();
    saveContext(context);
    setRunInUrl(run.id);

    if (
      typeof window.dationNavigate
      === "function"
    ) {
      window.dationNavigate(
        "decision-dashboard"
      );
    }

    renderDashboard(
      run,
      dataset,
      profile
    );

    updateLatestDecisionCta(run);

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
  };

  window.dationDashboardExecutionError = (
    function (
      runId,
      message
    ) {
      clearPoll();

      saveContext(
        Object.assign(
          {},
          state.context || {},
          {
            runId: runId,
            status: "error"
          }
        )
      );

      showError(message);
    }
  );

  window.dationDashboardTimeout = (
    function (runId) {
      clearPoll();

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
    }
  );

  window.dationOpenLatestDecision = (
    openLatestDecision
  );

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