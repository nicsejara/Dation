import {api, date, num} from "../shared.mjs";
import {createDropCard} from "./dropcard.mjs?v=upload-pro-v1";
import {createGuideDrawer} from "./guide-drawer.mjs?v=upload-pro-v1";
import {createPreviousDrawer} from "./library.mjs?v=upload-pro-v1";
import {renderValidationPanel} from "./preflight-panel.mjs?v=upload-pro-v1";
import {
  continueState,
  deriveCardState,
  technicalPreflightErrors,
} from "./selectors.mjs?v=upload-pro-v1";
import {renderSystemBanner} from "./system-banner.mjs?v=upload-pro-v1";
import {createValidationDrawer} from "./validation-report.mjs?v=upload-pro-v1";

const MAX_BYTES = 10 * 1024 * 1024;

function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function icon(name) {
  const paths = {
    back: '<path d="m15 18-6-6 6-6"/><path d="M9 12h11"/>',
    orders: '<path d="M9 5h6M9 9h6M9 13h4"/><path d="M7 3h10a2 2 0 0 1 2 2v14H5V5a2 2 0 0 1 2-2Z"/>',
    fleet: '<path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/>',
    table: '<path d="M4 5h16v14H4z"/><path d="M4 10h16M10 5v14"/>',
    shield: '<path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z"/><path d="m9 12 2 2 4-4"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
    warning: '<path d="M12 3 2.5 20h19Z"/><path d="M12 9v4M12 17h.01"/>',
    error: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    pending: '<circle cx="12" cy="12" r="9"/>',
    loader: '<path d="M21 12a9 9 0 1 1-3-6.7"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    map: '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>',
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("dispatch-pro-icon");
  svg.innerHTML = paths[name] || paths.check;
  return svg;
}

function fileSize(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  return `${num(bytes / 1024, 1)} KB`;
}

function domainRows(kind, rows) {
  if (rows == null) return null;
  const amount = num(rows);
  if (kind === "orders") {
    return `${amount} ${Number(rows) === 1 ? "orden" : "órdenes"}`;
  }
  return `${amount} ${Number(rows) === 1 ? "vehículo" : "vehículos"}`;
}

function dropTitle(kind) {
  return kind === "orders"
    ? "Arrastrá tu archivo de órdenes"
    : "Arrastrá tu archivo de flota";
}

function clientFileProblem(file) {
  if (!file?.name?.toLowerCase().endsWith(".csv")) {
    return "Solo se admiten archivos con extensión .csv.";
  }
  if (file.size > MAX_BYTES) {
    return "El archivo supera el límite de 10 MB.";
  }
  return null;
}

function makeHero() {
  const hero = el("section", null, "dispatch-pro-hero");
  hero.dataset.reveal = "";

  const copy = el("div", null, "dispatch-pro-hero-copy");
  const back = document.createElement("button");
  back.type = "button";
  back.className = "dispatch-pro-back";
  back.append(icon("back"), document.createTextNode("Volver a DDA Logística"));
  back.onclick = () => window.dationNavigate?.("logistics-overview");

  const badges = el("div", null, "dispatch-pro-hero-badges");
  badges.append(
    el("span", "DDA LOGÍSTICA", "dispatch-pro-hero-badge"),
    el("span", "PASO 1 · DATOS", "dispatch-pro-hero-badge is-step"),
  );

  copy.append(
    back,
    badges,
    el("span", "DATION · CARGA DE DATOS", "dispatch-pro-eyebrow is-on-dark"),
    el("h1", "Cargá tus datos y habilitá tu mapa de decisiones."),
    el(
      "p",
      "Subí tu Data Pack o reutilizá uno que ya cargaste. Dation lo valida y te abre el mapa de decisiones.",
      "dispatch-pro-hero-lead",
    ),
    el(
      "p",
      "Data Pack: los archivos que alimentan tus decisiones. Empezá con los mínimos y sumá el resto cuando quieras.",
      "dispatch-pro-datapack-definition",
    ),
  );

  const fileChips = el("div", null, "dispatch-pro-hero-file-chips");
  const ordersChip = el("span", "Órdenes");
  ordersChip.className = "is-orders";
  const fleetChip = el("span", "Flota");
  fleetChip.className = "is-fleet";
  fileChips.append(ordersChip, fleetChip);

  const status = el("div", null, "dispatch-pro-hero-status is-pending");
  status.append(
    el("i", ""),
    el("span", "0 de 2 archivos listos"),
  );
  copy.append(fileChips, status);

  const visual = el("div", null, "dispatch-pro-hero-visual");
  const watermark = document.createElement("img");
  watermark.src = "/static/assets/dda-logistics.svg?v=upload-pro-v1";
  watermark.alt = "";
  watermark.className = "dispatch-pro-hero-watermark";

  const panel = el("div", null, "dispatch-pro-how-panel");
  panel.append(el("span", "CÓMO FUNCIONA", "dispatch-pro-eyebrow is-on-dark"));

  [
    ["1", "DESCARGÁ", "La plantilla con el formato correcto.", "download"],
    ["2", "COMPLETÁ", "Solo lo mínimo. Lo opcional puede esperar.", "table"],
    ["3", "SUBÍ Y VALIDÁ", "Dation revisa todo antes de seguir.", "shield"],
  ].forEach(([number, label, description, iconName], index) => {
    const node = el("div", null, "dispatch-pro-how-node");
    const iconWrap = el("span", null, "dispatch-pro-how-icon");
    iconWrap.append(icon(iconName));
    const text = el("div");
    text.append(
      el("small", `${number} · ${label}`),
      el("strong", description),
    );
    node.append(iconWrap, text);
    panel.append(node);
    if (index < 2) panel.append(el("span", "", "dispatch-pro-how-connector"));
  });

  const history = el("div", null, "dispatch-pro-how-history");
  history.append(
    icon("history"),
    el("span", "¿Ya cargaste datos antes? Podés reutilizarlos."),
  );
  panel.append(history);
  visual.append(watermark, panel);
  hero.append(copy, visual);

  function update(readyCount, busy) {
    const statusCopy = status.querySelector("span");
    status.className = (
      "dispatch-pro-hero-status "
      + (readyCount === 2
        ? "is-ready"
        : busy || readyCount
          ? "is-progress"
          : "is-pending")
    );
    statusCopy.textContent = `${readyCount} de 2 archivos listos`;
  }

  return {hero, update};
}

function makeDataPackHeader() {
  const head = el("header", null, "dispatch-pro-section-head");
  head.append(
    el("span", "DATA PACK", "dispatch-pro-eyebrow"),
    el("h2", "Elegí cómo cargar tus datos."),
    el(
      "p",
      "Podés subir archivos nuevos o reutilizar cargas anteriores. Cada archivo se valida apenas lo cargás.",
    ),
  );
  return head;
}

function makeFinalBar(onNext, scrollToData, scrollToProblem) {
  const bar = el("section", null, "dispatch-pro-final is-pending");
  bar.dataset.reveal = "";

  const watermark = document.createElement("img");
  watermark.src = "/static/assets/dda-logistics.svg?v=upload-pro-v1";
  watermark.alt = "";
  watermark.className = "dispatch-pro-final-watermark";

  const copy = el("div", null, "dispatch-pro-final-copy");
  const eyebrow = el("span", "SIGUIENTE PASO", "dispatch-pro-eyebrow");
  const title = el("h2", "Todavía falta un paso.");
  const description = el(
    "p",
    "Completá Órdenes y Flota para crear tu Decision Case.",
  );
  const note = el("small", "", "dispatch-pro-final-note");
  note.hidden = true;
  copy.append(eyebrow, title, description, note);

  const actions = el("div", null, "dispatch-pro-final-actions");
  const primary = document.createElement("button");
  primary.type = "button";
  primary.className = "button button--primary";
  primary.textContent = "Faltan 2 archivos";
  const secondary = document.createElement("button");
  secondary.type = "button";
  secondary.className = "button button--secondary";
  secondary.textContent = "Revisar mis datos";
  secondary.onclick = scrollToData;
  actions.append(primary, secondary);

  const preview = el("div", null, "dispatch-pro-map-preview");
  preview.append(el("span", "ESTO VAS A VER", "dispatch-pro-eyebrow"));
  const chain = el("div", null, "dispatch-pro-preview-chain");
  const assignment = el("div", null, "dispatch-pro-preview-node is-pending");
  assignment.append(
    icon("map"),
    el("strong", "Asignación de carga"),
    el("small", "Pendiente"),
  );
  const planning = el("div", null, "dispatch-pro-preview-node is-locked");
  planning.append(
    icon("lock"),
    el("strong", "Planificación"),
    el("small", "Bloqueada"),
  );
  const execution = el("div", null, "dispatch-pro-preview-node is-locked");
  execution.append(
    icon("lock"),
    el("strong", "Ejecución física"),
    el("small", "Bloqueada"),
  );
  chain.append(
    assignment,
    el("i", "", "dispatch-pro-preview-link"),
    planning,
    el("i", "", "dispatch-pro-preview-link"),
    execution,
  );
  preview.append(chain);
  bar.append(watermark, copy, actions, preview);

  function update(result, context = {}) {
    const {
      missingCount = 0,
      errorCount = 0,
      warningCount = 0,
    } = context;
    bar.className = `dispatch-pro-final is-${result.kind}`;
    note.hidden = true;
    primary.className = "button button--secondary";

    if (result.enabled) {
      title.textContent = "Tu Decision Case está listo.";
      description.textContent = (
        "Explorá en el Decision Map qué decisión podés resolver ahora "
        + "y cuál sigue en la cadena."
      );
      primary.className = "button button--primary";
      primary.textContent = "Ir al mapa de decisiones →";
      primary.onclick = onNext;
      if (warningCount) {
        note.hidden = false;
        note.textContent = (
          `Podés avanzar: hay ${warningCount} `
          + `${warningCount === 1 ? "aviso" : "avisos"} sobre columnas opcionales.`
        );
      }
      assignment.className = "dispatch-pro-preview-node is-ready";
      assignment.querySelector("small").textContent = "Disponible";
      return;
    }

    assignment.className = "dispatch-pro-preview-node is-pending";
    assignment.querySelector("small").textContent = "Pendiente";

    if (result.kind === "error") {
      title.textContent = `Hay ${errorCount || 1} ${(errorCount || 1) === 1 ? "cosa" : "cosas"} para corregir.`;
      description.textContent = "Revisá el primer problema y corregí el archivo antes de continuar.";
      primary.textContent = "Corregir archivos";
      primary.onclick = scrollToProblem;
      return;
    }

    title.textContent = "Todavía falta un paso.";
    description.textContent = missingCount
      ? "Completá los archivos pendientes para crear tu Decision Case."
      : result.message;
    primary.textContent = missingCount
      ? `Faltan ${missingCount} ${missingCount === 1 ? "archivo" : "archivos"}`
      : "Revisar carga";
    primary.onclick = missingCount ? scrollToProblem : scrollToData;
  }

  return {bar, update};
}

function makeSticky(onNext, scrollToProblem) {
  const bar = el("div", null, "dispatch-pro-sticky");
  bar.hidden = true;
  const status = el("div", null, "dispatch-pro-sticky-status");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button button--primary";
  bar.append(status, button);

  function update(result, context = {}) {
    const {
      ordersTone = "pending",
      fleetTone = "pending",
      missingCount = 0,
      errorCount = 0,
      engaged = false,
    } = context;

    bar.hidden = !engaged;
    status.replaceChildren();

    [
      ["orders", "Órdenes", ordersTone],
      ["fleet", "Flota", fleetTone],
    ].forEach(([kind, label, tone]) => {
      const item = el(
        "span",
        null,
        `dispatch-pro-sticky-file is-${kind} is-${tone}`,
      );
      item.append(
        el("i", ""),
        el(
          "strong",
          `${label} ${tone === "success" || tone === "warning" ? "✓" : tone === "error" ? "!" : "pendiente"}`,
        ),
      );
      status.append(item);
    });

    if (result.enabled) {
      button.className = "button button--primary";
      button.textContent = "Ir al mapa de decisiones →";
      button.onclick = onNext;
      return;
    }
    button.className = "button button--secondary";
    button.textContent = result.kind === "error"
      ? `Corregir ${errorCount || 1} ${(errorCount || 1) === 1 ? "problema" : "problemas"}`
      : `Faltan ${missingCount || 1} ${(missingCount || 1) === 1 ? "archivo" : "archivos"}`;
    button.onclick = scrollToProblem;
  }

  return {bar, update};
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

function revealSections(root) {
  root.classList.add("is-enhanced");
  const nodes = [...root.querySelectorAll("[data-reveal]")];
  if (
    !("IntersectionObserver" in window)
    || window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    nodes.forEach((node) => node.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, {threshold: 0.08});
  nodes.forEach((node) => observer.observe(node));
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
    reports: {orders: null, fleet: null},
    phases: {orders: "idle", fleet: "idle"},
    saveErrors: {orders: null, fleet: null},
    duplicateNotice: {orders: null, fleet: null},
    duplicate: {orders: false, fleet: false},
    reused: {orders: null, fleet: null},
    replacing: {orders: false, fleet: false},
    pendingFiles: {orders: null, fleet: null},
    libraries: {orders: [], fleet: []},
    finalVisible: false,
  };

  root.replaceChildren();
  root.className = "dispatch dispatch-upload-screen dispatch-upload-pro";

  const hero = makeHero();
  const banner = el("section");
  banner.hidden = true;

  const dataPack = el("section", null, "dispatch-pro-data-pack");
  dataPack.id = "dispatch-data-pack";
  dataPack.dataset.reveal = "";
  const cards = el("div", null, "dispatch-pro-file-grid");
  dataPack.append(makeDataPackHeader(), cards);

  const validationRoot = el("section");
  validationRoot.dataset.reveal = "";

  const refs = {};
  let guide = null;
  let previousDrawer = null;
  let validationDrawer = null;

  function scrollToData() {
    dataPack.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function firstProblemKind() {
    for (const kind of ["orders", "fleet"]) {
      const report = reportFor(kind);
      if (
        !state[kind]
        || Number(report?.counts?.errors || 0)
        || local.saveErrors[kind]
      ) {
        return kind;
      }
    }
    if (technicalPreflightErrors(state.preflight).length) return "orders";
    return "orders";
  }

  function scrollToProblem() {
    const kind = firstProblemKind();
    const card = refs[kind]?.card;
    if (!card) {
      scrollToData();
      return;
    }
    card.scrollIntoView({behavior: "smooth", block: "center"});
    card.classList.remove("is-attention");
    window.requestAnimationFrame(() => {
      card.classList.add("is-attention");
      window.setTimeout(
        () => card.classList.remove("is-attention"),
        1100,
      );
    });
  }

  const finalBar = makeFinalBar(onNext, scrollToData, scrollToProblem);
  const sticky = makeSticky(onNext, scrollToProblem);

  root.append(
    hero.hero,
    banner,
    dataPack,
    validationRoot,
    finalBar.bar,
    sticky.bar,
  );

  function reportFor(kind) {
    return local.reports[kind] || state[kind]?.profile_json || null;
  }

  function fileTone(kind) {
    const report = reportFor(kind);
    if (local.phases[kind] !== "idle") return "validating";
    if (local.saveErrors[kind] || Number(report?.counts?.errors || 0)) {
      return "error";
    }
    if (report?.valid || state[kind]) {
      return Number(report?.counts?.warnings || 0)
        ? "warning"
        : "success";
    }
    return "pending";
  }

  function readyCount() {
    return ["orders", "fleet"].filter((kind) => (
      state[kind] && reportFor(kind)?.valid
    )).length;
  }

  function warningCount() {
    return ["orders", "fleet"].reduce(
      (total, kind) => total + Number(reportFor(kind)?.counts?.warnings || 0),
      0,
    );
  }

  function errorCount() {
    const fileErrors = ["orders", "fleet"].reduce(
      (total, kind) => {
        const report = reportFor(kind);
        return total + (
          local.saveErrors[kind]
          || Number(report?.counts?.errors || 0)
            ? 1
            : 0
        );
      },
      0,
    );
    return fileErrors + (
      technicalPreflightErrors(state.preflight).length ? 1 : 0
    );
  }

  function missingCount() {
    return ["orders", "fleet"].filter((kind) => !state[kind]).length;
  }

  function engaged() {
    return ["orders", "fleet"].some((kind) => (
      Boolean(state[kind])
      || Boolean(reportFor(kind))
      || Boolean(local.pendingFiles[kind])
      || local.phases[kind] !== "idle"
    ));
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

    const context = {
      missingCount: missingCount(),
      errorCount: errorCount(),
      warningCount: warningCount(),
      ordersTone: fileTone("orders"),
      fleetTone: fileTone("fleet"),
      engaged: engaged(),
    };

    finalBar.update(result, context);
    sticky.update(result, context);
    sticky.bar.hidden = sticky.bar.hidden || local.finalVisible;

    const count = readyCount();
    const busy = local.phases.orders !== "idle" || local.phases.fleet !== "idle";
    hero.update(count, busy);
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
    if (!report) return;

    validationDrawer.open({
      report,
      filename: file?.name || null,
      source,
      heading: Number(report.counts?.errors || 0)
        ? "Revisar problemas"
        : "Revisar avisos",
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
      report: {errors, warnings: []},
      source,
      heading: "Compatibilidad entre archivos",
    });
  }

  function triggerReplace(kind) {
    const ref = refs[kind];
    if (!ref) return;
    local.replacing[kind] = true;
    ref.setMode("upload");
    renderCard(kind);
    ref.file.click();
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
        onReplace: triggerReplace,
      },
    );
    finalState();
  }

  function renderPreviousInline(kind) {
    const ref = refs[kind];
    if (!ref) return;
    ref.previousList.replaceChildren();

    const items = local.libraries[kind].slice(0, 3);
    ref.previousEmpty.hidden = items.length > 0;
    ref.previousAll.hidden = local.libraries[kind].length <= 3;

    items.forEach((item) => {
      const row = el(
        "article",
        null,
        `dispatch-pro-inline-library-row ${state[kind]?.id === item.id ? "is-selected" : ""}`,
      );
      const fileIcon = el("span", "CSV", "dispatch-pro-library-file-icon");
      const copy = el("div");
      copy.append(
        el("strong", item.original_filename || item.label || "Archivo"),
        el(
          "small",
          [
            domainRows(kind, item.row_count),
            item.created_at
              ? date(item.created_at.slice(0, 10))
              : null,
          ].filter(Boolean).join(" · "),
        ),
      );
      const use = document.createElement("button");
      use.type = "button";
      use.className = "dispatch-pro-secondary-button";
      use.textContent = state[kind]?.id === item.id ? "En uso" : "Usar";
      use.disabled = state[kind]?.id === item.id;
      use.onclick = () => selectPrevious(kind, item);
      row.append(fileIcon, copy, use);
      ref.previousList.append(row);
    });
  }

  function renderCard(kind) {
    const ref = refs[kind];
    if (!ref) return;

    const report = reportFor(kind);
    if (report) local.reports[kind] = report;

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
        ? "Guardando archivo…"
        : `Validando ${local.pendingFiles[kind]?.name || "archivo"}…`;
      ref.progressFile.textContent = local.pendingFiles[kind]?.name || "";
    }

    if (fileInfo) {
      ref.fileName.textContent = fileInfo.name;
      ref.fileState.replaceChildren();
      ref.fileState.className = `dispatch-pro-state-badge is-${cardState.tone}`;
      const stateIconName = cardState.tone === "success"
        ? "check"
        : cardState.tone === "warning"
          ? "warning"
          : cardState.tone === "error"
            ? "error"
            : cardState.tone === "pending"
              ? "pending"
              : "loader";
      ref.fileState.append(
        icon(stateIconName),
        document.createTextNode(cardState.label),
      );
      ref.fileMeta.textContent = [
        domainRows(kind, fileInfo.rows),
        fileSize(fileInfo.size),
      ].filter(Boolean).join(" · ");

      const reused = local.reused[kind];
      ref.reusedBadge.hidden = !reused;
      ref.reusedBadge.textContent = reused
        ? `Carga anterior${reused.date ? ` · ${reused.date}` : ""}`
        : "";
    }

    const issues = (
      Number(report?.counts?.errors || 0)
      + Number(report?.counts?.warnings || 0)
    );
    ref.reviewProblems.hidden = !issues;
    if (issues) {
      ref.reviewProblems.lastChild.textContent = Number(report?.counts?.errors || 0)
        ? "Revisar problemas"
        : "Ver avisos";
    }

    ref.notice.hidden = true;
    ref.notice.replaceChildren();
    const firstError = report?.errors?.[0];
    const firstWarning = report?.warnings?.[0];
    const issueNotice = firstError
      ? [
          firstError.message || firstError.detail || "Hay un dato para corregir.",
          firstError.column ? `Columna: ${firstError.column}.` : null,
          firstError.hint || null,
        ].filter(Boolean).join(" ")
      : firstWarning
        ? [
            firstWarning.message || firstWarning.detail || "Hay un aviso para revisar.",
            firstWarning.hint || "Podés continuar si no bloquea este paso.",
          ].filter(Boolean).join(" ")
        : null;

    const notice = (
      local.duplicateNotice[kind]
      || local.saveErrors[kind]
      || issueNotice
      || (
        report?.valid
        && !state[kind]
        && !local.status?.available
          ? "El archivo es válido, pero todavía no se puede guardar."
          : null
      )
    );

    if (notice) {
      ref.notice.hidden = false;
      ref.notice.textContent = notice;
    }

    ref.card.classList.remove(
      "is-success",
      "is-warning",
      "is-error",
      "is-validating",
      "is-pending",
    );
    ref.card.classList.add(`is-${fileTone(kind)}`);
    renderPreviousInline(kind);
    renderValidation();
  }

  async function loadLibrary(kind) {
    if (!local.status?.available) {
      local.libraries[kind] = [];
      renderPreviousInline(kind);
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
    renderPreviousInline(kind);
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
        errors: [{
          code: "PREFLIGHT_REQUEST_FAILED",
          detail: error.message,
        }],
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
    local.reused[kind] = {
      date: dataset.created_at
        ? date(dataset.created_at.slice(0, 10))
        : null,
    };
    persist();
    refs[kind].setMode("upload");
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
        {method: "POST", body: form},
      );

      const dataset = stored.dataset || stored.existing_dataset;
      state[kind] = dataset;
      local.reports[kind] = stored.validation || local.reports[kind];
      local.saveErrors[kind] = null;
      local.duplicate[kind] = Boolean(stored.duplicate);
      local.reused[kind] = stored.duplicate
        ? {
            date: dataset.created_at
              ? date(dataset.created_at.slice(0, 10))
              : null,
          }
        : null;
      local.duplicateNotice[kind] = stored.duplicate
        ? "Este archivo ya estaba cargado. Reutilizamos la versión guardada."
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
    local.reused[kind] = null;
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
        errors: [{
          code: "INVALID_FILE",
          message: problem,
          hint: "Elegí un CSV válido de hasta 10 MB.",
        }],
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
        {method: "POST", body: form},
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
        file: {name: file.name, size_bytes: file.size},
        errors: [{
          code: "VALIDATION_REQUEST_FAILED",
          message: error.message,
          hint: "Reintentá la carga. Si persiste, revisá la conexión.",
        }],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
      persist();
      renderCard(kind);
      await refreshPreflight();
    }
  }

  async function removeFile(kind) {
    state[kind] = null;
    local.reports[kind] = null;
    local.pendingFiles[kind] = null;
    local.saveErrors[kind] = null;
    local.duplicateNotice[kind] = null;
    local.duplicate[kind] = false;
    local.reused[kind] = null;
    local.replacing[kind] = false;
    state.preflight = null;
    persist();
    refs[kind].setMode("upload");
    renderCard(kind);
    await refreshPreflight();
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

      const openPicker = () => ref.file.click();

      ref.drop.onclick = (event) => {
        if (event.target.closest("a, button")) return;
        openPicker();
      };
      ref.drop.onkeydown = (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openPicker();
        }
      };
      ref.choose.onclick = (event) => {
        event.stopPropagation();
        openPicker();
      };

      ref.file.onchange = () => {
        const selected = ref.file.files?.[0];
        if (selected) handleFile(kind, selected);
        ref.file.value = "";
      };

      ref.drop.ondragover = (event) => {
        event.preventDefault();
        ref.drop.classList.add("is-dragging");
        ref.dropStrong.textContent = "Soltá para cargar";
      };
      ref.drop.ondragleave = () => {
        ref.drop.classList.remove("is-dragging");
        ref.dropStrong.textContent = dropTitle(kind);
      };
      ref.drop.ondrop = (event) => {
        event.preventDefault();
        ref.drop.classList.remove("is-dragging");
        ref.dropStrong.textContent = dropTitle(kind);
        const selected = event.dataTransfer?.files?.[0];
        if (selected) handleFile(kind, selected);
      };

      ref.replace.onclick = () => triggerReplace(kind);
      ref.remove.onclick = () => removeFile(kind);
      ref.reviewColumns.onclick = () => {
        guide.open(
          kind,
          ref.reviewColumns,
          {
            orders: reportFor("orders"),
            fleet: reportFor("fleet"),
          },
        );
      };
      ref.reviewProblems.onclick = () => {
        openValidation(kind, ref.reviewProblems);
      };
      ref.reuseTab.addEventListener("click", () => renderPreviousInline(kind));
      ref.previousAll.onclick = () => openPrevious(kind, ref.previousAll);

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

    if ("IntersectionObserver" in window) {
      const finalObserver = new IntersectionObserver((entries) => {
        local.finalVisible = entries.some((entry) => entry.isIntersecting);
        finalState();
      }, {threshold: 0.18});
      finalObserver.observe(finalBar.bar);
    }

    revealSections(root);
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
    revealSections(root);
  }
}
