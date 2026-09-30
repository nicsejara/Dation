(function () {
  "use strict";

  var DATA_STORAGE_KEY = (
    "dation.logistics.data-stage.v1"
  );

  var state = {
    dataset: null,
    profile: null,
    mode: "preset",
    objective: "min_cost",
    weights: {
      cost: 100,
      trips: 0
    },
    running: false
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

  function readStoredDataset() {
    if (
      window.dationDataStage
      && window.dationDataStage
        .activeDataset
      && window.dationDataStage
        .profile
    ) {
      return {
        dataset: (
          window.dationDataStage
            .activeDataset
        ),
        profile: (
          window.dationDataStage
            .profile
        )
      };
    }

    try {
      var raw = sessionStorage.getItem(
        DATA_STORAGE_KEY
      );

      if (!raw) {
        return null;
      }

      return JSON.parse(raw);
    } catch (error) {
      return null;
    }
  }

  function setText(id, value) {
    var element = (
      document.getElementById(id)
    );

    if (element) {
      element.textContent = value;
    }
  }

  function getModeLabel() {
    if (
      state.weights.cost === 100
      && state.weights.trips === 0
    ) {
      return "Priorizar ahorro";
    }

    if (
      state.weights.cost === 0
      && state.weights.trips === 100
    ) {
      return "Priorizar operación";
    }

    if (
      state.weights.cost === 50
      && state.weights.trips === 50
    ) {
      return "Equilibrar criterios";
    }

    return "Prioridad personalizada";
  }

  function getExplanation() {
    var cost = state.weights.cost;
    var trips = state.weights.trips;

    if (cost === 100) {
      return (
        "Esta configuración prioriza "
        + "exclusivamente el costo "
        + "estimado."
      );
    }

    if (trips === 100) {
      return (
        "Esta configuración prioriza "
        + "exclusivamente la reducción "
        + "de viajes."
      );
    }

    if (cost === trips) {
      return (
        "Costo y viajes tienen la misma "
        + "importancia dentro de la "
        + "decisión."
      );
    }

    if (cost > trips) {
      return (
        "La decisión favorece el ahorro, "
        + "manteniendo sensibilidad sobre "
        + "la cantidad de viajes."
      );
    }

    return (
      "La decisión favorece la reducción "
      + "de viajes, manteniendo sensibilidad "
      + "sobre el costo."
    );
  }

  function deriveConfiguration() {
    var cost = (
      state.weights.cost / 100
    );
    var trips = (
      state.weights.trips / 100
    );

    if (
      state.weights.cost === 100
      && state.weights.trips === 0
    ) {
      return {
        mode: "preset",
        objective: "min_cost",
        weights: {
          cost: 1,
          trips: 0
        }
      };
    }

    if (
      state.weights.cost === 0
      && state.weights.trips === 100
    ) {
      return {
        mode: "preset",
        objective: "min_trips",
        weights: {
          cost: 0,
          trips: 1
        }
      };
    }

    return {
      mode: "custom",
      objective: "custom",
      weights: {
        cost: cost,
        trips: trips
      }
    };
  }

  function syncPresetSelection() {
    $$("[data-preset]")
      .forEach(function (button) {
        var preset = (
          button.getAttribute(
            "data-preset"
          )
        );

        var selected = false;

        if (
          preset === "min_cost"
          && state.weights.cost === 100
        ) {
          selected = true;
        }

        if (
          preset === "min_trips"
          && state.weights.trips === 100
        ) {
          selected = true;
        }

        if (
          preset === "balanced"
          && state.weights.cost === 50
          && state.weights.trips === 50
        ) {
          selected = true;
        }

        button.classList.toggle(
          "is-selected",
          selected
        );
      });
  }

  function renderDatasetContext() {
    var dataset = state.dataset;
    var profile = state.profile;

    var runButton = (
      $("#decision-review-run")
    );

    if (!dataset || !profile) {
      setText(
        "decision-dataset-name",
        "Dataset no disponible"
      );
      setText(
        "decision-dataset-meta",
        (
          "Volvé a Cargar data y validá "
          + "un dataset para continuar."
        )
      );

      if (runButton) {
        runButton.disabled = true;
      }

      return;
    }

    setText(
      "decision-dataset-name",
      dataset.original_filename
    );

    var rows = (
      profile.validation
      && profile.validation.rows
    );

    setText(
      "decision-dataset-meta",
      (
        formatNumber(rows)
        + " filas validadas · "
        + (
          profile.validation
          && profile.validation.schema
            ? profile.validation.schema
            : "schema logístico"
        )
      )
    );

    if (runButton) {
      runButton.disabled = false;
    }
  }

  function renderConfiguration() {
    var cost = state.weights.cost;
    var trips = state.weights.trips;

    var costSlider = (
      $("#decision-cost-slider")
    );
    var tripsSlider = (
      $("#decision-trips-slider")
    );

    if (costSlider) {
      costSlider.value = String(cost);
    }

    if (tripsSlider) {
      tripsSlider.value = String(trips);
    }

    setText(
      "decision-cost-value",
      cost + "%"
    );
    setText(
      "decision-trips-value",
      trips + "%"
    );
    setText(
      "decision-weight-sum",
      "100% asignado"
    );
    setText(
      "decision-mode-label",
      getModeLabel()
    );
    setText(
      "decision-allocation-label",
      (
        "Costo "
        + cost
        + "% · Viajes "
        + trips
        + "%"
      )
    );
    setText(
      "decision-weight-explanation",
      getExplanation()
    );
    setText(
      "decision-execution-title",
      getModeLabel()
    );
    setText(
      "decision-execution-copy",
      (
        "Costo "
        + cost
        + "% · Viajes "
        + trips
        + "% · cálculo determinístico"
      )
    );

    var costBar = (
      $("#decision-allocation-cost")
    );
    var tripsBar = (
      $("#decision-allocation-trips")
    );

    if (costBar) {
      costBar.style.width = (
        cost + "%"
      );
    }

    if (tripsBar) {
      tripsBar.style.width = (
        trips + "%"
      );
    }

    syncPresetSelection();
    renderDatasetContext();
  }

  function applyPreset(preset) {
    if (preset === "min_trips") {
      state.mode = "preset";
      state.objective = "min_trips";
      state.weights = {
        cost: 0,
        trips: 100
      };
    } else if (preset === "balanced") {
      state.mode = "custom";
      state.objective = "custom";
      state.weights = {
        cost: 50,
        trips: 50
      };
    } else {
      state.mode = "preset";
      state.objective = "min_cost";
      state.weights = {
        cost: 100,
        trips: 0
      };
    }

    renderConfiguration();
  }

  function setCostWeight(value) {
    var bounded = Math.max(
      0,
      Math.min(
        100,
        Math.round(
          Number(value)
        )
      )
    );

    state.mode = "custom";
    state.objective = "custom";
    state.weights = {
      cost: bounded,
      trips: 100 - bounded
    };

    renderConfiguration();
  }

  function setTripsWeight(value) {
    var bounded = Math.max(
      0,
      Math.min(
        100,
        Math.round(
          Number(value)
        )
      )
    );

    state.mode = "custom";
    state.objective = "custom";
    state.weights = {
      cost: 100 - bounded,
      trips: bounded
    };

    renderConfiguration();
  }

  function openModal() {
    var modal = (
      $("#decision-confirm-modal")
    );

    if (
      !modal
      || !state.dataset
      || !state.profile
    ) {
      return;
    }

    var config = deriveConfiguration();

    setText(
      "confirm-dataset-name",
      state.dataset.original_filename
    );

    setText(
      "confirm-dataset-meta",
      (
        formatNumber(
          state.profile.validation
            && state.profile.validation.rows
        )
        + " filas validadas · "
        + (
          state.profile.validation
          && state.profile.validation.schema
            ? state.profile.validation.schema
            : "schema logístico"
        )
      )
    );

    setText(
      "confirm-mode",
      (
        config.mode === "preset"
          ? getModeLabel()
          : "Personalizado"
      )
    );
    setText(
      "confirm-cost",
      state.weights.cost + "%"
    );
    setText(
      "confirm-trips",
      state.weights.trips + "%"
    );

    var error = (
      $("#decision-confirm-error")
    );

    if (error) {
      error.textContent = "";
      error.className = (
        "inline-status is-hidden"
      );
    }

    modal.classList.remove(
      "is-hidden"
    );

    document.body.classList.add(
      "decision-modal-open"
    );

    var confirmButton = (
      $("#decision-confirm-run")
    );

    if (confirmButton) {
      window.setTimeout(
        function () {
          confirmButton.focus();
        },
        50
      );
    }
  }

  function closeModal() {
    if (state.running) {
      return;
    }

    var modal = (
      $("#decision-confirm-modal")
    );

    if (modal) {
      modal.classList.add(
        "is-hidden"
      );
    }

    document.body.classList.remove(
      "decision-modal-open"
    );
  }

  function showModalError(message) {
    var element = (
      $("#decision-confirm-error")
    );

    if (!element) {
      return;
    }

    element.textContent = message;
    element.className = (
      "inline-status is-error"
    );
  }

  async function requestRun(
    datasetId,
    configuration
  ) {
    var response = await fetch(
      "/api/runs/"
      + encodeURIComponent(datasetId),
      {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": (
            "application/json"
          )
        },
        body: JSON.stringify(
          configuration
        )
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
      var detail = (
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

      throw new Error(detail);
    }

    return payload;
  }

  async function executeDecision() {
    if (
      state.running
      || !state.dataset
      || !state.profile
    ) {
      return;
    }

    var confirmButton = (
      $("#decision-confirm-run")
    );
    var reviewButton = (
      $("#decision-review-run")
    );

    state.running = true;

    if (confirmButton) {
      confirmButton.disabled = true;
      confirmButton.textContent = (
        "Calculando decisión…"
      );
      confirmButton.classList.add(
        "is-loading"
      );
    }

    if (reviewButton) {
      reviewButton.disabled = true;
    }

    try {
      var configuration = (
        deriveConfiguration()
      );

      var run = await requestRun(
        state.dataset.id,
        configuration
      );

      window.dationDecisionStage = {
        run: run,
        dataset: state.dataset,
        profile: state.profile,
        configuration: configuration
      };

      if (
        typeof window
          .dationConsumeDecisionRun
        === "function"
      ) {
        window.dationConsumeDecisionRun(
          run,
          state.dataset,
          state.profile
        );
      } else {
        window.dispatchEvent(
          new CustomEvent(
            "dation:run-ready",
            {
              detail: {
                run: run,
                dataset: state.dataset,
                profile: state.profile
              }
            }
          )
        );
      }

      closeModal();
    } catch (error) {
      showModalError(
        error.message
        || (
          "No se pudo ejecutar "
          + "la decisión."
        )
      );
    } finally {
      state.running = false;

      if (confirmButton) {
        confirmButton.disabled = false;
        confirmButton.classList.remove(
          "is-loading"
        );
        confirmButton.innerHTML = (
          "Confirmar y ejecutar "
          + '<span aria-hidden="true">→</span>'
        );
      }

      if (reviewButton) {
        reviewButton.disabled = (
          !state.dataset
          || !state.profile
        );
      }
    }
  }

  function hydrateDataset(
    dataset,
    profile
  ) {
    if (!dataset || !profile) {
      return;
    }

    state.dataset = dataset;
    state.profile = profile;

    renderDatasetContext();
  }

  function boot() {
    var restored = readStoredDataset();

    if (
      restored
      && restored.dataset
      && restored.profile
    ) {
      hydrateDataset(
        restored.dataset,
        restored.profile
      );
    }

    $$("[data-preset]")
      .forEach(function (button) {
        button.addEventListener(
          "click",
          function () {
            applyPreset(
              button.getAttribute(
                "data-preset"
              )
            );
          }
        );
      });

    var costSlider = (
      $("#decision-cost-slider")
    );
    var tripsSlider = (
      $("#decision-trips-slider")
    );

    if (costSlider) {
      costSlider.addEventListener(
        "input",
        function (event) {
          setCostWeight(
            event.target.value
          );
        }
      );
    }

    if (tripsSlider) {
      tripsSlider.addEventListener(
        "input",
        function (event) {
          setTripsWeight(
            event.target.value
          );
        }
      );
    }

    var reviewButton = (
      $("#decision-review-run")
    );

    if (reviewButton) {
      reviewButton.addEventListener(
        "click",
        function () {
          if (
            !state.dataset
            || !state.profile
          ) {
            if (
              typeof window.dationNavigate
              === "function"
            ) {
              window.dationNavigate(
                "logistics-data"
              );
            }

            return;
          }

          openModal();
        }
      );
    }

    $$("[data-close-decision-modal]")
      .forEach(function (button) {
        button.addEventListener(
          "click",
          closeModal
        );
      });

    var confirmButton = (
      $("#decision-confirm-run")
    );

    if (confirmButton) {
      confirmButton.addEventListener(
        "click",
        executeDecision
      );
    }

    document.addEventListener(
      "keydown",
      function (event) {
        if (event.key === "Escape") {
          closeModal();
        }
      }
    );

    window.addEventListener(
      "dation:dataset-ready",
      function (event) {
        hydrateDataset(
          event.detail
            && event.detail.dataset,
          event.detail
            && event.detail.profile
        );
      }
    );

    renderConfiguration();
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