import {
  continueState,
  deriveCardState,
  technicalPreflightErrors,
} from "./selectors.mjs";

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

function technicalChecklist() {
  const list = el("div", null, "dispatch-quality-checks");
  [
    "Estructura correcta",
    "Columnas correctas",
    "Tipos de datos correctos",
  ].forEach((label) => {
    list.append(el("span", `✓ ${label}`));
  });
  return list;
}

function fileRow({
  kind,
  report,
  dataset,
  phase,
  saveError,
  storageAvailable,
  onReview,
}) {
  const row = el("article", null, "dispatch-quality-row");
  const copy = el("div");
  const name = kind === "orders"
    ? "Órdenes de envío"
    : "Flota disponible";

  const state = deriveCardState({
    report,
    dataset,
    saveError,
    phase,
    storageAvailable,
  });

  copy.append(
    el("strong", name),
    el("span", state.label, `is-${state.tone}`),
  );

  const errors = Number(report?.counts?.errors || 0);
  const warnings = Number(report?.counts?.warnings || 0);
  if (report?.valid && !errors) {
    copy.append(technicalChecklist());
  }

  row.append(copy);

  if (errors || warnings) {
    const review = document.createElement("button");
    review.type = "button";
    review.className = "dispatch-text-action";
    review.textContent = errors
      ? "Revisar problemas"
      : "Ver observaciones";
    review.onclick = () => onReview(kind, review);
    row.append(review);
  }

  return row;
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
  },
) {
  root.replaceChildren();
  root.className = "dispatch-panel dispatch-quality-panel";
  root.append(
    el("h2", "Validación de archivos"),
    el(
      "p",
      (
        "Comprobamos que ambos archivos tengan la estructura y "
        + "los datos necesarios para continuar."
      ),
    ),
  );

  const rows = el("div", null, "dispatch-quality-list");
  rows.append(
    fileRow({
      kind: "orders",
      report: reports.orders,
      dataset: datasets.orders,
      phase: phases.orders,
      saveError: saveErrors.orders,
      storageAvailable,
      onReview,
    }),
    fileRow({
      kind: "fleet",
      report: reports.fleet,
      dataset: datasets.fleet,
      phase: phases.fleet,
      saveError: saveErrors.fleet,
      storageAvailable,
      onReview,
    }),
  );

  const relationErrors = technicalPreflightErrors(preflight);
  if (relationErrors.length) {
    const relation = el(
      "article",
      null,
      "dispatch-quality-row dispatch-quality-row--relation is-error",
    );
    const copy = el("div");
    copy.append(
      el("strong", "Compatibilidad entre archivos"),
      el(
        "span",
        (
          `⛔ ${relationErrors.length} `
          + `${relationErrors.length === 1 ? "problema" : "problemas"}`
        ),
        "is-error",
      ),
    );
    const review = document.createElement("button");
    review.type = "button";
    review.className = "dispatch-text-action";
    review.textContent = "Revisar problemas";
    review.onclick = () => onReviewRelations(review);
    relation.append(copy, review);
    rows.append(relation);
  }

  root.append(rows);

  const final = continueState({
    storageAvailable,
    orders: datasets.orders,
    fleet: datasets.fleet,
    reports,
    preflight,
    phases,
    saveErrors,
  });

  const result = el(
    "div",
    null,
    `dispatch-quality-result is-${final.kind}`,
  );
  result.textContent = final.enabled
    ? "✓ Todos los controles fueron superados"
    : final.message;
  root.append(result);
}
