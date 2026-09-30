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

    if (
      typeof window
        .dationConsumeDecisionRun
      === "function"
    ) {
      await window
        .dationConsumeDecisionRun(
          run,
          dataset,
          profile
        );
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

    renderEnhancedDashboard(run);
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

    if (!stored && urlRunId) {
      stored = {
        runId: urlRunId,
        status: "running"
      };
    }

    if (
      urlRunId
      && stored.runId !== urlRunId
    ) {
      stored = Object.assign(
        {},
        stored,
        {
          runId: urlRunId,
          status: "running"
        }
      );
    }

    saveContext(stored);

    if (
      stored.status === "running"
      || stored.status === "timeout"
    ) {
      if (
        typeof window.dationNavigate
        === "function"
      ) {
        window.dationNavigate(
          "decision-dashboard"
        );
      }

      showRunning();
      pollCurrentRun();
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

    bindComparison();
  }

  function boot() {
    bindControls();
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