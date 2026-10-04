import {technicalPreflightErrors} from "./selectors.mjs";

function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function icon(name) {
  const paths = {
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
    warning: '<path d="M12 3 2.5 20h19Z"/><path d="M12 9v4M12 17h.01"/>',
    error: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    pending: '<circle cx="12" cy="12" r="9"/>',
    loader: '<path d="M21 12a9 9 0 1 1-3-6.7"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"/>',
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("dispatch-pro-icon");
  svg.innerHTML = paths[name] || paths.pending;
  return svg;
}

const STRUCTURE_CODES = new Set([
  "INVALID_ENCODING",
  "EMPTY_FILE",
  "INVALID_DELIMITER",
  "MISSING_HEADER",
  "DUPLICATE_COLUMN",
  "ALIAS_CONFLICT",
  "LEGACY_MIXED",
  "ROW_LENGTH",
  "NO_DATA_ROWS",
  "EXTRA_COLUMN",
  "LEGACY_FLEET_POOL_FORMAT",
]);

const REQUIRED_CODES = new Set([
  "MISSING_COLUMN",
  "REQUIRED_EMPTY",
]);

function toneIcon(tone) {
  return tone === "success"
    ? "check"
    : tone === "warning"
      ? "warning"
      : tone === "error"
        ? "error"
        : tone === "validating"
          ? "loader"
          : "pending";
}

function stateLabel(tone) {
  return {
    success: "Correcto",
    warning: "Aviso",
    error: "Error",
    validating: "Revisando",
    pending: "Pendiente",
  }[tone] || "Pendiente";
}

function issuesFor(report, bucket) {
  const all = [
    ...(report?.errors || []).map((item) => ({...item, severity: "error"})),
    ...(report?.warnings || []).map((item) => ({...item, severity: "warning"})),
  ];
  return all.filter((item) => {
    const code = item.code || "";
    if (bucket === "structure") return STRUCTURE_CODES.has(code);
    if (bucket === "required") return REQUIRED_CODES.has(code);
    return !STRUCTURE_CODES.has(code) && !REQUIRED_CODES.has(code);
  });
}

function requiredStats(report, requiredCount) {
  const entries = Object.values(report?.completeness || {}).filter(
    (item) => item?.required,
  );
  const complete = entries.filter(
    (item) => item.present && item.complete,
  ).length;
  return {
    complete: report ? complete : 0,
    total: requiredCount,
  };
}

function optionalStats(report, optionalCount) {
  const entries = Object.values(report?.completeness || {}).filter(
    (item) => item && !item.required,
  );
  const complete = entries.filter(
    (item) => item.present && item.complete,
  ).length;
  return {
    complete: report ? complete : 0,
    total: optionalCount,
  };
}

function rowTone(report, phase, bucket, requiredCount) {
  if (phase !== "idle") {
    return bucket === "structure" ? "validating" : "pending";
  }
  if (!report) return "pending";

  if (bucket === "structure" && report.detected_format === "legacy_mixed") {
    return "error";
  }

  if (bucket === "required") {
    const required = requiredStats(report, requiredCount);
    if (required.complete < required.total) return "error";
  }

  const issues = issuesFor(report, bucket);
  if (issues.some((item) => item.severity === "error")) return "error";
  if (issues.some((item) => item.severity === "warning")) return "warning";
  return "success";
}

function rowMetric(bucket, report, requiredCount) {
  if (bucket === "required") {
    const stats = requiredStats(report, requiredCount);
    return `${stats.complete} de ${stats.total}`;
  }
  return stateLabel(rowTone(report, "idle", bucket, requiredCount));
}

function issueCopy(issue) {
  if (!issue) return null;
  const where = [
    issue.column ? `columna ${issue.column}` : null,
    issue.row ? `fila ${issue.row}` : null,
  ].filter(Boolean).join(", ");
  return [
    issue.message || issue.detail || "Hay un dato para revisar.",
    where ? `Dónde: ${where}.` : null,
    issue.hint ? `Cómo arreglarlo: ${issue.hint}` : null,
  ].filter(Boolean).join(" ");
}

function validationRow({
  label,
  bucket,
  report,
  phase,
  requiredCount,
  kind,
  onReview,
  onReplace,
}) {
  const tone = rowTone(report, phase, bucket, requiredCount);
  const row = el(
    "div",
    null,
    `dispatch-pro-validation-row is-${tone}`,
  );
  row.dataset.validationBucket = bucket;

  const line = el("div", null, "dispatch-pro-validation-row-line");
  const state = el("span", null, "dispatch-pro-validation-row-icon");
  state.append(icon(toneIcon(tone)));
  const labelNode = el("span", label, "dispatch-pro-validation-row-label");
  const metric = el(
    "strong",
    bucket === "required"
      ? rowMetric(bucket, report, requiredCount)
      : stateLabel(tone),
    "dispatch-pro-validation-row-metric",
  );
  line.append(state, labelNode, metric);
  row.append(line);

  if (tone === "error" || tone === "warning") {
    const problems = issuesFor(report, bucket);
    const first = problems.find((item) => item.severity === "error")
      || problems[0];
    const detail = el("div", null, "dispatch-pro-validation-detail");
    detail.append(
      el(
        "p",
        issueCopy(first)
          || (tone === "error"
            ? "Hay datos que necesitás corregir antes de continuar."
            : "Hay una observación para revisar. Podés continuar si no bloquea este paso."),
      ),
    );

    const actions = el("div", null, "dispatch-pro-validation-actions");
    const replace = document.createElement("button");
    replace.type = "button";
    replace.className = "dispatch-pro-text-action";
    replace.textContent = "Reemplazar archivo";
    replace.onclick = () => onReplace(kind);

    const template = document.createElement("a");
    template.href = `/api/dispatch/templates/${kind}`;
    template.download = `${kind}.csv`;
    template.className = "dispatch-pro-text-action";
    template.textContent = "Descargar plantilla";

    const review = document.createElement("button");
    review.type = "button";
    review.className = "dispatch-pro-text-action";
    review.textContent = "Ver detalle";
    review.onclick = () => onReview(kind, review);
    actions.append(replace, template, review);
    detail.append(actions);
    row.append(detail);
  }

  return {row, tone};
}

export function renderInlineValidation(
  ref,
  {
    kind,
    report,
    phase,
    requiredCount,
    optionalCount,
    onReview,
    onReplace,
  },
) {
  ref.validationBody.replaceChildren();

  const definitions = [
    ["Estructura del archivo", "structure"],
    ["Columnas mínimas", "required"],
    ["Tipos de datos", "types"],
  ];

  const built = definitions.map(([label, bucket]) => (
    validationRow({
      label,
      bucket,
      report,
      phase,
      requiredCount,
      kind,
      onReview,
      onReplace,
    })
  ));

  const allSuccess = built.every(({tone}) => tone === "success");
  const hasError = built.some(({tone}) => tone === "error");
  const hasWarning = built.some(({tone}) => tone === "warning");
  const validating = phase !== "idle";

  const tone = validating
    ? "validating"
    : hasError
      ? "error"
      : hasWarning
        ? "warning"
        : allSuccess
          ? "success"
          : "pending";

  ref.connector.className = `dispatch-pro-validation-connector is-${tone}`;
  ref.validation.className = `dispatch-pro-inline-validation is-${tone}`;
  ref.validationHint.textContent = validating
    ? "Validando…"
    : report
      ? allSuccess
        ? "Archivo listo."
        : hasError
          ? "Revisá los errores para continuar."
          : "Podés continuar con avisos."
      : "Empieza apenas cargás el archivo.";

  if (allSuccess) {
    const details = document.createElement("details");
    details.className = "dispatch-pro-validation-success";
    const summary = document.createElement("summary");
    const summaryIcon = el("span", null, "dispatch-pro-validation-row-icon");
    summaryIcon.append(icon("check"));
    summary.append(
      summaryIcon,
      el("strong", "Todos los controles correctos"),
      el("small", "Ver detalle"),
    );
    const body = el("div", null, "dispatch-pro-validation-success-body");
    built.forEach(({row}) => body.append(row));
    details.append(summary, body);
    ref.validationBody.append(details);
  } else {
    const priority = {error: 0, warning: 1, validating: 2, pending: 3, success: 4};
    built
      .sort((a, b) => priority[a.tone] - priority[b.tone])
      .forEach(({row}, index) => {
        row.style.setProperty("--validation-index", String(index));
        ref.validationBody.append(row);
      });
  }

  const optional = optionalStats(report, optionalCount);
  const optionalNote = el(
    "small",
    report
      ? `Columnas opcionales: ${optional.complete} de ${optional.total}`
      : `Columnas opcionales: 0 de ${optional.total}`,
    "dispatch-pro-optional-note",
  );
  optionalNote.title = "Las columnas opcionales habilitan decisiones posteriores y no bloquean este paso.";
  ref.validationBody.append(optionalNote);

  return tone;
}

export function renderCompatibilityStrip(
  root,
  {
    datasets,
    preflight,
    onReviewRelations,
  },
) {
  root.replaceChildren();
  root.className = "dispatch-pro-compatibility";
  root.hidden = !(datasets.orders && datasets.fleet);
  if (root.hidden) return;

  const relationErrors = technicalPreflightErrors(preflight);
  const tone = !preflight
    ? "validating"
    : relationErrors.length
      ? "error"
      : "success";
  root.classList.add(`is-${tone}`);

  const statusIcon = el("span", null, "dispatch-pro-compatibility-icon");
  statusIcon.append(icon(toneIcon(tone)));

  const copy = el("div", null, "dispatch-pro-compatibility-copy");
  copy.append(
    el("strong", "Entre archivos"),
    el(
      "span",
      tone === "validating"
        ? "Revisando compatibilidad entre Órdenes y Flota…"
        : tone === "error"
          ? "Hay referencias entre los archivos que necesitás corregir."
          : "Compatibilidad correcta entre Órdenes y Flota.",
    ),
  );

  root.append(statusIcon, copy);
  if (relationErrors.length) {
    const review = document.createElement("button");
    review.type = "button";
    review.className = "dispatch-pro-text-action";
    review.textContent = "Revisar";
    review.onclick = () => onReviewRelations(review);
    root.append(review);
  }
}
