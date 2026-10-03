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

export function createDropCard(kind, contract) {
  const card = el(
    "section",
    null,
    `dispatch-panel dispatch-upload-card dispatch-upload-card--${kind}`,
  );
  card.dataset.kind = kind;

  const header = el("div", null, "dispatch-upload-card-header");
  const copy = el("div");
  const requiredCount = contract.columns.filter((column) => column.required).length;
  const optionalCount = contract.columns.length - requiredCount;
  copy.append(
    el(
      "span",
      kind === "orders"
        ? "01 · Demanda"
        : "02 · Recursos",
      "dispatch-kicker",
    ),
    el("h2", contract.label),
    el(
      "p",
      kind === "orders"
        ? "Qué productos y cantidades deben transportarse desde Córdoba hacia cada destino."
        : "Una fila por camión real, propio o tercerizado, con su capacidad y atributos disponibles.",
    ),
    el(
      "small",
      `${requiredCount} columnas mínimas · ${optionalCount} opcionales para decisiones posteriores`,
      "dispatch-upload-contract-summary",
    ),
  );

  const template = document.createElement("a");
  template.href = `/api/dispatch/templates/${kind}`;
  template.download = `${kind}.csv`;
  template.className = "dispatch-template-button";
  template.textContent = "Descargar plantilla";

  header.append(copy, template);

  const drop = document.createElement("button");
  drop.type = "button";
  drop.className = "dispatch-upload-drop";
  drop.setAttribute(
    "aria-label",
    kind === "orders"
      ? "Elegir archivo CSV de órdenes"
      : "Elegir archivo CSV de flota",
  );
  drop.append(
    el("span", "⇧", "dispatch-upload-icon"),
    el(
      "strong",
      kind === "orders"
        ? "Arrastrá orders.csv acá"
        : "Arrastrá fleet.csv acá",
    ),
    el(
      "span",
      "o hacé clic para elegirlo desde tu equipo",
      "dispatch-upload-drop-copy",
    ),
    el("small", "CSV UTF-8 · hasta 10 MB"),
  );

  const progress = el("div", null, "dispatch-upload-progress");
  progress.hidden = true;
  const progressTitle = el("strong", "Validando estructura…");
  const progressFile = el("small", "");
  progress.append(
    progressTitle,
    el("div", "", "dispatch-upload-progress-bar"),
    progressFile,
  );

  const filePanel = el("div", null, "dispatch-file-panel");
  filePanel.hidden = true;
  const fileName = el("strong", "");
  const fileState = el("span", "", "dispatch-file-state");
  const fileMeta = el("small", "");
  filePanel.append(
    el("span", "CSV", "dispatch-file-icon"),
    el("div", null, "dispatch-file-copy"),
  );
  filePanel.querySelector(".dispatch-file-copy").append(
    fileName,
    fileState,
    fileMeta,
  );

  const actions = el("div", null, "dispatch-file-actions");
  const replace = document.createElement("button");
  replace.type = "button";
  replace.className = "dispatch-text-action";
  replace.textContent = "Reemplazar archivo";

  const reviewColumns = document.createElement("button");
  reviewColumns.type = "button";
  reviewColumns.className = "dispatch-text-action";
  reviewColumns.textContent = "Revisar columnas";

  const reviewProblems = document.createElement("button");
  reviewProblems.type = "button";
  reviewProblems.className = "dispatch-text-action";
  reviewProblems.textContent = "Revisar problemas";
  reviewProblems.hidden = true;

  actions.append(replace, reviewColumns, reviewProblems);

  const previous = document.createElement("button");
  previous.type = "button";
  previous.className = "dispatch-previous-button";
  previous.textContent = kind === "orders"
    ? "Usar una carga anterior →"
    : "Usar una flota guardada →";

  const notice = el("div", null, "dispatch-card-notice");
  notice.hidden = true;

  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  file.hidden = true;

  card.append(
    header,
    drop,
    progress,
    filePanel,
    actions,
    previous,
    notice,
    file,
  );

  return {
    card,
    drop,
    progress,
    progressTitle,
    progressFile,
    filePanel,
    fileName,
    fileState,
    fileMeta,
    actions,
    replace,
    reviewColumns,
    reviewProblems,
    previous,
    notice,
    file,
  };
}
