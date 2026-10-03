import {api, date, num} from "../shared.mjs";
import {createDropCard} from "./dropcard.mjs";
import {createGuideDrawer} from "./guide-drawer.mjs";
import {createPreviousDrawer} from "./library.mjs";
import {renderValidationPanel} from "./preflight-panel.mjs";
import {
  continueState,
  deriveCardState,
  technicalPreflightErrors,
} from "./selectors.mjs";
import {renderSystemBanner} from "./system-banner.mjs";
import {createValidationDrawer} from "./validation-report.mjs";

const MAX_BYTES = 10 * 1024 * 1024;

function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (value != null) {
    node.textContent = value;
  }
  return node;
}

function fileSize(bytes) {
  if (bytes == null) {
    return "—";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${num(bytes / 1024, 1)} KB`;
}

function dropTitle(kind) {
  return kind === "orders"
    ? "Arrastrá orders.csv acá"
    : "Arrastrá fleet.csv acá";
}

function clientFileProblem(file) {
  if (!file?.name?.toLowerCase().endsWith(".csv")) {
    return "Sólo se admiten archivos con extensión .csv.";
  }
  if (file.size > MAX_BYTES) {
    return "El archivo supera el límite de 10 MB.";
  }
  return null;
}

function makeHowItWorks() {
  const section = el("section", null, "dispatch-panel dispatch-how-compact");
  section.append(el("h2", "Cómo funciona"));

  const steps = el("div", null, "dispatch-how-compact-steps");
  [
    [
      "1",
      "Descargá la plantilla",
      "Usá el formato correcto desde el inicio.",
    ],
    [
      "2",
      "Completá lo necesario",
      "Las columnas opcionales pueden quedar vacías hasta necesitarlas.",
    ],
    [
      "3",
      "Subí y validá",
      "Dation revisa los datos antes de continuar.",
    ],
  ].forEach(([number, title, copy], index) => {
    const item = el("article");
    item.append(
      el("span", number, "dispatch-how-number"),
      el("div", null, "dispatch-how-copy"),
    );
    item.querySelector(".dispatch-how-copy").append(
      el("strong", title),
      el("small", copy),
    );
    steps.append(item);
    if (index < 2) {
      steps.append(el("span", "→", "dispatch-how-arrow"));
    }
  });
  section.append(steps);
  return section;
}

function makeFinalBar(onNext) {
  const bar = el("section", null, "dispatch-final-bar is-pending");
  const icon = el("span", "○", "dispatch-final-icon");
  const copy = el("div");
  const title = el("strong", "Completá los dos archivos");
  const description = el(
    "p",
    "Necesitamos órdenes y flota técnicamente válidas para continuar.",
  );
  copy.append(title, description);

  const button = document.createElement("button");
  button.type = "button";
  button.className = "dispatch-final-cta";
  button.textContent = "Ir al mapa de decisiones →";
  button.disabled = true;
  button.onclick = () => {
    if (!button.disabled) {
      onNext();
    }
  };

  bar.append(icon, copy, button);

  function update(result) {
    bar.className = `dispatch-final-bar is-${result.kind}`;
    button.disabled = !result.enabled;

    if (result.enabled) {
      icon.textContent = "✓";
      title.textContent = "Data Pack validado";
      description.textContent = (
        "Órdenes y Flota superaron la validación técnica. "
        + "Explorá en el mapa qué decisiones están habilitadas y cuál sigue en la cadena."
      );
      return;
    }

    if (result.kind === "error") {
      icon.textContent = "⛔";
      title.textContent = "Hay archivos que necesitan corrección";
      description.textContent = (
        "Corregí los problemas indicados antes de continuar."
      );
      return;
    }

    icon.textContent = "○";
    title.textContent = "Completá los dos archivos";
    description.textContent = result.message;
  }

  return {bar, update, button};
}

function currentFile(dataset, report, pendingFile) {
  if (report?.file) {
    return {
      name: report.file.name,
      size: report.file.size_bytes,
      rows: report.rows,
    };
  }
  if (dataset) {
    return {
      name: dataset.original_filename,
      size: dataset.size_bytes,
      rows: dataset.row_count,
    };
  }
  if (pendingFile) {
    return {
      name: pendingFile.name,
      size: pendingFile.size,
      rows: null,
    };
  }
  return null;
}

export async function mountUploadScreen(
  root,
  {
    state,
    persist,
    runPreflight,
    onNext,
  },
) {
  const local = {
    status: null,
    contracts: null,
    reports: {
      orders: null,
      fleet: null,
    },
    phases: {
      orders: "idle",
      fleet: "idle",
    },
    saveErrors: {
      orders: null,
      fleet: null,
    },
    duplicateNotice: {
      orders: null,
      fleet: null,
    },
    duplicate: {
      orders: false,
      fleet: false,
    },
    replacing: {
      orders: false,
      fleet: false,
    },
    pendingFiles: {
      orders: null,
      fleet: null,
    },
    libraries: {
      orders: [],
      fleet: [],
    },
  };

  root.replaceChildren();
  root.className = "dispatch dispatch-upload-screen";

  const heading = el("header", null, "dispatch-upload-heading-v3");
  const meta = el("div", null, "dispatch-upload-meta");
  meta.append(
    el("span", "LOGISTICS DATA PACK", "dispatch-kicker"),
    el("span", "Fase 1 · Datos", "dispatch-step-chip"),
  );
  heading.append(
    meta,
    el("h1", "Cargar datos"),
    el(
      "p",
      "Cargá Órdenes y Flota. Dation valida estructura, tipos y compatibilidad entre archivos antes de habilitar el mapa de decisiones.",
    ),
  );

  const banner = el("section");
  banner.hidden = true;

  const cards = el("div", null, "dispatch-upload-cards-v3");
  const validationRoot = el("section");
  const finalBar = makeFinalBar(onNext);

  root.append(
    heading,
    banner,
    makeHowItWorks(),
    cards,
    validationRoot,
    finalBar.bar,
  );

  let guide = null;
  let previousDrawer = null;
  let validationDrawer = null;
  const refs = {};

  function reportFor(kind) {
    return local.reports[kind] || state[kind]?.profile_json || null;
  }

  function finalState() {
    const result = continueState({
      storageAvailable: Boolean(local.status?.available),
      orders: state.orders,
      fleet: state.fleet,
      reports: {
        orders: reportFor("orders"),
        fleet: reportFor("fleet"),
      },
      preflight: state.preflight,
      phases: local.phases,
      saveErrors: local.saveErrors,
    });
    finalBar.update(result);
    window.dationSetDataReady(Boolean(result.enabled));
    return result;
  }

  function openValidation(kind, source) {
    const report = reportFor(kind);
    const file = currentFile(
      state[kind],
      report,
      local.pendingFiles[kind],
    );
    if (!report) {
      return;
    }
    validationDrawer.open({
      report,
      filename: file?.name || null,
      source,
      heading: Number(report.counts?.errors || 0)
        ? "Revisar problemas"
        : "Revisar observaciones",
    });
  }

  function openRelationValidation(source) {
    const errors = technicalPreflightErrors(state.preflight).map(
      (item) => ({
        ...item,
        message: item.detail || "Referencia no encontrada.",
        hint: (
          "Corregí el identificador para que exista en el archivo de flota."
        ),
      }),
    );
    validationDrawer.open({
      report: {
        errors,
        warnings: [],
      },
      source,
      heading: "Compatibilidad entre archivos",
    });
  }

  function renderValidation() {
    renderValidationPanel(
      validationRoot,
      {
        storageAvailable: Boolean(local.status?.available),
        datasets: {
          orders: state.orders,
          fleet: state.fleet,
        },
        reports: {
          orders: reportFor("orders"),
          fleet: reportFor("fleet"),
        },
        phases: local.phases,
        saveErrors: local.saveErrors,
        preflight: state.preflight,
        onReview: openValidation,
        onReviewRelations: openRelationValidation,
      },
    );
    finalState();
  }

  function renderCard(kind) {
    const ref = refs[kind];
    if (!ref) {
      return;
    }

    const report = reportFor(kind);
    if (report) {
      local.reports[kind] = report;
    }

    const cardState = deriveCardState({
      report,
      dataset: state[kind],
      saveError: local.saveErrors[kind],
      phase: local.phases[kind],
      storageAvailable: Boolean(local.status?.available),
      duplicate: local.duplicate[kind],
    });

    const fileInfo = currentFile(
      state[kind],
      report,
      local.pendingFiles[kind],
    );

    const busy = local.phases[kind] !== "idle";
    const showFile = Boolean(fileInfo) && !busy && !local.replacing[kind];
    const showDrop = !busy && (!showFile || local.replacing[kind]);

    ref.drop.hidden = !showDrop;
    ref.progress.hidden = !busy;
    ref.filePanel.hidden = !showFile;
    ref.actions.hidden = !showFile;

    if (busy) {
      ref.progressTitle.textContent = local.phases[kind] === "uploading"
        ? "Subiendo archivo…"
        : "Validando estructura…";
      ref.progressFile.textContent = local.pendingFiles[kind]?.name || "";
    }

    if (fileInfo) {
      ref.fileName.textContent = fileInfo.name;
      ref.fileState.textContent = cardState.label;
      ref.fileState.className = (
        `dispatch-file-state is-${cardState.tone}`
      );
      ref.fileMeta.textContent = [
        fileSize(fileInfo.size),
        fileInfo.rows != null
          ? `${num(fileInfo.rows)} registros`
          : null,
      ].filter(Boolean).join(" · ");
    }

    const issues = (
      Number(report?.counts?.errors || 0)
      + Number(report?.counts?.warnings || 0)
    );
    ref.reviewProblems.hidden = !issues;
    ref.reviewProblems.textContent = Number(report?.counts?.errors || 0)
      ? "Revisar problemas"
      : "Ver observaciones";

    ref.notice.hidden = true;
    ref.notice.replaceChildren();
    const notice = (
      local.duplicateNotice[kind]
      || local.saveErrors[kind]
      || (
        report?.valid
        && !state[kind]
        && !local.status?.available
        ? (
          "El archivo es válido, pero falta activar el almacenamiento "
          + "para poder continuar."
        )
        : null
      )
    );
    if (notice) {
      ref.notice.hidden = false;
      ref.notice.textContent = notice;
    }

    ref.card.classList.toggle(
      "is-file-valid",
      cardState.key === "valid" || cardState.key === "duplicate",
    );

    renderValidation();
  }

  async function loadLibrary(kind) {
    if (!local.status?.available) {
      local.libraries[kind] = [];
      return;
    }
    const response = await api(
      `/api/datasets?type=${kind}&limit=20&offset=0`,
    );
    local.libraries[kind] = response.items || [];

    if (state[kind]) {
      const refreshed = local.libraries[kind].find(
        (item) => item.id === state[kind].id,
      );
      if (refreshed) {
        state[kind] = refreshed;
        local.reports[kind] = refreshed.profile_json || null;
        persist();
      }
    }
  }

  async function refreshPreflight() {
    state.preflight = null;
    renderValidation();

    if (
      !state.orders
      || !state.fleet
      || !reportFor("orders")?.valid
      || !reportFor("fleet")?.valid
      || !local.status?.available
    ) {
      return;
    }

    try {
      await runPreflight();
    } catch (error) {
      state.preflight = {
        valid: false,
        errors: [
          {
            code: "PREFLIGHT_REQUEST_FAILED",
            detail: error.message,
          },
        ],
        warnings: [],
        anomalies: [],
      };
    }
    renderValidation();
  }

  async function selectPrevious(kind, dataset) {
    state[kind] = dataset;
    local.reports[kind] = dataset.profile_json || null;
    local.pendingFiles[kind] = null;
    local.saveErrors[kind] = null;
    local.duplicateNotice[kind] = null;
    local.duplicate[kind] = false;
    local.replacing[kind] = false;
    persist();
    renderCard(kind);
    await refreshPreflight();
  }

  function openPrevious(kind, source) {
    previousDrawer.open({
      kind,
      items: local.libraries[kind],
      selected: state[kind],
      source,
      onSelect: (dataset) => selectPrevious(kind, dataset),
    });
  }

  async function saveValid(kind, file) {
    if (!local.status?.available) {
      local.phases[kind] = "idle";
      renderCard(kind);
      return;
    }

    local.phases[kind] = "uploading";
    renderCard(kind);

    const form = new FormData();
    form.append("file", file);

    try {
      const stored = await api(
        `/api/datasets/upload?dataset_type=${kind}`,
        {
          method: "POST",
          body: form,
        },
      );

      const dataset = stored.dataset || stored.existing_dataset;
      state[kind] = dataset;
      local.reports[kind] = stored.validation || local.reports[kind];
      local.saveErrors[kind] = null;
      local.duplicate[kind] = Boolean(stored.duplicate);
      local.duplicateNotice[kind] = stored.duplicate
        ? (
          "Este archivo ya estaba cargado"
          + (
            dataset.created_at
              ? ` el ${date(dataset.created_at.slice(0, 10))}`
              : ""
          )
          + ". Usamos esa versión."
        )
        : null;
      local.replacing[kind] = false;
      local.pendingFiles[kind] = null;
      local.phases[kind] = "idle";
      persist();

      await loadLibrary(kind);
      renderCard(kind);
      refocusSuccess(kind);
      await refreshPreflight();
    } catch (error) {
      local.phases[kind] = "idle";
      local.saveErrors[kind] = error.message;
      state[kind] = null;
      persist();
      renderCard(kind);
    }
  }

  function refocusSuccess(kind) {
    const card = refs[kind].card;
    card.classList.remove("is-accepted");
    window.requestAnimationFrame(() => {
      card.classList.add("is-accepted");
      window.setTimeout(
        () => card.classList.remove("is-accepted"),
        500,
      );
    });
  }

  async function handleFile(kind, file) {
    const problem = clientFileProblem(file);
    local.pendingFiles[kind] = file;
    local.saveErrors[kind] = null;
    local.duplicate[kind] = false;
    local.duplicateNotice[kind] = null;
    local.replacing[kind] = false;

    if (problem) {
      state[kind] = null;
      local.reports[kind] = {
        valid: false,
        rows: 0,
        file: {
          name: file?.name || "archivo.csv",
          size_bytes: file?.size || 0,
        },
        errors: [
          {
            code: "INVALID_FILE",
            message: problem,
            hint: "Elegí un CSV válido de hasta 10 MB.",
          },
        ],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
      local.phases[kind] = "idle";
      persist();
      renderCard(kind);
      await refreshPreflight();
      return;
    }

    local.phases[kind] = "processing";
    renderCard(kind);

    try {
      const form = new FormData();
      form.append("file", file);
      const report = await api(
        `/api/datasets/validate?dataset_type=${kind}`,
        {
          method: "POST",
          body: form,
        },
      );

      local.reports[kind] = report;
      if (!report.valid) {
        state[kind] = null;
        local.phases[kind] = "idle";
        persist();
        renderCard(kind);
        await refreshPreflight();
        return;
      }

      await saveValid(kind, file);
    } catch (error) {
      state[kind] = null;
      local.phases[kind] = "idle";
      local.reports[kind] = {
        valid: false,
        rows: 0,
        file: {
          name: file.name,
          size_bytes: file.size,
        },
        errors: [
          {
            code: "VALIDATION_REQUEST_FAILED",
            message: error.message,
            hint: "Reintentá la carga. Si persiste, revisá la conexión.",
          },
        ],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
      persist();
      renderCard(kind);
      await refreshPreflight();
    }
  }

  try {
    const [status, contracts] = await Promise.all([
      api("/api/dispatch/status"),
      api("/api/dispatch/contracts"),
    ]);
    local.status = status;
    local.contracts = contracts;
    state.available = Boolean(status.available);
    renderSystemBanner(banner, status);

    guide = createGuideDrawer(contracts);
    previousDrawer = createPreviousDrawer();
    validationDrawer = createValidationDrawer();

    for (const kind of ["orders", "fleet"]) {
      const ref = createDropCard(kind, contracts.formats[kind]);
      refs[kind] = ref;
      cards.append(ref.card);

      ref.drop.onclick = () => ref.file.click();
      ref.file.onchange = () => {
        const selected = ref.file.files?.[0];
        if (selected) {
          handleFile(kind, selected);
        }
        ref.file.value = "";
      };

      ref.drop.ondragover = (event) => {
        event.preventDefault();
        ref.drop.classList.add("is-dragging");
        ref.drop.querySelector("strong").textContent = "Soltá para validar";
      };
      ref.drop.ondragleave = () => {
        ref.drop.classList.remove("is-dragging");
        ref.drop.querySelector("strong").textContent = dropTitle(kind);
      };
      ref.drop.ondrop = (event) => {
        event.preventDefault();
        ref.drop.classList.remove("is-dragging");
        ref.drop.querySelector("strong").textContent = dropTitle(kind);
        const selected = event.dataTransfer?.files?.[0];
        if (selected) {
          handleFile(kind, selected);
        }
      };

      ref.replace.onclick = () => {
        local.replacing[kind] = true;
        renderCard(kind);
        ref.file.click();
      };
      ref.reviewColumns.onclick = () => {
        guide.open(kind, ref.reviewColumns);
      };
      ref.reviewProblems.onclick = () => {
        openValidation(kind, ref.reviewProblems);
      };
      ref.previous.onclick = () => {
        openPrevious(kind, ref.previous);
      };

      if (state[kind]?.profile_json) {
        local.reports[kind] = state[kind].profile_json;
      }
      renderCard(kind);
    }

    await Promise.all([
      loadLibrary("orders"),
      loadLibrary("fleet"),
    ]);
    renderCard("orders");
    renderCard("fleet");
    await refreshPreflight();
  } catch (error) {
    state.available = false;
    local.status = {
      available: false,
      checks: [],
      message: (
        "No pudimos consultar el estado del sistema. "
        + "Recargá la pantalla para reintentar."
      ),
    };
    renderSystemBanner(banner, local.status);
    renderValidation();
  }
}
