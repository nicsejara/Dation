import {api, date, num, post} from "../shared.mjs";
import {createDropCard} from "./dropcard.mjs";
import {createGuideDrawer} from "./guide-drawer.mjs";
import {renderLibrary} from "./library.mjs";
import {renderUnderstood} from "./metrics.mjs";
import {renderPreflight} from "./preflight-panel.mjs";
import {
  continueState,
  deriveCardState,
  stepTone,
} from "./selectors.mjs";
import {createSummaryPanel} from "./summary-panel.mjs";
import {renderSystemBanner} from "./system-banner.mjs";
import {renderValidationReport} from "./validation-report.mjs";

const MAX_BYTES = 10 * 1024 * 1024;
const INTRO_KEY = "dation.dispatch.ingestion.intro.dismissed.v1";

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
    return "";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${num(bytes / 1024, 1)} KB`;
}

function todayTime(value) {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  return new Intl.DateTimeFormat(
    "es-AR",
    {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(parsed);
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

function cardReport(dataset, localReport) {
  return localReport || dataset?.profile_json || null;
}

function currentFile(kind, dataset, report) {
  if (dataset) {
    return {
      name: dataset.original_filename,
      size: dataset.size_bytes,
      createdAt: dataset.created_at,
    };
  }
  if (report?.file) {
    return {
      name: report.file.name,
      size: report.file.size_bytes,
      createdAt: null,
    };
  }
  return null;
}

function makeStepper() {
  const nav = el("nav", null, "dispatch-ingestion-stepper");
  nav.setAttribute("aria-label", "Progreso de la carga");
  const items = {};
  [
    ["orders", "1", "Órdenes", "dispatch-upload-orders"],
    ["fleet", "2", "Flota", "dispatch-upload-fleet"],
    ["review", "3", "Revisión", "dispatch-upload-review"],
  ].forEach(([key, number, label, target]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.step = key;
    button.append(
      el("span", number),
      el("strong", label),
    );
    button.onclick = () => {
      document.getElementById(target)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    };
    nav.append(button);
    items[key] = button;
  });
  return {nav, items};
}

function updateStepper(stepper, state, reports, preflight) {
  for (const kind of ["orders", "fleet"]) {
    const tone = stepTone({
      dataset: state[kind],
      report: reports[kind],
      kind,
    });
    stepper.items[kind].className = `is-${tone}`;
  }
  const reviewTone = stepTone({
    preflight,
    kind: "review",
  });
  stepper.items.review.className = `is-${reviewTone}`;
}

function makeIntroduction(onSample, onGuide, onDismiss) {
  const section = el("section", null, "dispatch-panel dispatch-intro");
  const copy = el("div");
  copy.append(
    el("span", "Primera vez", "dispatch-kicker"),
    el("h2", "Prepará tus datos en pocos minutos"),
    el(
      "p",
      (
        "Las órdenes cambian en cada corrida. "
        + "La flota se carga una vez y se reutiliza."
      ),
    ),
  );

  const close = document.createElement("button");
  close.type = "button";
  close.className = "dispatch-intro-close";
  close.setAttribute("aria-label", "Cerrar introducción");
  close.textContent = "×";
  close.onclick = onDismiss;

  const steps = el("div", null, "dispatch-intro-steps");
  [
    "Descargá la plantilla",
    "Completala sin cambiar los encabezados",
    "Subí el CSV y lo validamos al instante",
  ].forEach((value, index) => {
    const item = el("div");
    item.append(
      el("span", String(index + 1)),
      el("strong", value),
    );
    steps.append(item);
  });

  const actions = el("div", null, "dispatch-actions");
  const sample = document.createElement("button");
  sample.type = "button";
  sample.className = "dispatch-primary-action";
  sample.textContent = "Probar con datos de ejemplo";
  sample.onclick = onSample;

  const guide = document.createElement("button");
  guide.type = "button";
  guide.className = "dispatch-text-action";
  guide.textContent = "Ver la guía de formato";
  guide.onclick = () => onGuide("orders", guide);
  actions.append(sample, guide);

  section.append(copy, close, steps, actions);
  return section;
}

export async function mountUploadScreen(
  root,
  {
    state,
    persist,
    runPreflight,
    onNext,
    isReady,
  },
) {
  const local = {
    status: null,
    contracts: null,
    reports: {
      orders: null,
      fleet: null,
    },
    validating: {
      orders: false,
      fleet: false,
    },
    saveErrors: {
      orders: null,
      fleet: null,
    },
    duplicate: {
      orders: false,
      fleet: false,
    },
    duplicateNotice: {
      orders: null,
      fleet: null,
    },
    replacing: {
      orders: false,
      fleet: false,
    },
    libraries: {
      orders: [],
      fleet: [],
    },
    queries: {
      orders: "",
      fleet: "",
    },
  };

  root.replaceChildren();
  root.className = "dispatch dispatch-upload-screen";

  const heading = el("header", null, "dispatch-upload-heading");
  const headingCopy = el("div");
  headingCopy.append(
    el("span", "Paso 1 de 3", "dispatch-step-chip"),
    el("h1", "Cargar datos"),
    el(
      "p",
      (
        "Para calcular el plan necesitamos dos archivos: "
        + "qué hay que entregar y con qué camiones."
      ),
    ),
  );
  const guideButton = document.createElement("button");
  guideButton.type = "button";
  guideButton.className = "dispatch-guide-button";
  guideButton.textContent = "ⓘ Guía de formato";
  heading.append(headingCopy, guideButton);

  const stepper = makeStepper();
  const banner = el("section");
  banner.hidden = true;
  const introSlot = el("div");
  const shell = el("div", null, "dispatch-ingestion-layout");
  const main = el("main", null, "dispatch-ingestion-main");
  const preflightRoot = el("section");
  const common = document.createElement("details");
  common.className = "dispatch-common-errors";
  const commonSummary = document.createElement("summary");
  commonSummary.textContent = "Errores frecuentes y cómo resolverlos";
  common.append(
    commonSummary,
    el(
      "p",
      (
        "Fechas inválidas, IDs repetidos, distancias distintas para la misma ruta "
        + "y encabezados cambiados se informan juntos para que puedas corregirlos "
        + "en una sola pasada."
      ),
    ),
  );
  const summary = createSummaryPanel(() => {
    if (!summary.button.disabled) {
      onNext();
    }
  });
  shell.append(main, summary.panel);
  root.append(
    heading,
    stepper.nav,
    banner,
    introSlot,
    shell,
  );
  main.append(preflightRoot, common);

  let guide = null;
  const refs = {};

  function summaryState() {
    const result = summary.update({
      storageAvailable: Boolean(local.status?.available),
      orders: state.orders,
      fleet: state.fleet,
      reports: local.reports,
      preflight: state.preflight,
    });
    updateStepper(
      stepper,
      state,
      local.reports,
      state.preflight,
    );
    window.dationSetDataReady(
      Boolean(result.enabled && isReady()),
    );
  }

  async function rename(kind) {
    const dataset = state[kind];
    const value = refs[kind].labelInput.value.trim();
    if (!dataset || !value || value === dataset.label) {
      return;
    }
    try {
      const response = await api(
        `/api/datasets/${dataset.id}`,
        {
          method: "PATCH",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({label: value}),
        },
      );
      state[kind] = response.dataset;
      persist();
      await loadLibrary(kind);
      renderCard(kind);
      summaryState();
    } catch (error) {
      local.saveErrors[kind] = error.message;
      renderCard(kind);
    }
  }

  function renderCard(kind) {
    const ref = refs[kind];
    if (!ref) {
      return;
    }
    const dataset = state[kind];
    const report = cardReport(dataset, local.reports[kind]);
    local.reports[kind] = report;

    const visibleState = deriveCardState({
      validation: report,
      saved: dataset,
      error: local.saveErrors[kind],
      validating: local.validating[kind],
      storageAvailable: Boolean(local.status?.available),
      duplicate: local.duplicate[kind],
    });
    ref.status.className = (
      `dispatch-upload-status is-${visibleState.tone}`
    );
    ref.status.textContent = visibleState.label;

    const fileInfo = currentFile(kind, dataset, report);
    const compact = Boolean(
      fileInfo
      && !local.replacing[kind]
      && !local.validating[kind],
    );
    ref.fileRow.hidden = !compact;
    ref.drop.hidden = compact || local.validating[kind];
    ref.progress.hidden = !local.validating[kind];
    ref.card.classList.toggle("is-loaded", compact);
    ref.card.classList.toggle(
      "is-recurrent-fleet",
      kind === "fleet" && Boolean(dataset),
    );

    if (fileInfo) {
      ref.fileName.textContent = fileInfo.name;
      ref.fileMeta.textContent = [
        fileSize(fileInfo.size),
        fileInfo.createdAt
          ? `cargado ${todayTime(fileInfo.createdAt)}`
          : report?.detected
            ? "validado"
            : null,
      ].filter(Boolean).join(" · ");
    }

    ref.fields.hidden = !report?.valid;
    if (
      report?.valid
      && document.activeElement !== ref.labelInput
    ) {
      ref.labelInput.value = (
        dataset?.label
        || report.suggested_label
        || fileInfo?.name
        || ""
      );
    }
    if (kind === "fleet" && ref.defaultInput) {
      ref.defaultInput.checked = dataset
        ? Boolean(dataset.is_default)
        : true;
    }

    ref.notice.replaceChildren();
    ref.notice.hidden = true;
    if (
      local.duplicateNotice[kind]
      || local.saveErrors[kind]
      || (
        report?.valid
        && !dataset
        && !local.status?.available
      )
    ) {
      ref.notice.hidden = false;
      ref.notice.textContent = (
        local.duplicateNotice[kind]
        || local.saveErrors[kind]
        || "Falta activar el almacenamiento. El archivo es válido, pero aún no se guarda."
      );
    }

    renderValidationReport(
      ref.report,
      report,
      {saved: Boolean(dataset)},
    );
    renderUnderstood(ref.understood, kind, report);
    summaryState();
  }

  function libraryOptions(kind) {
    return {
      kind,
      items: local.libraries[kind],
      selected: state[kind],
      query: local.queries[kind],
      onSearch: (value) => loadLibrary(kind, value),
      onSelect: async (dataset) => {
        state[kind] = dataset;
        local.reports[kind] = dataset.profile_json || null;
        local.saveErrors[kind] = null;
        local.replacing[kind] = false;
        persist();
        renderCard(kind);
        await refreshPreflight();
        await loadLibrary(kind);
      },
      onMakeDefault: async (dataset) => {
        await post(`/api/datasets/${dataset.id}/default`, {});
        state.fleet = {
          ...dataset,
          is_default: true,
        };
        persist();
        await loadLibrary("fleet");
        renderCard("fleet");
        await refreshPreflight();
      },
      onArchive: async (dataset) => {
        await post(`/api/datasets/${dataset.id}/archive`, {});
        if (state[kind]?.id === dataset.id) {
          state[kind] = null;
          local.reports[kind] = null;
          persist();
        }
        await loadLibrary(kind);
        renderCard(kind);
        await refreshPreflight();
      },
      onUndo: async (dataset) => {
        await post(`/api/datasets/${dataset.id}/unarchive`, {});
        await loadLibrary(kind);
      },
    };
  }

  async function loadLibrary(
    kind,
    query = local.queries[kind],
  ) {
    local.queries[kind] = query;
    if (!local.status?.available) {
      local.libraries[kind] = [];
      if (refs[kind]) {
        renderLibrary(
          refs[kind].library,
          libraryOptions(kind),
        );
      }
      return;
    }

    const search = query
      ? `&q=${encodeURIComponent(query)}`
      : "";
    const response = await api(
      `/api/datasets?type=${kind}&limit=20&offset=0${search}`,
    );
    local.libraries[kind] = response.items || [];

    if (state[kind]) {
      state[kind] = (
        local.libraries[kind].find(
          (item) => item.id === state[kind].id,
        )
        || state[kind]
      );
    }

    if (kind === "fleet" && !state.fleet) {
      state.fleet = (
        local.libraries.fleet.find(
          (item) => item.is_default,
        )
        || null
      );
      if (state.fleet) {
        local.reports.fleet = state.fleet.profile_json || null;
      }
    }

    persist();
    if (refs[kind]) {
      renderLibrary(
        refs[kind].library,
        libraryOptions(kind),
      );
    }
  }

  async function refreshPreflight() {
    state.preflight = null;
    renderPreflight(
      preflightRoot,
      null,
      state.orders,
      state.fleet,
    );
    summaryState();

    if (
      !state.orders
      || !state.fleet
      || !local.status?.available
    ) {
      return;
    }

    try {
      await runPreflight();
    } catch (error) {
      state.preflight = {
        valid: false,
        findings: [
          {
            id: "preflight_error",
            severity: "error",
            title: "No pudimos completar la revisión conjunta",
            consequence: error.message,
            items: [],
          },
        ],
        errors: [{detail: error.message}],
        warnings: [],
        anomalies: [],
        readiness: {
          can_continue: false,
          blockers: [error.message],
          reason: error.message,
        },
      };
    }

    renderPreflight(
      preflightRoot,
      state.preflight,
      state.orders,
      state.fleet,
    );
    summaryState();
  }

  async function saveValid(kind, file) {
    const report = local.reports[kind];
    if (!local.status?.available) {
      renderCard(kind);
      return;
    }

    const form = new FormData();
    form.append("file", file);
    form.append(
      "label",
      report?.suggested_label || file.name,
    );
    if (kind === "fleet" && state.fleet?.id) {
      form.append("parent_dataset_id", state.fleet.id);
    }

    try {
      const stored = await api(
        `/api/datasets/upload?dataset_type=${kind}`,
        {
          method: "POST",
          body: form,
        },
      );
      const dataset = (
        stored.dataset
        || stored.existing_dataset
      );
      state[kind] = dataset;
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

      if (
        kind === "fleet"
        && refs[kind].defaultInput?.checked
      ) {
        await post(
          `/api/datasets/${dataset.id}/default`,
          {},
        );
        state.fleet = {
          ...dataset,
          is_default: true,
        };
      }

      persist();
      local.replacing[kind] = false;
      await loadLibrary(kind);
      renderCard(kind);
      await refreshPreflight();
    } catch (error) {
      local.saveErrors[kind] = error.message;
      renderCard(kind);
    }
  }

  async function handleFile(kind, file) {
    const problem = clientFileProblem(file);
    if (problem) {
      local.reports[kind] = {
        valid: false,
        rows: 0,
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
      renderCard(kind);
      return;
    }

    local.validating[kind] = true;
    local.saveErrors[kind] = null;
    local.duplicate[kind] = false;
    local.duplicateNotice[kind] = null;
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
        persist();
      }
      if (report.valid) {
        await saveValid(kind, file);
      }
    } catch (error) {
      local.reports[kind] = {
        valid: false,
        rows: 0,
        errors: [
          {
            code: "VALIDATION_REQUEST_FAILED",
            message: error.message,
            hint: "Reintentá. Si persiste, revisá la conexión.",
          },
        ],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
    } finally {
      local.validating[kind] = false;
      renderCard(kind);
    }
  }

  async function loadSamples(button) {
    button.disabled = true;
    button.textContent = "Cargando datos de ejemplo…";
    try {
      const result = await post(
        "/api/datasets/load-sample",
        {},
      );
      state.orders = result.orders;
      state.fleet = result.fleet;
      local.reports.orders = result.orders_validation;
      local.reports.fleet = result.fleet_validation;
      persist();
      localStorage.setItem(INTRO_KEY, "1");
      introSlot.replaceChildren();
      await Promise.all([
        loadLibrary("orders"),
        loadLibrary("fleet"),
      ]);
      renderCard("orders");
      renderCard("fleet");
      await refreshPreflight();
    } catch (error) {
      button.disabled = false;
      button.textContent = "Probar con datos de ejemplo";
      banner.hidden = false;
      banner.className = "dispatch-system-banner";
      banner.replaceChildren(
        el("strong", "No pudimos cargar los datos de ejemplo"),
        el("p", error.message),
      );
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
    guideButton.onclick = () => {
      guide.open("orders", guideButton);
    };

    for (const kind of ["orders", "fleet"]) {
      refs[kind] = createDropCard(
        kind,
        contracts.formats[kind],
        (tab, source) => guide.open(tab, source),
      );
    }

    main.prepend(
      refs.orders.card,
      refs.fleet.card,
    );

    for (const kind of ["orders", "fleet"]) {
      const ref = refs[kind];
      ref.drop.onclick = () => ref.file.click();
      ref.replace.onclick = () => {
        local.replacing[kind] = true;
        renderCard(kind);
        ref.file.click();
      };
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
      };
      ref.drop.ondrop = (event) => {
        event.preventDefault();
        ref.drop.classList.remove("is-dragging");
        const selected = event.dataTransfer?.files?.[0];
        if (selected) {
          handleFile(kind, selected);
        }
      };
      ref.labelInput.onchange = () => rename(kind);
      if (kind === "fleet" && ref.defaultInput) {
        ref.defaultInput.onchange = async () => {
          if (!state.fleet) {
            return;
          }
          if (!ref.defaultInput.checked && state.fleet.is_default) {
            ref.defaultInput.checked = true;
            ref.notice.hidden = false;
            ref.notice.textContent = (
              "Para dejar de usar esta flota como vigente, "
              + "marcá otra versión como vigente."
            );
            return;
          }
          if (ref.defaultInput.checked) {
            await post(
              `/api/datasets/${state.fleet.id}/default`,
              {},
            );
            state.fleet.is_default = true;
            persist();
            await loadLibrary("fleet");
            renderCard("fleet");
          }
        };
      }
    }

    await Promise.all([
      loadLibrary("orders"),
      loadLibrary("fleet"),
    ]);

    if (state.orders?.profile_json) {
      local.reports.orders = state.orders.profile_json;
    }
    if (state.fleet?.profile_json) {
      local.reports.fleet = state.fleet.profile_json;
    }

    renderLibrary(
      refs.orders.library,
      libraryOptions("orders"),
    );
    renderLibrary(
      refs.fleet.library,
      libraryOptions("fleet"),
    );
    renderCard("orders");
    renderCard("fleet");

    const dismissed = localStorage.getItem(INTRO_KEY) === "1";
    const firstTime = (
      !dismissed
      && !state.orders
      && !state.fleet
      && !local.libraries.orders.length
      && !local.libraries.fleet.length
    );
    if (firstTime) {
      let intro = null;
      intro = makeIntroduction(
        (event) => loadSamples(event.currentTarget),
        (tab, source) => guide.open(tab, source),
        () => {
          localStorage.setItem(INTRO_KEY, "1");
          intro?.remove();
        },
      );
      introSlot.append(intro);
    }

    await refreshPreflight();
  } catch (error) {
    state.available = false;
    local.status = {
      available: false,
      checks: [],
      message: (
        "No pudimos consultar el estado del sistema. "
        + "Podés reintentar recargando la pantalla."
      ),
    };
    renderSystemBanner(banner, local.status);
    preflightRoot.replaceChildren(
      el("p", error.message, "dispatch-alert"),
    );
    summaryState();
  }
}
