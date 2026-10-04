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

function icon(name) {
  const paths = {
    orders: '<path d="M9 5h6M9 9h6M9 13h4"/><path d="M7 3h10a2 2 0 0 1 2 2v14H5V5a2 2 0 0 1 2-2Z"/><path d="M8 19v2h8v-2"/>',
    fleet: '<path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
    download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/>',
    refresh: '<path d="M20 6v5h-5"/><path d="M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5L20 15"/>',
    columns: '<path d="M4 5h16v14H4z"/><path d="M10 5v14M15 5v14"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M8 10v7M12 10v7M16 10v7M6 7l1 14h10l1-14"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/>',
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("dispatch-pro-icon");
  svg.innerHTML = paths[name] || paths.file;
  return svg;
}

function requirementChip(label, optional = false) {
  const chip = el(
    "span",
    label,
    `dispatch-pro-requirement ${optional ? "is-optional" : "is-required"}`,
  );
  if (optional) {
    chip.title = "Las opcionales habilitan decisiones posteriores.";
  }
  return chip;
}

export function createDropCard(kind, contract) {
  const requiredCount = contract.columns.filter(
    (column) => column.required,
  ).length;
  const optionalCount = contract.columns.length - requiredCount;
  const label = kind === "orders" ? "Órdenes" : "Flota";

  const card = el(
    "section",
    null,
    `dispatch-pro-file-card dispatch-pro-file-card--${kind}`,
  );
  card.dataset.kind = kind;

  const accent = el("div", null, "dispatch-pro-file-accent");
  accent.setAttribute("aria-hidden", "true");

  const header = el("div", null, "dispatch-pro-file-head");
  const entityIcon = el("span", null, "dispatch-pro-entity-icon");
  entityIcon.append(icon(kind));

  const copy = el("div", null, "dispatch-pro-file-copy");
  copy.append(
    el(
      "span",
      kind === "orders" ? "01 · DEMANDA" : "02 · RECURSOS",
      "dispatch-pro-eyebrow",
    ),
    el("h3", label),
    el(
      "p",
      kind === "orders"
        ? "Qué productos y cantidades hay que transportar, y hacia dónde."
        : "Tus vehículos, propios o tercerizados, con su capacidad y disponibilidad.",
    ),
  );
  if (kind === "fleet") {
    copy.append(
      el("small", "Una fila por vehículo.", "dispatch-pro-format-hint"),
    );
  }
  const chips = el("div", null, "dispatch-pro-requirements");
  chips.append(
    requirementChip(`${requiredCount} columnas mínimas`),
    requirementChip(`${optionalCount} opcionales`, true),
  );
  copy.append(chips);
  header.append(entityIcon, copy);

  const switcher = el("div", null, "dispatch-pro-source-switch");
  switcher.setAttribute("role", "group");
  switcher.setAttribute("aria-label", `Cómo cargar ${label.toLowerCase()}`);

  const uploadTab = document.createElement("button");
  uploadTab.type = "button";
  uploadTab.textContent = "Subir nuevo";
  uploadTab.dataset.mode = "upload";
  uploadTab.setAttribute("aria-pressed", "true");

  const reuseTab = document.createElement("button");
  reuseTab.type = "button";
  reuseTab.textContent = "Reutilizar anterior";
  reuseTab.dataset.mode = "reuse";
  reuseTab.setAttribute("aria-pressed", "false");

  switcher.append(uploadTab, reuseTab);

  const uploadView = el("div", null, "dispatch-pro-source-view");
  uploadView.dataset.sourceView = "upload";

  const drop = el("div", null, "dispatch-pro-dropzone");
  drop.setAttribute("role", "button");
  drop.tabIndex = 0;
  drop.setAttribute(
    "aria-label",
    kind === "orders"
      ? "Elegir archivo CSV de órdenes"
      : "Elegir archivo CSV de flota",
  );
  const uploadIcon = el("span", null, "dispatch-pro-drop-icon");
  uploadIcon.append(icon("upload"));
  const dropStrong = el(
    "strong",
    kind === "orders"
      ? "Arrastrá tu archivo de órdenes"
      : "Arrastrá tu archivo de flota",
  );
  const dropCopy = el("span", "o elegilo desde tu equipo", "dispatch-pro-drop-copy");

  const choose = document.createElement("button");
  choose.type = "button";
  choose.className = "dispatch-pro-choose";
  choose.textContent = "Elegir archivo";

  const rules = el("small", "Formato CSV · hasta 10 MB", "dispatch-pro-drop-rules");

  const template = document.createElement("a");
  template.href = `/api/dispatch/templates/${kind}`;
  template.download = `${kind}.csv`;
  template.className = "dispatch-pro-template-link";
  template.append(icon("download"), document.createTextNode("Descargar plantilla"));
  template.addEventListener("click", (event) => event.stopPropagation());

  drop.append(uploadIcon, dropStrong, dropCopy, choose, rules, template);

  const progress = el("div", null, "dispatch-pro-progress");
  progress.hidden = true;
  const progressTop = el("div", null, "dispatch-pro-progress-top");
  const progressTitle = el("strong", "Validando archivo…");
  const progressFile = el("small", "");
  progressTop.append(progressTitle, progressFile);
  progress.append(progressTop, el("div", "", "dispatch-pro-progress-bar"));

  const filePanel = el("div", null, "dispatch-pro-file-panel");
  filePanel.hidden = true;
  const fileIcon = el("span", null, "dispatch-pro-file-icon");
  fileIcon.append(icon("file"));
  const fileCopy = el("div", null, "dispatch-pro-loaded-copy");
  const fileName = el("strong", "");
  const fileMeta = el("small", "");
  const reusedBadge = el(
    "span",
    "",
    "dispatch-pro-reused-badge",
  );
  reusedBadge.hidden = true;
  fileCopy.append(fileName, fileMeta, reusedBadge);
  const fileState = el("span", "", "dispatch-pro-state-badge");
  filePanel.append(fileIcon, fileCopy, fileState);

  const actions = el("div", null, "dispatch-pro-file-actions");
  actions.hidden = true;

  const replace = document.createElement("button");
  replace.type = "button";
  replace.className = "dispatch-pro-text-action";
  replace.append(icon("refresh"), document.createTextNode("Reemplazar"));

  const reviewColumns = document.createElement("button");
  reviewColumns.type = "button";
  reviewColumns.className = "dispatch-pro-text-action";
  reviewColumns.append(icon("columns"), document.createTextNode("Ver columnas"));

  const reviewProblems = document.createElement("button");
  reviewProblems.type = "button";
  reviewProblems.className = "dispatch-pro-text-action";
  reviewProblems.append(icon("file"), document.createTextNode("Revisar problemas"));
  reviewProblems.hidden = true;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "dispatch-pro-text-action is-danger";
  remove.append(icon("trash"), document.createTextNode("Quitar"));

  actions.append(replace, reviewColumns, reviewProblems, remove);

  const notice = el("div", null, "dispatch-pro-card-notice");
  notice.hidden = true;

  uploadView.append(drop, progress, filePanel, actions, notice);

  const previousView = el("div", null, "dispatch-pro-source-view");
  previousView.dataset.sourceView = "reuse";
  previousView.hidden = true;

  const previousHead = el("div", null, "dispatch-pro-library-head");
  previousHead.append(
    el(
      "strong",
      kind === "orders" ? "Tus cargas anteriores" : "Tus flotas guardadas",
    ),
    el(
      "small",
      kind === "orders"
        ? "Reutilizá una versión ya validada."
        : "Elegí una flota guardada y volvé a validarla.",
    ),
  );

  const previousList = el("div", null, "dispatch-pro-inline-library");

  const previousEmpty = el("div", null, "dispatch-pro-library-empty");
  previousEmpty.hidden = true;
  previousEmpty.append(
    icon("history"),
    el("p", "Todavía no tenés cargas guardadas."),
  );
  const previousEmptyUpload = document.createElement("button");
  previousEmptyUpload.type = "button";
  previousEmptyUpload.className = "dispatch-pro-secondary-button";
  previousEmptyUpload.textContent = "Subir nuevo";
  previousEmpty.append(previousEmptyUpload);

  const previousAll = document.createElement("button");
  previousAll.type = "button";
  previousAll.className = "dispatch-pro-text-action dispatch-pro-view-all";
  previousAll.textContent = "Ver todas";

  previousView.append(previousHead, previousList, previousEmpty, previousAll);

  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  file.hidden = true;

  card.append(
    accent,
    header,
    switcher,
    uploadView,
    previousView,
    file,
  );

  function setMode(mode) {
    const upload = mode !== "reuse";
    uploadTab.setAttribute("aria-pressed", String(upload));
    reuseTab.setAttribute("aria-pressed", String(!upload));
    uploadView.hidden = !upload;
    previousView.hidden = upload;
  }

  uploadTab.onclick = () => setMode("upload");
  reuseTab.onclick = () => setMode("reuse");
  previousEmptyUpload.onclick = () => setMode("upload");

  return {
    card,
    drop,
    dropStrong,
    choose,
    progress,
    progressTitle,
    progressFile,
    filePanel,
    fileName,
    fileState,
    fileMeta,
    reusedBadge,
    actions,
    replace,
    reviewColumns,
    reviewProblems,
    remove,
    notice,
    file,
    uploadTab,
    reuseTab,
    previousView,
    previousList,
    previousEmpty,
    previousEmptyUpload,
    previousAll,
    setMode,
  };
}
