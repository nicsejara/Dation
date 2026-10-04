function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function icon(name) {
  const paths = {
    orders: '<path d="M9 5h6M9 9h6M9 13h4"/><path d="M7 3h10a2 2 0 0 1 2 2v14H5V5a2 2 0 0 1 2-2Z"/><path d="M8 19v2h8v-2"/>',
    fleet: '<path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    upload: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
    uploadCloud: '<path d="M16 16l-4-4-4 4M12 12v9"/><path d="M20.4 17.5A5 5 0 0 0 18 8.2 7 7 0 0 0 4.3 10.8 4 4 0 0 0 5 18h3"/>',
    folder: '<path d="M3 6h6l2 2h10v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    download: '<path d="M12 4v12"/><path d="m7 11 5 5 5-5"/><path d="M5 20h14"/>',
    refresh: '<path d="M20 6v5h-5"/><path d="M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5L20 15"/>',
    columns: '<path d="M4 5h16v14H4z"/><path d="M10 5v14M15 5v14"/>',
    close: '<path d="m7 7 10 10M17 7 7 17"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>',
    dot: '<circle cx="12" cy="12" r="4"/>',
    circle: '<circle cx="12" cy="12" r="8"/>',
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
    null,
    `dispatch-pro-requirement ${optional ? "is-optional" : "is-required"}`,
  );
  chip.append(
    icon(optional ? "circle" : "dot"),
    document.createTextNode(label),
  );
  chip.title = optional
    ? "Habilitan decisiones posteriores. No bloquean este paso."
    : "Necesarias para iniciar la Asignación de carga.";
  return chip;
}

function segmentButton(label, iconName, mode) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.mode = mode;
  const labelNode = el("span", label);
  button.append(icon(iconName), labelNode);
  return {button, labelNode};
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
  const intro = kind === "orders"
    ? "Cada fila es una orden, con sus productos, cantidades, origen, destino y fechas."
    : "Cada fila es un vehículo, con su capacidad, disponibilidad, costos y velocidad.";
  copy.append(
    el(
      "span",
      kind === "orders" ? "01 · DEMANDA" : "02 · RECURSOS",
      "dispatch-pro-eyebrow",
    ),
    el("h3", label),
    el("p", intro),
  );

  const headerState = el(
    "span",
    "Pendiente",
    "dispatch-pro-state-badge is-pending dispatch-pro-header-state",
  );
  header.append(entityIcon, copy, headerState);

  const requirementsRow = el("div", null, "dispatch-pro-requirements-row");
  const chips = el("div", null, "dispatch-pro-requirements");
  chips.append(
    requirementChip(`${requiredCount} mínimas`),
    requirementChip(`${optionalCount} opcionales`, true),
  );

  const template = document.createElement("a");
  template.href = `/api/dispatch/templates/${kind}`;
  template.download = `${kind}.csv`;
  template.className = "dispatch-pro-template-button";
  template.append(icon("download"), document.createTextNode("Descargar plantilla"));
  requirementsRow.append(chips, template);

  const switcher = el("div", null, "dispatch-pro-source-switch");
  switcher.setAttribute("role", "group");
  switcher.setAttribute("aria-label", `Cómo cargar ${label.toLowerCase()}`);

  const uploadSegment = segmentButton("Subir nuevo", "upload", "upload");
  const reuseSegment = segmentButton(
    "Reutilizar anterior",
    "history",
    "reuse",
  );
  const uploadTab = uploadSegment.button;
  const reuseTab = reuseSegment.button;
  const reuseLabel = reuseSegment.labelNode;
  uploadTab.setAttribute("aria-pressed", "true");
  reuseTab.setAttribute("aria-pressed", "false");
  switcher.append(uploadTab, reuseTab);

  const uploadView = el("div", null, "dispatch-pro-source-view");
  uploadView.dataset.sourceView = "upload";

  const uploadBlockLabel = el(
    "span",
    "1 · CARGAR ARCHIVO",
    "dispatch-pro-block-label",
  );

  const drop = el("div", null, "dispatch-pro-dropzone");
  drop.setAttribute("role", "button");
  drop.tabIndex = 0;
  drop.setAttribute(
    "aria-label",
    kind === "orders"
      ? "Elegir archivo CSV de órdenes"
      : "Elegir archivo CSV de flota",
  );

  const uploadHalo = el("span", null, "dispatch-pro-drop-halo");
  const uploadIcon = el("span", null, "dispatch-pro-drop-icon");
  uploadIcon.append(icon("uploadCloud"));
  uploadHalo.append(uploadIcon);

  const dropStrong = el(
    "strong",
    kind === "orders"
      ? "Arrastrá tu archivo de órdenes"
      : "Arrastrá tu archivo de flota",
  );
  const dropCopy = el(
    "span",
    "o elegilo desde tu equipo",
    "dispatch-pro-drop-copy",
  );

  const choose = document.createElement("button");
  choose.type = "button";
  choose.className = "dispatch-pro-choose";
  choose.append(icon("folder"), document.createTextNode("Elegir archivo"));

  const rules = el("div", null, "dispatch-pro-drop-rules");
  rules.append(
    el("span", ".CSV", "dispatch-pro-format-pill"),
    el("span", "Hasta 10 MB", "dispatch-pro-format-pill"),
  );

  drop.append(uploadHalo, dropStrong, dropCopy, choose, rules);

  const progress = el("div", null, "dispatch-pro-progress");
  progress.hidden = true;
  const progressTop = el("div", null, "dispatch-pro-progress-top");
  const progressCopy = el("div");
  const progressTitle = el("strong", "Validando archivo…");
  const progressFile = el("small", "");
  progressCopy.append(progressTitle, progressFile);
  const cancelUpload = document.createElement("button");
  cancelUpload.type = "button";
  cancelUpload.className = "dispatch-pro-text-action is-danger";
  cancelUpload.textContent = "Cancelar";
  progressTop.append(progressCopy, cancelUpload);
  progress.append(progressTop, el("div", "", "dispatch-pro-progress-bar"));

  const filePanel = el("div", null, "dispatch-pro-file-panel");
  filePanel.hidden = true;
  const fileIcon = el("span", null, "dispatch-pro-file-icon");
  fileIcon.append(icon("file"));
  const fileCopy = el("div", null, "dispatch-pro-loaded-copy");
  const fileName = el("strong", "");
  const fileMeta = el("div", null, "dispatch-pro-loaded-meta");
  const reusedBadge = el(
    "span",
    "",
    "dispatch-pro-reused-badge",
  );
  reusedBadge.hidden = true;
  fileCopy.append(fileName, fileMeta, reusedBadge);
  filePanel.append(fileIcon, fileCopy);

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

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "dispatch-pro-text-action is-danger";
  remove.append(icon("close"), document.createTextNode("Quitar"));

  actions.append(replace, reviewColumns, remove);

  const notice = el("div", null, "dispatch-pro-card-notice");
  notice.hidden = true;

  uploadView.append(
    uploadBlockLabel,
    drop,
    progress,
    filePanel,
    actions,
    notice,
  );

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
      "Elegí una versión guardada. Dation la valida otra vez antes de continuar.",
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
  previousAll.append(
    icon("history"),
    document.createTextNode("Ver historial completo →"),
  );

  previousView.append(previousHead, previousList, previousEmpty, previousAll);

  const connector = el("div", null, "dispatch-pro-validation-connector is-pending");
  const connectorDot = el("span", null, "dispatch-pro-validation-connector-dot");
  connector.append(connectorDot);

  const validation = el("section", null, "dispatch-pro-inline-validation");
  validation.setAttribute("aria-live", "polite");
  const validationHead = el("div", null, "dispatch-pro-inline-validation-head");
  const validationTitle = el(
    "span",
    "2 · VALIDACIÓN",
    "dispatch-pro-block-label",
  );
  const validationHint = el(
    "small",
    "Empieza apenas cargás el archivo.",
    "dispatch-pro-validation-hint",
  );
  validationHead.append(validationTitle, validationHint);
  const validationBody = el("div", null, "dispatch-pro-inline-validation-body");
  validation.append(validationHead, validationBody);

  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  file.hidden = true;

  card.append(
    accent,
    header,
    requirementsRow,
    switcher,
    uploadView,
    previousView,
    connector,
    validation,
    file,
  );

  function setMode(mode) {
    const upload = mode !== "reuse";
    uploadTab.setAttribute("aria-pressed", String(upload));
    reuseTab.setAttribute("aria-pressed", String(!upload));
    uploadView.hidden = !upload;
    previousView.hidden = upload;
  }

  function setReuseCount(count) {
    reuseLabel.textContent = count > 0
      ? `Reutilizar anterior · ${count}`
      : "Reutilizar anterior";
  }

  uploadTab.onclick = () => setMode("upload");
  reuseTab.onclick = () => setMode("reuse");
  previousEmptyUpload.onclick = () => setMode("upload");

  return {
    card,
    requiredCount,
    optionalCount,
    headerState,
    template,
    drop,
    dropStrong,
    choose,
    progress,
    progressTitle,
    progressFile,
    cancelUpload,
    filePanel,
    fileName,
    fileMeta,
    reusedBadge,
    actions,
    replace,
    reviewColumns,
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
    connector,
    validation,
    validationHint,
    validationBody,
    setMode,
    setReuseCount,
  };
}
