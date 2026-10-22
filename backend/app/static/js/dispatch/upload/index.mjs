import {mountCaseIdentity,hasCaseExecutions} from '../case-identity.mjs';
import {responsibilityProblem} from '../workflow-responsibility.mjs';
import {mountDemoAction} from '../../platform/onboarding.mjs';
import {createScope,scopeFor} from "../lifecycle.mjs";
import {createWorkflowActionBar} from "../workflow-action-bar.mjs";
import {decisionHero} from "../decision-config-ui.mjs";
import {api, date, num} from "../shared.mjs";
import {createDropCard} from "./dropcard.mjs";
import {createGuideDrawer} from "./guide-drawer.mjs";
import {createPreviousDrawer} from "./library.mjs";
import {renderInlineValidation, renderCompatibilityStrip} from "./preflight-panel.mjs";
import {
  continueState,
  deriveCardState,
  technicalPreflightErrors,
} from "./selectors.mjs";
import {renderSystemBanner} from "./system-banner.mjs";
import {createValidationDrawer} from "./validation-report.mjs";
import {validateCsvFile,storeCsvFile} from './file-api.mjs';

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

function shortDateTime(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return new Intl.DateTimeFormat("es-AR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function dropTitle(kind) {
  return kind === "orders"
    ? "Arrastrá tu archivo de órdenes"
    : "Arrastrá tu archivo de flota";
}

function clientFileProblem(file) {
  if (!file?.name?.toLowerCase().endsWith(".csv")) {
    return "Este archivo no es un CSV. Descargá la plantilla o exportalo en formato CSV.";
  }
  if (file.size > MAX_BYTES) {
    return "El archivo supera los 10 MB. Probá con uno más liviano.";
  }
  if (file.size === 0) {
    return "El archivo no tiene datos. Revisalo y volvé a cargarlo.";
  }
  return null;
}

function workflowStep(id, fallback) {
  const steps = (
    window.DationDdaFlow
    && Array.isArray(window.DationDdaFlow.steps)
  )
    ? window.DationDdaFlow.steps
    : [];
  return steps.find((step) => step.id === id) || fallback;
}

function makeHero() {
  const dataStep = workflowStep("data", {number: 1, label: "Carga de datos"});
  const template = document.createElement("template");
  template.innerHTML = decisionHero({
    className: "dispatch-pro-hero",
    reveal: true,
    step: dataStep,
    title: "Preparar Decision Case",
    description: "Tu Data Pack reúne Órdenes y Flota. Subí archivos nuevos o reutilizá una carga anterior; Dation valida su estructura y compatibilidad.",
    panelTitle: "CÓMO FUNCIONA",
    panelItems: [
      {label: "1 · DESCARGÁ", description: "La plantilla con el formato correcto.", icon: "download"},
      {label: "2 · COMPLETÁ", description: "Solo lo mínimo. Lo opcional puede esperar.", icon: "clipboardList"},
      {label: "3 · SUBÍ", description: "Validación automática de archivos.", icon: "clipboardCheck"},
    ],
  });
  const hero = template.content.firstElementChild;
  const copy = hero.querySelector(".dispatch-pro-hero-copy");
  const panel = hero.querySelector(".dispatch-pro-how-panel");

  const fileChips = el("div", null, "dispatch-pro-hero-file-chips");
  const prefix = el(
    "span",
    "Vas a cargar",
    "dispatch-pro-hero-chip-prefix",
  );

  const ordersChip = el("span", null, "dispatch-pro-hero-file-chip is-orders");
  ordersChip.append(
    icon("orders"),
    document.createTextNode("Órdenes"),
  );

  const fleetChip = el("span", null, "dispatch-pro-hero-file-chip is-fleet");
  fleetChip.append(
    icon("fleet"),
    document.createTextNode("Flota"),
  );

  fileChips.append(prefix, ordersChip, fleetChip);
  copy.append(fileChips);

  const history = el("div", null, "dispatch-pro-how-history");
  const historyCopy = el("span", "¿Ya cargaste datos antes? ");
  const reuseLink = document.createElement("button");
  reuseLink.type = "button";
  reuseLink.className = "dispatch-pro-how-reuse-link";
  reuseLink.textContent = "Reutilizalos →";
  history.append(icon("history"), historyCopy, reuseLink);

  panel.append(history);

  return {hero, reuseLink};
}

function makeDataPackHeader() {
  const head = el("header", null, "dispatch-pro-section-head");
  head.append(
    el("span", "DATA PACK", "dispatch-pro-eyebrow"),
    el("h2", "Elegí cómo cargar tus datos."),
    el(
      "p",
      "Subí archivos nuevos o reutilizá una carga anterior. Cada archivo se valida apenas lo cargás; las columnas opcionales no bloquean este paso.",
    ),
  );
  return head;
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
      name: (
        dataset.canonical_filename
        || dataset.label
        || dataset.original_filename
        || "Archivo"
      ),
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
  scopeFor(root)?.own(()=>observer.disconnect());
  nodes.forEach((node) => observer.observe(node));
}

export async function mountUploadScreen(
  root,
  {
    state,
    persist,
    runPreflight,
    onNext,
    isCurrent=()=>true,
    mountWorkflow,
    saveIdentity,
  },
) {
  const scope=createScope(root),current=()=>scope.active&&isCurrent();
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
    controllers: {orders: null, fleet: null},
  };

  scope.own(()=>{for(const controller of Object.values(local.controllers))controller?.abort();});
  root.replaceChildren();
  root.className = "dispatch dispatch-upload-screen dispatch-upload-pro";

  const hero = makeHero();
  const demoRoot=el('div');const demoView=mountDemoAction(demoRoot,()=>window.dationSession?.identity||{membership:{access_role:'viewer'}});scope.own(()=>demoView.dispose());
  const banner = el("section");
  banner.hidden = true;

  const dataPack = el("section", null, "dispatch-pro-data-pack");
  dataPack.id = "dispatch-data-pack";
  dataPack.dataset.reveal = "";
  const cards = el("div", null, "dispatch-pro-file-grid");
  dataPack.append(makeDataPackHeader(), cards);

  const compatibilityRoot = el("section", null, "dispatch-pro-compatibility");
  compatibilityRoot.hidden = true;
  compatibilityRoot.dataset.reveal = "";

  function allowInputChange(){
    if(!hasCaseExecutions(state.decisionCase)&&state.caseContext?.status!=='archived')return true;
    const note=root.querySelector('[data-input-guard]');
    if(note){note.hidden=false;note.focus();}return false;
  }
  const refs = {};
  let guide = null;
  let previousDrawer = null;
  let validationDrawer = null;

  function scrollToData() {
    dataPack.scrollIntoView({behavior: "smooth", block: "start"});
  }

  function openReuseMode(event) {
    event?.preventDefault();
    ["orders", "fleet"].forEach((kind) => {
      refs[kind]?.setMode("reuse");
      renderPreviousInline(kind);
    });
    scrollToData();
  }

  hero.reuseLink.addEventListener("click", openReuseMode);

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
    card.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "center"});
    card.tabIndex = -1;
    card.focus({preventScroll:true});
    card.classList.remove("is-attention");
    window.requestAnimationFrame(() => {
      card.classList.add("is-attention");
      scope.timeout(
        () => card.classList.remove("is-attention"),
        1100,
      );
    });
  }

  const actionBar = createWorkflowActionBar({label:"Data Pack", onContinue:onNext, onProblem:scrollToProblem});
  if (typeof ResizeObserver !== "undefined") {
    scope.observe(new ResizeObserver(() => {
      root.style.setProperty("--workflow-bar-space", `${actionBar.bar.getBoundingClientRect().height + 32}px`);
    }), actionBar.bar);
  }

  root.append(
    hero.hero,
    demoRoot,
    banner,
    dataPack,
    compatibilityRoot,
    actionBar.bar,
  );
  mountCaseIdentity(root,{state,persist,onSave:saveIdentity});
  const guard=el('section',null,'d-card case-input-guard');guard.dataset.inputGuard='';guard.tabIndex=-1;
  guard.hidden=!hasCaseExecutions(state.decisionCase)&&state.caseContext?.status!=='archived';
  guard.append(el('p','Este Data Pack tiene ejecuciones o está archivado. Podés consultarlo. Para usar otros inputs, iniciá otro Case y conservá estos resultados.'));
  const newCase=el('button','Iniciar otro Decision Case','d-button d-button--secondary');newCase.type='button';scope.listen(newCase,'click',()=>window.DationDispatch.startNewDecision());guard.append(newCase);dataPack.before(guard);
  mountWorkflow?.(root,()=>finalState());

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


  function missingCount() {
    return ["orders", "fleet"].filter((kind) => !state[kind]).length;
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
      items: ["orders", "fleet"].map(key => ({key, label:key === "orders" ? "Órdenes" : "Flota", tone:fileTone(key)})),
      busy: Object.values(local.phases).some(phase => phase !== "idle"),
      storageAvailable: Boolean(local.status?.available),
    };

    const responsibility=responsibilityProblem(state.workflow,'data_preparation','data');
    if(result.enabled&&responsibility){result.enabled=false;result.kind='responsibility';result.message=responsibility;}
    actionBar.update(result, context);
    if(responsibility&&state.preflight?.valid){actionBar.button.firstElementChild.textContent='Seleccioná tu decisión';}

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
    if(!allowInputChange())return;
    const ref = refs[kind];
    if (!ref) return;
    local.replacing[kind] = true;
    ref.setMode("upload");
    renderCard(kind);
    ref.file.click();
  }

  function renderValidation() {
    ["orders", "fleet"].forEach((kind) => {
      const ref = refs[kind];
      if (!ref) return;
      renderInlineValidation(
        ref,
        {
          kind,
          report: reportFor(kind),
          phase: local.phases[kind],
          requiredCount: ref.requiredCount,
          optionalCount: ref.optionalCount,
          onReview: openValidation,
          onReplace: triggerReplace,
        },
      );
    });

    renderCompatibilityStrip(
      compatibilityRoot,
      {
        datasets: {
          orders: state.orders,
          fleet: state.fleet,
        },
        preflight: state.preflight,
        onReviewRelations: openRelationValidation,
      },
    );
    finalState();
  }

  function renderPreviousInline(kind) {
    const ref = refs[kind];
    if (!ref) return;
    ref.previousList.replaceChildren();

    const items = local.libraries[kind].slice(0, 3);
    ref.setReuseCount(local.libraries[kind].length);
    ref.previousEmpty.hidden = items.length > 0;
    ref.previousAll.hidden = items.length === 0;

    items.forEach((item) => {
      const selected = state[kind]?.id === item.id;
      const row = el(
        "article",
        null,
        `dispatch-pro-inline-library-row ${selected ? "is-selected" : ""}`,
      );
      const radio = el("span", null, "dispatch-pro-library-radio");
      const fileIcon = el("span", "CSV", "dispatch-pro-library-file-icon");
      const copy = el("div", null, "dispatch-pro-library-row-copy");
      const status = deriveCardState({
        report: item.profile_json || null,
        dataset: item,
      });
      const statusChip = el(
        "span",
        status.label,
        `dispatch-pro-library-state is-${status.tone}`,
      );
      copy.append(
        el(
          "strong",
          item.canonical_filename
            || item.label
            || item.original_filename
            || "Archivo",
        ),
        el(
          "small",
          [
            shortDateTime(item.created_at),
            domainRows(kind, item.row_count),
          ].filter(Boolean).join(" · "),
        ),
        statusChip,
      );
      const use = document.createElement("button");
      use.type = "button";
      use.className = "dispatch-pro-secondary-button";
      use.textContent = selected ? "En uso" : "Usar esta carga";
      use.disabled = selected;
      use.onclick = () => selectPrevious(kind, item);
      row.append(radio, fileIcon, copy, use);
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

    const stateIconName = cardState.tone === "success"
      ? "check"
      : cardState.tone === "warning"
        ? "warning"
        : cardState.tone === "error"
          ? "error"
          : cardState.key === "uploading" || cardState.key === "processing"
            ? "loader"
            : "pending";
    ref.headerState.replaceChildren();
    ref.headerState.className = `dispatch-pro-state-badge dispatch-pro-header-state is-${cardState.tone}`;
    ref.headerState.append(
      icon(stateIconName),
      document.createTextNode(cardState.label),
    );

    if (fileInfo) {
      ref.fileName.textContent = fileInfo.name;
      ref.fileMeta.replaceChildren();
      [
        domainRows(kind, fileInfo.rows),
        fileSize(fileInfo.size),
      ].filter(Boolean).forEach((value) => {
        ref.fileMeta.append(
          el("span", value, "dispatch-pro-file-meta-pill"),
        );
      });

      const reused = local.reused[kind];
      ref.reusedBadge.hidden = !reused;
      ref.reusedBadge.replaceChildren();
      if (reused) {
        ref.reusedBadge.append(
          icon("history"),
          document.createTextNode(
            `Carga anterior${reused.date ? ` · ${reused.date}` : ""}`,
          ),
        );
      }
    }

    ref.notice.hidden = true;
    ref.notice.replaceChildren();
    const notice = (
      local.duplicateNotice[kind]
      || local.saveErrors[kind]
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
      if(!current())return;
    local.libraries[kind] = [];
      renderPreviousInline(kind);
      return;
    }

    const response = await api(
      `/api/datasets?type=${kind}&limit=20&offset=0`, {signal:scope.signal},
    );
    if(!current())return;
    local.libraries[kind] = response.items || [];

    if (state[kind]) {
      const refreshed = local.libraries[kind].find(
        (item) => item.id === state[kind].id,
      );
      if (refreshed) {
        if(!current())return;
      state[kind] = refreshed;
        if(!current())return;
      local.reports[kind] = refreshed.profile_json || null;
        persist();
      }
    }
    renderPreviousInline(kind);
  }

  async function refreshPreflight() {
    state.preflight = null;
    mountWorkflow?.(root,()=>finalState());
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
      if(current())mountWorkflow?.(root,()=>finalState());
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
    if(!allowInputChange())return;
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

  function cancelCurrent(kind) {
    local.controllers[kind]?.abort();
    local.controllers[kind] = null;
    local.phases[kind] = "idle";
    local.pendingFiles[kind] = null;
    local.replacing[kind] = false;
    if (!state[kind]) {
      if(!current())return;
      local.reports[kind] = null;
    }
    renderCard(kind);
    refreshPreflight();
  }

  async function saveValid(kind, file) {
    if (!local.status?.available) {
      local.phases[kind] = "idle";
      renderCard(kind);
      return;
    }

    local.phases[kind] = "uploading";
    renderCard(kind);

    try {
      const controller = new AbortController();
      local.controllers[kind] = controller;
      const stored = await storeCsvFile(kind,file,{signal:controller.signal});
      local.controllers[kind] = null;

      const dataset = stored.dataset || stored.existing_dataset;
      if(!current())return;
      state[kind] = dataset;
      if(!current())return;
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
      local.controllers[kind] = null;
      local.phases[kind] = "idle";
      if (error?.name === "AbortError") {
        local.pendingFiles[kind] = null;
        local.replacing[kind] = false;
        renderCard(kind);
        return;
      }
      local.saveErrors[kind] = "No pudimos subir el archivo. Reintentar.";
      if(!current())return;
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
      scope.timeout(
        () => card.classList.remove("is-accepted"),
        500,
      );
    });
  }

  async function handleFile(kind, file) {
    if(!allowInputChange())return;
    const problem = clientFileProblem(file);
    local.pendingFiles[kind] = file;
    local.saveErrors[kind] = null;
    local.duplicate[kind] = false;
    local.duplicateNotice[kind] = null;
    local.reused[kind] = null;
    local.replacing[kind] = false;

    if (problem) {
      if(!current())return;
      state[kind] = null;
      if(!current())return;
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
          hint: "Corregí el archivo o descargá la plantilla para usar la estructura esperada.",
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
      const controller = new AbortController();
      local.controllers[kind] = controller;
      const report = await validateCsvFile(kind,file,{signal:controller.signal});
      local.controllers[kind] = null;

      if(!current())return;
      local.reports[kind] = report;
      if (!report.valid) {
        if(!current())return;
      state[kind] = null;
        local.phases[kind] = "idle";
        persist();
        renderCard(kind);
        await refreshPreflight();
        return;
      }

      await saveValid(kind, file);
    } catch (error) {
      local.controllers[kind] = null;
      if(!current())return;
      state[kind] = null;
      local.phases[kind] = "idle";
      if (error?.name === "AbortError") {
        local.pendingFiles[kind] = null;
        renderCard(kind);
        await refreshPreflight();
        return;
      }
      if(!current())return;
      local.reports[kind] = {
        valid: false,
        rows: 0,
        file: {name: file.name, size_bytes: file.size},
        errors: [{
          code: "VALIDATION_REQUEST_FAILED",
          message: "No pudimos subir el archivo.",
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
    if(!allowInputChange())return;
    local.controllers[kind]?.abort();
    local.controllers[kind] = null;
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
      api("/api/dispatch/status",{signal:scope.signal}),
      api("/api/dispatch/contracts",{signal:scope.signal}),
    ]);
    if(!current())return;
    local.status = status;
    local.contracts = contracts;
    state.available = Boolean(status.available);
    renderSystemBanner(banner, status);

    guide = createGuideDrawer(contracts,scope);
    previousDrawer = createPreviousDrawer(scope);
    validationDrawer = createValidationDrawer(scope);

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
      ref.cancelUpload.onclick = () => cancelCurrent(kind);
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
      ref.reuseTab.addEventListener("click", () => renderPreviousInline(kind));
      ref.previousAll.onclick = () => openPrevious(kind, ref.previousAll);

      if (state[kind]?.profile_json) {
        if(!current())return;
      local.reports[kind] = state[kind].profile_json;
      }
      renderCard(kind);
    }

    await Promise.all([
      loadLibrary("orders"),
      loadLibrary("fleet"),
    ]);
    if(!current())return;
    renderCard("orders");
    renderCard("fleet");
    await refreshPreflight();

    if(!current())return;
    revealSections(root);
  } catch (error) {
    if(!current())return;
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
