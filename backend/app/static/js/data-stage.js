(function () {
  "use strict";

  var state = {
    datasets: [],
    activeDataset: null,
    profile: null,
    dragDepth: 0
  };

  function $(selector) {
    return document.querySelector(selector);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatNumber(value, digits) {
    digits = digits == null ? 0 : digits;

    if (
      value === null
      || value === undefined
      || Number.isNaN(Number(value))
    ) {
      return "—";
    }

    return new Intl.NumberFormat(
      "es-AR",
      { maximumFractionDigits: digits }
    ).format(Number(value));
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

  function bytes(value) {
    var size = Number(value || 0);

    if (!size) {
      return "0 KB";
    }

    if (size < 1024) {
      return size + " B";
    }

    if (size < 1024 * 1024) {
      return (size / 1024).toFixed(1) + " KB";
    }

    return (
      (size / (1024 * 1024)).toFixed(1)
      + " MB"
    );
  }

  async function request(url, options) {
    options = options || {};

    var response = await fetch(
      url,
      Object.assign(
        {
          credentials: "same-origin"
        },
        options
      )
    );

    var contentType = (
      response.headers.get("content-type")
      || ""
    );

    var payload = (
      contentType.includes("application/json")
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

  function showProgress(message, type) {
    type = type || "loading";

    var element = $("#upload-progress");

    if (!element) {
      return;
    }

    element.textContent = message;
    element.className = "inline-status";

    if (type === "loading") {
      element.classList.add("is-loading");
    }

    if (type === "success") {
      element.classList.add("is-success");
    }

    if (type === "error") {
      element.classList.add("is-error");
    }
  }

  function hideProgress() {
    var element = $("#upload-progress");

    if (!element) {
      return;
    }

    element.textContent = "";
    element.className = (
      "inline-status is-hidden"
    );
  }

  function setDropState(active) {
    var dropzone = $("#upload-dropzone");

    if (!dropzone) {
      return;
    }

    dropzone.classList.toggle(
      "is-dragging",
      Boolean(active)
    );
  }

  function setText(id, value) {
    var element = (
      document.getElementById(id)
    );

    if (element) {
      element.textContent = value;
    }
  }

  function setActiveDatasetSummary(
    dataset,
    status
  ) {
    status = status || "Validando…";

    var card = $("#active-dataset-card");
    var name = $("#active-dataset-name");
    var meta = $("#active-dataset-meta");
    var datasetStatus = (
      $("#active-dataset-status")
    );
    var configState = (
      $("#data-config-state")
    );

    if (!card || !name || !meta) {
      return;
    }

    if (!dataset) {
      card.classList.add("is-empty");
      name.textContent = (
        "Ningún dataset seleccionado"
      );
      meta.textContent = (
        "Cargá un archivo o seleccioná "
        + "uno existente para iniciar "
        + "la validación."
      );

      if (datasetStatus) {
        datasetStatus.textContent = "—";
      }

      if (configState) {
        configState.innerHTML = (
          '<span class="status-dot '
          + 'status-dot--pending"></span>'
          + " Dataset pendiente"
        );
      }

      return;
    }

    card.classList.remove("is-empty");
    name.textContent = (
      dataset.original_filename
    );

    meta.textContent = (
      formatNumber(dataset.row_count)
      + " filas · "
      + formatNumber(dataset.column_count)
      + " columnas · "
      + bytes(dataset.size_bytes)
      + " · "
      + formatDate(dataset.created_at)
    );

    if (datasetStatus) {
      datasetStatus.textContent = status;
    }

    if (configState) {
      configState.innerHTML = (
        '<span class="status-dot '
        + 'status-dot--pending"></span>'
        + " Validando evidencia"
      );
    }
  }

  function renderDatasetLibrary() {
    var container = (
      $("#workspace-dataset-list")
    );

    if (!container) {
      return;
    }

    if (!state.datasets.length) {
      container.innerHTML = (
        '<div class="empty-state '
        + 'empty-state--compact">'
        + "Todavía no hay datasets "
        + "almacenados."
        + "</div>"
      );
      return;
    }

    container.innerHTML = (
      state.datasets
        .slice(0, 6)
        .map(function (dataset) {
          var active = (
            state.activeDataset
            && state.activeDataset.id
              === dataset.id
          );

          return (
            '<div class="dataset-row '
            + (active ? "is-active" : "")
            + '">'
            + '<div class="dataset-row-icon">'
            + "CSV</div>"
            + "<div>"
            + "<strong>"
            + escapeHtml(
                dataset.original_filename
              )
            + "</strong>"
            + "<small>"
            + formatNumber(
                dataset.row_count
              )
            + " filas · "
            + formatNumber(
                dataset.column_count
              )
            + " columnas · "
            + bytes(
                dataset.size_bytes
              )
            + "</small>"
            + "</div>"
            + "<small>"
            + formatDate(
                dataset.created_at
              )
            + "</small>"
            + '<button class="dataset-action" '
            + 'type="button" '
            + 'data-data-stage-dataset="'
            + escapeHtml(dataset.id)
            + '">'
            + (
              active
                ? "Seleccionado"
                : "Usar dataset"
            )
            + "</button>"
            + "</div>"
          );
        })
        .join("")
    );
  }

  async function loadDatasets() {
    var container = (
      $("#workspace-dataset-list")
    );

    if (container) {
      container.innerHTML = (
        '<div class="empty-state '
        + 'empty-state--compact">'
        + "Cargando datasets…"
        + "</div>"
      );
    }

    var response = await request(
      "/api/datasets?limit=80"
    );

    state.datasets = (
      Array.isArray(response.items)
        ? response.items
        : []
    );

    renderDatasetLibrary();

    return state.datasets;
  }

  function renderPreview(rows) {
    var head = $("#preview-table-head");
    var body = $("#preview-table-body");

    if (!head || !body) {
      return;
    }

    if (!rows || !rows.length) {
      head.innerHTML = "";
      body.innerHTML = (
        "<tr><td>"
        + "Sin registros para previsualizar."
        + "</td></tr>"
      );
      return;
    }

    var columns = Object.keys(rows[0]);

    head.innerHTML = (
      "<tr>"
      + columns
        .map(function (column) {
          return (
            "<th>"
            + escapeHtml(column)
            + "</th>"
          );
        })
        .join("")
      + "</tr>"
    );

    body.innerHTML = (
      rows
        .map(function (row) {
          return (
            "<tr>"
            + columns
              .map(function (column) {
                return (
                  "<td>"
                  + escapeHtml(row[column])
                  + "</td>"
                );
              })
              .join("")
            + "</tr>"
          );
        })
        .join("")
    );
  }

  function renderValidation(payload) {
    var panel = $("#dataset-profile-panel");

    if (!panel) {
      return;
    }

    var dataset = payload.dataset;
    var validation = payload.validation;
    var profile = payload.profile;

    panel.classList.remove("is-hidden");

    setText(
      "active-dataset-status",
      "Listo"
    );

    var configState = (
      $("#data-config-state")
    );

    if (configState) {
      configState.innerHTML = (
        '<span class="status-dot '
        + 'status-dot--live"></span>'
        + " Datos validados"
      );
    }

    setText(
      "profile-dataset-title",
      dataset.original_filename
    );
    setText(
      "profile-created",
      formatDate(dataset.created_at)
    );
    setText(
      "profile-rows",
      formatNumber(validation.rows)
    );
    setText(
      "profile-columns",
      formatNumber(validation.columns)
    );
    setText(
      "profile-size",
      bytes(dataset.size_bytes)
    );
    setText(
      "profile-schema",
      validation.schema
    );
    setText(
      "profile-id",
      dataset.id
        ? dataset.id.slice(0, 8) + "…"
        : "—"
    );
    setText(
      "profile-hash-short",
      dataset.sha256
        ? dataset.sha256.slice(0, 12)
          + "…"
        : "—"
    );

    setText(
      "validator-schema-status",
      validation.missing_columns
      && validation.missing_columns.length
        ? "Revisar"
        : "Compatible"
    );

    setText(
      "validator-columns-status",
      formatNumber(validation.columns)
      + " / 14"
    );

    setText(
      "validator-columns-detail",
      validation.missing_columns
      && validation.missing_columns.length
        ? (
          "Faltan: "
          + validation.missing_columns
            .join(", ")
        )
        : (
          "Todas las columnas requeridas "
          + "están presentes"
        )
    );

    setText(
      "validator-empty-status",
      formatNumber(
        validation.empty_required_cells
        == null
          ? 0
          : validation.empty_required_cells
      )
    );

    setText(
      "validator-duplicates-status",
      formatNumber(
        validation.duplicate_shipments
        == null
          ? 0
          : validation.duplicate_shipments
      )
    );

    setText(
      "profile-shipments",
      formatNumber(profile.shipments)
    );
    setText(
      "profile-units",
      formatNumber(profile.total_units)
    );
    setText(
      "profile-weight",
      formatNumber(
        profile.total_weight_kg
      )
      + " kg"
    );
    setText(
      "profile-origins",
      formatNumber(profile.origins)
    );
    setText(
      "profile-destinations",
      formatNumber(profile.destinations)
    );
    setText(
      "profile-vehicles",
      formatNumber(profile.vehicle_types)
    );
    setText(
      "profile-distance",
      formatNumber(
        profile.average_distance_km,
        1
      )
      + " km"
    );

    var range = (
      profile.dispatch_date_range
    );

    setText(
      "profile-date-range",
      range
      && range.from
      && range.to
        ? range.from + " → " + range.to
        : "—"
    );

    setText(
      "profile-hash",
      dataset.sha256 || "—"
    );

    var priorities = (
      $("#priority-distribution")
    );

    if (priorities) {
      var items = Object.entries(
        profile.priority_distribution
        || {}
      );

      priorities.innerHTML = (
        items.length
          ? items
            .map(function (item) {
              return (
                '<span class="priority-item">'
                + escapeHtml(item[0])
                + "<strong>"
                + formatNumber(item[1])
                + "</strong>"
                + "</span>"
              );
            })
            .join("")
          : (
            '<span class="priority-item">'
            + "Sin datos de prioridad"
            + "</span>"
          )
      );
    }

    renderPreview(
      payload.preview || []
    );

    var continueButton = (
      $("#continue-to-decision")
    );

    if (continueButton) {
      continueButton.disabled = false;
    }

    if (
      typeof window.dationSetDataReady
      === "function"
    ) {
      window.dationSetDataReady(true);
    }

    window.dationDataStage = {
      activeDataset: dataset,
      profile: payload
    };

    window.dispatchEvent(
      new CustomEvent(
        "dation:dataset-ready",
        {
          detail: {
            dataset: dataset,
            profile: payload
          }
        }
      )
    );

    window.setTimeout(
      function () {
        panel.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      },
      100
    );
  }

  async function selectDataset(
    datasetId
  ) {
    var dataset = (
      state.datasets.find(
        function (item) {
          return item.id === datasetId;
        }
      )
    );

    if (!dataset) {
      throw new Error(
        "No se encontró el dataset "
        + "seleccionado."
      );
    }

    state.activeDataset = dataset;
    state.profile = null;

    setActiveDatasetSummary(
      dataset,
      "Validando…"
    );

    renderDatasetLibrary();

    var continueButton = (
      $("#continue-to-decision")
    );

    if (continueButton) {
      continueButton.disabled = true;
    }

    if (
      typeof window.dationSetDataReady
      === "function"
    ) {
      window.dationSetDataReady(false);
    }

    var panel = $("#dataset-profile-panel");

    if (panel) {
      panel.classList.add("is-hidden");
    }

    var profile = await request(
      "/api/datasets/"
      + encodeURIComponent(dataset.id)
      + "/profile"
    );

    state.profile = profile;
    renderValidation(profile);

    return profile;
  }

  async function uploadFile(file) {
    if (!file) {
      return;
    }

    if (
      !file.name
        .toLowerCase()
        .endsWith(".csv")
    ) {
      showProgress(
        "Sólo se admiten archivos "
        + "con extensión .csv.",
        "error"
      );
      return;
    }

    var maxBytes = (
      10 * 1024 * 1024
    );

    if (file.size > maxBytes) {
      showProgress(
        "El archivo supera el límite "
        + "actual de 10 MB.",
        "error"
      );
      return;
    }

    var browse = $("#browse-file");

    if (browse) {
      browse.disabled = true;
      browse.textContent = (
        "Validando archivo…"
      );
    }

    showProgress(
      "Subiendo, validando estructura "
      + "y almacenando evidencia…",
      "loading"
    );

    try {
      var body = new FormData();
      body.append("file", file);

      var result = await request(
        "/api/datasets/upload",
        {
          method: "POST",
          body: body
        }
      );

      await loadDatasets();

      var datasetId = (
        result.duplicate
          ? result.existing_dataset.id
          : result.dataset.id
      );

      await selectDataset(datasetId);

      showProgress(
        result.duplicate
          ? (
            "El archivo ya existía. "
            + "Se reutilizó la evidencia "
            + "almacenada."
          )
          : (
            "Archivo validado correctamente. "
            + result.validation.rows
            + " filas y "
            + result.validation.columns
            + " columnas listas."
          ),
        "success"
      );
    } catch (error) {
      showProgress(
        error.message
        || "No se pudo procesar el archivo.",
        "error"
      );
    } finally {
      if (browse) {
        browse.disabled = false;
        browse.textContent = (
          "Seleccionar archivo CSV"
        );
      }

      var input = $("#dataset-file");

      if (input) {
        input.value = "";
      }
    }
  }

  function bindDropzone() {
    var input = $("#dataset-file");
    var browse = $("#browse-file");
    var dropzone = $("#upload-dropzone");

    if (!input || !browse || !dropzone) {
      return;
    }

    browse.addEventListener(
      "click",
      function (event) {
        event.preventDefault();
        input.click();
      }
    );

    input.addEventListener(
      "change",
      function () {
        uploadFile(
          input.files
          && input.files[0]
        );
      }
    );

    dropzone.addEventListener(
      "dragenter",
      function (event) {
        event.preventDefault();
        state.dragDepth += 1;
        setDropState(true);
      }
    );

    dropzone.addEventListener(
      "dragover",
      function (event) {
        event.preventDefault();

        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = (
            "copy"
          );
        }

        setDropState(true);
      }
    );

    dropzone.addEventListener(
      "dragleave",
      function (event) {
        event.preventDefault();

        state.dragDepth = Math.max(
          0,
          state.dragDepth - 1
        );

        if (state.dragDepth === 0) {
          setDropState(false);
        }
      }
    );

    dropzone.addEventListener(
      "drop",
      function (event) {
        event.preventDefault();
        state.dragDepth = 0;
        setDropState(false);

        var file = (
          event.dataTransfer
          && event.dataTransfer.files
          && event.dataTransfer.files[0]
        );

        uploadFile(file);
      }
    );
  }

  function bindLibrary() {
    document.addEventListener(
      "click",
      async function (event) {
        var button = (
          event.target.closest(
            "[data-data-stage-dataset]"
          )
        );

        if (!button) {
          return;
        }

        event.preventDefault();
        event.stopPropagation();

        button.disabled = true;
        var original = button.textContent;
        button.textContent = "Validando…";

        try {
          await selectDataset(
            button.getAttribute(
              "data-data-stage-dataset"
            )
          );
        } catch (error) {
          showProgress(
            error.message,
            "error"
          );
        } finally {
          button.disabled = false;
          button.textContent = original;
        }
      }
    );
  }

  function bindContinue() {
    var button = (
      $("#continue-to-decision")
    );

    if (!button) {
      return;
    }

    button.addEventListener(
      "click",
      function (event) {
        event.preventDefault();

        if (
          !state.activeDataset
          || !state.profile
        ) {
          showProgress(
            "Primero seleccioná y validá "
            + "un dataset.",
            "error"
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
    );
  }

  async function boot() {
    bindDropzone();
    bindLibrary();
    bindContinue();

    setActiveDatasetSummary(null);
    hideProgress();

    try {
      await loadDatasets();
    } catch (error) {
      var container = (
        $("#workspace-dataset-list")
      );

      if (container) {
        container.innerHTML = (
          '<div class="empty-state '
          + 'empty-state--compact">'
          + "No se pudieron cargar los datasets. "
          + escapeHtml(error.message)
          + "</div>"
        );
      }
    }
  }

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      { once: true }
    );
  } else {
    boot();
  }
})();