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

export function createDropCard(kind, contract, onGuide) {
  const card = el("section", null, "dispatch-panel dispatch-upload-card");
  card.dataset.kind = kind;
  card.id = `dispatch-upload-${kind}`;

  const head = el("div", null, "dispatch-upload-card-head");
  const titleWrap = el("div");
  titleWrap.append(
    el(
      "span",
      kind === "orders" ? "1 · Órdenes" : "2 · Flota",
      "dispatch-kicker",
    ),
    el("h2", contract.label),
    el("p", contract.role),
  );

  const status = el(
    "span",
    "○ Sin archivo",
    "dispatch-upload-status is-neutral",
  );
  head.append(titleWrap, status);

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
    el(
      "strong",
      kind === "orders"
        ? "Arrastrá tu CSV de órdenes acá"
        : "Arrastrá tu CSV de flota acá",
    ),
    el("span", "Elegir archivo", "dispatch-upload-drop-action"),
    el(
      "small",
      "CSV UTF-8 · hasta 10 MB · separador ; o ,",
    ),
  );

  const progress = el("div", null, "dispatch-upload-progress");
  progress.hidden = true;
  progress.append(
    el("strong", "Validando tu archivo…"),
    el("div", "", "dispatch-upload-progress-bar"),
    el(
      "small",
      "Leyendo → Validando estructura → Revisando reglas → Guardando",
    ),
  );

  const fileRow = el("div", null, "dispatch-file-row");
  fileRow.hidden = true;
  const fileInfo = el("div", null, "dispatch-file-info");
  const fileName = el("strong", "");
  const fileMeta = el("small", "");
  fileInfo.append(fileName, fileMeta);
  const replace = document.createElement("button");
  replace.type = "button";
  replace.className = "dispatch-text-action";
  replace.textContent = "Reemplazar";
  fileRow.append(el("span", "CSV", "dispatch-file-icon"), fileInfo, replace);

  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  file.hidden = true;

  const actions = el("div", null, "dispatch-upload-links");
  const template = document.createElement("a");
  template.href = `/api/dispatch/templates/${kind}`;
  template.download = `${kind}.csv`;
  template.textContent = "↓ Descargar plantilla";
  const example = document.createElement("a");
  example.href = `/api/dispatch/examples/${kind}`;
  example.download = `${kind}_ejemplo.csv`;
  example.textContent = "↗ Ver ejemplo";
  const guide = document.createElement("button");
  guide.type = "button";
  guide.className = "dispatch-text-action";
  guide.textContent = "ⓘ Guía de formato";
  guide.onclick = () => onGuide(kind, guide);
  actions.append(template, example, guide);

  const fields = el("div", null, "dispatch-upload-fields");
  fields.hidden = true;
  const label = document.createElement("label");
  label.append(el("span", "Nombre de la carga"));
  const labelInput = document.createElement("input");
  labelInput.maxLength = 120;
  label.append(labelInput);
  fields.append(label);

  let defaultInput = null;
  if (kind === "fleet") {
    const defaultLabel = document.createElement("label");
    defaultLabel.className = "dispatch-check-label";
    defaultInput = document.createElement("input");
    defaultInput.type = "checkbox";
    defaultInput.checked = true;
    defaultLabel.append(
      defaultInput,
      document.createTextNode(" Usar como flota vigente"),
      el(
        "small",
        "Las próximas corridas la usarán automáticamente.",
      ),
    );
    fields.append(defaultLabel);
  }

  const notice = el("div", null, "dispatch-card-notice");
  notice.hidden = true;
  const report = el("div", null, "dispatch-validation-report");
  report.setAttribute("aria-live", "polite");
  const understood = el("div", null, "dispatch-upload-profile");
  const library = el("div", null, "dispatch-library");

  card.append(
    head,
    progress,
    fileRow,
    drop,
    file,
    actions,
    fields,
    notice,
    report,
    understood,
    library,
  );

  return {
    card,
    status,
    drop,
    progress,
    fileRow,
    fileName,
    fileMeta,
    replace,
    file,
    fields,
    labelInput,
    defaultInput,
    notice,
    report,
    understood,
    library,
  };
}
