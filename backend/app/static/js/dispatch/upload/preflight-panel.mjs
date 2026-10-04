import {
  continueState,
  deriveCardState,
  technicalPreflightErrors,
} from "./selectors.mjs";

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
    orders: '<path d="M9 5h6M9 9h6M9 13h4"/><path d="M7 3h10a2 2 0 0 1 2 2v14H5V5a2 2 0 0 1 2-2Z"/>',
    fleet: '<path d="M3 7h11v9H3z"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"/>',
    chevron: '<path d="m9 8 6 4-6 4Z"/>',
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("dispatch-pro-icon");
  svg.innerHTML = paths[name] || paths.pending;
  return svg;
}

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

function fileTone({
  report,
  dataset,
  phase,
  saveError,
  storageAvailable,
}) {
  if (phase !== "idle") return "validating";
  if (saveError) return "error";
  const errors = Number(report?.counts?.errors || 0);
  const warnings = Number(report?.counts?.warnings || 0);
  if (errors) return "error";
  if (report?.valid || dataset) {
    return warnings ? "warning" : "success";
  }
  if (report && !report.valid) return "error";
  if (!storageAvailable && report?.valid) return "warning";
  return "pending";
}

function checkRows(report, phase) {
  if (phase !== "idle") {
    return [
      ["Estructura del archivo", "validating"],
      ["Columnas mínimas", "pending"],
      ["Tipos de datos", "pending"],
    ];
  }

  if (!report) {
    return [
      ["Estructura del archivo", "pending"],
      ["Columnas mínimas", "pending"],
      ["Tipos de datos", "pending"],
    ];
  }

  const completeness = report.completeness || {};
  const required = Object.values(completeness).filter(
    (item) => item?.required,
  );
  const missingRequired = required.filter(
    (item) => !item.present || !item.complete,
  );
  const errors = Number(report.counts?.errors || 0);
  const warnings = Number(report.counts?.warnings || 0);
  const structureTone = report.detected_format === "legacy_mixed"
    ? "error"
    : "success";

  return [
    ["Estructura del archivo", structureTone],
    ["Columnas mínimas", missingRequired.length ? "error" : "success"],
    [
      "Tipos de datos",
      errors ? "error" : warnings ? "warning" : "success",
    ],
  ];
}

function statusLabel(tone) {
  return {
    success: "Listo",
    warning: "Listo, con avisos",
    error: "Para corregir",
    validating: "Validando",
    pending: "Pendiente",
  }[tone] || "Pendiente";
}

function checkLabel(tone) {
  return {
    success: "Correcto",
    warning: "Aviso",
    error: "Error",
    validating: "Revisando",
    pending: "Pendiente",
  }[tone] || "Pendiente";
}

function fileValidationBlock({
  kind,
  report,
  dataset,
  phase,
  saveError,
  storageAvailable,
  onReview,
  onReplace,
}) {
  const tone = fileTone({
    report,
    dataset,
    phase,
    saveError,
    storageAvailable,
  });
  const rows = checkRows(report, phase);
  const problems = (
    Number(report?.counts?.errors || 0)
    + Number(report?.counts?.warnings || 0)
  );

  const details = document.createElement("details");
  details.className = `dispatch-pro-validation-file is-${tone}`;
  details.open = tone === "error" || tone === "warning";

  const summary = document.createElement("summary");
  const entity = el("span", null, "dispatch-pro-validation-entity");
  entity.append(icon(kind));
  const copy = el("span", null, "dispatch-pro-validation-summary-copy");
  copy.append(
    el("strong", kind === "orders" ? "Órdenes" : "Flota"),
    el(
      "small",
      rows.every(([, state]) => state === "success")
        ? "3 de 3 controles correctos"
        : tone === "validating"
          ? "Revisando el archivo…"
          : problems
            ? `${problems} ${problems === 1 ? "observación" : "observaciones"} para revisar`
            : "Controles pendientes",
    ),
  );
  const badge = el(
    "span",
    null,
    `dispatch-pro-state-badge is-${tone}`,
  );
  badge.append(icon(toneIcon(tone)), document.createTextNode(statusLabel(tone)));
  summary.append(entity, copy, badge);
  details.append(summary);

  const body = el("div", null, "dispatch-pro-validation-body");
  rows.forEach(([label, rowTone]) => {
    const row = el(
      "div",
      null,
      `dispatch-pro-validation-check is-${rowTone}`,
    );
    const stateIcon = el("span", null, "dispatch-pro-check-icon");
    stateIcon.append(icon(toneIcon(rowTone)));
    row.append(
      stateIcon,
      el("span", label),
      el("strong", checkLabel(rowTone)),
    );
    body.append(row);
  });

  if (problems || saveError) {
    const issue = el("div", null, "dispatch-pro-validation-actions");
    const review = document.createElement("button");
    review.type = "button";
    review.className = "dispatch-pro-secondary-button";
    review.textContent = Number(report?.counts?.errors || 0)
      ? "Revisar problemas"
      : "Ver avisos";
    review.onclick = () => onReview(kind, review);
    issue.append(review);

    if (onReplace) {
      const replace = document.createElement("button");
      replace.type = "button";
      replace.className = "dispatch-pro-text-action";
      replace.textContent = "Reemplazar archivo";
      replace.onclick = () => onReplace(kind);
      issue.append(replace);
    }
    body.append(issue);
  }

  details.append(body);
  return {details, tone};
}

function summaryState({
  storageAvailable,
  datasets,
  reports,
  phases,
  saveErrors,
  preflight,
}) {
  const relationErrors = technicalPreflightErrors(preflight);
  const files = ["orders", "fleet"].map((kind) => (
    fileTone({
      report: reports[kind],
      dataset: datasets[kind],
      phase: phases[kind],
      saveError: saveErrors[kind],
      storageAvailable,
    })
  ));

  const errors = (
    files.filter((tone) => tone === "error").length
    + (relationErrors.length ? 1 : 0)
  );
  const warnings = files.filter((tone) => tone === "warning").length;
  const correct = files.filter((tone) => tone === "success").length;
  const validating = files.some((tone) => tone === "validating");

  if (validating) {
    return {
      tone: "validating",
      title: "Revisando tus datos…",
      correct,
      warnings,
      errors,
    };
  }
  if (errors) {
    return {
      tone: "error",
      title: `Hay ${errors} ${errors === 1 ? "cosa" : "cosas"} para corregir.`,
      correct,
      warnings,
      errors,
    };
  }
  if (datasets.orders && datasets.fleet && reports.orders?.valid && reports.fleet?.valid) {
    return {
      tone: warnings ? "warning" : "success",
      title: warnings
        ? "Tus datos están listos, con avisos."
        : "Tus datos están listos.",
      correct: warnings ? Math.max(0, 2 - warnings) : 2,
      warnings,
      errors: 0,
    };
  }
  return {
    tone: "pending",
    title: "Cargá tus dos archivos para validar.",
    correct,
    warnings,
    errors,
  };
}

export function renderValidationPanel(
  root,
  {
    storageAvailable,
    datasets,
    reports,
    phases,
    saveErrors,
    preflight,
    onReview,
    onReviewRelations,
    onReplace,
  },
) {
  root.replaceChildren();
  root.className = "dispatch-pro-validation";
  root.setAttribute("aria-live", "polite");

  const state = summaryState({
    storageAvailable,
    datasets,
    reports,
    phases,
    saveErrors,
    preflight,
  });

  const head = el(
    "div",
    null,
    `dispatch-pro-validation-summary is-${state.tone}`,
  );
  const summaryIcon = el("span", null, "dispatch-pro-validation-summary-icon");
  summaryIcon.append(icon(toneIcon(state.tone)));
  const summaryCopy = el("div", null, "dispatch-pro-validation-summary-copy-main");
  summaryCopy.append(
    el("span", "VALIDACIÓN", "dispatch-pro-eyebrow"),
    el("h2", state.title),
    el(
      "p",
      "Revisamos lo mínimo para iniciar la Asignación de carga. Las columnas opcionales no bloquean este paso.",
    ),
  );

  const counters = el("div", null, "dispatch-pro-validation-counters");
  [
    [state.correct, "correctos", "success"],
    [state.warnings, "avisos", "warning"],
    [state.errors, "errores", "error"],
  ].forEach(([value, label, tone]) => {
    counters.append(
      el(
        "span",
        `${value} ${label}`,
        `dispatch-pro-counter is-${tone}`,
      ),
    );
  });
  summaryCopy.append(counters);
  head.append(summaryIcon, summaryCopy);
  root.append(head);

  const grid = el("div", null, "dispatch-pro-validation-grid");
  const orderBlock = fileValidationBlock({
    kind: "orders",
    report: reports.orders,
    dataset: datasets.orders,
    phase: phases.orders,
    saveError: saveErrors.orders,
    storageAvailable,
    onReview,
    onReplace,
  });
  const fleetBlock = fileValidationBlock({
    kind: "fleet",
    report: reports.fleet,
    dataset: datasets.fleet,
    phase: phases.fleet,
    saveError: saveErrors.fleet,
    storageAvailable,
    onReview,
    onReplace,
  });
  grid.append(orderBlock.details, fleetBlock.details);
  root.append(grid);

  if (datasets.orders && datasets.fleet) {
    const relationErrors = technicalPreflightErrors(preflight);
    const relationTone = !preflight
      ? "validating"
      : relationErrors.length
        ? "error"
        : "success";
    const relation = el(
      "div",
      null,
      `dispatch-pro-relation is-${relationTone}`,
    );
    const relationIcon = el("span", null, "dispatch-pro-relation-icon");
    relationIcon.append(icon("link"));
    const relationCopy = el("div");
    relationCopy.append(
      el("strong", "Compatibilidad entre archivos"),
      el(
        "small",
        relationTone === "validating"
          ? "Revisando referencias necesarias para continuar…"
          : relationTone === "error"
            ? `${relationErrors.length} ${relationErrors.length === 1 ? "problema" : "problemas"} entre Órdenes y Flota.`
            : "Las referencias necesarias entre Órdenes y Flota son consistentes.",
      ),
    );
    const relationBadge = el(
      "span",
      null,
      `dispatch-pro-state-badge is-${relationTone}`,
    );
    relationBadge.append(
      icon(toneIcon(relationTone)),
      document.createTextNode(statusLabel(relationTone)),
    );
    relation.append(relationIcon, relationCopy, relationBadge);

    if (relationErrors.length) {
      const review = document.createElement("button");
      review.type = "button";
      review.className = "dispatch-pro-text-action";
      review.textContent = "Revisar";
      review.onclick = () => onReviewRelations(review);
      relation.append(review);
    }
    root.append(relation);
  }

  const final = continueState({
    storageAvailable,
    orders: datasets.orders,
    fleet: datasets.fleet,
    reports,
    preflight,
    phases,
    saveErrors,
  });

  root.dataset.state = final.kind;
}
