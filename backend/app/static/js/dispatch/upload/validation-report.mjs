import {csv, download} from "../shared.mjs";
import {groupProblems} from "./selectors.mjs";

function text(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  node.textContent = value;
  return node;
}

function issueRow(item) {
  const row = document.createElement("li");
  const where = [
    item.row ? `fila ${item.row}` : null,
    item.column ? `columna ${item.column}` : null,
  ].filter(Boolean).join(" · ");

  row.append(
    text("strong", where || "Archivo"),
    document.createTextNode(" — "),
    text("span", item.message || "Problema de validación"),
  );
  if (item.value !== undefined) {
    row.append(text("small", `Valor: ${item.value}`));
  }
  if (item.hint) {
    row.append(text("small", `Cómo corregirlo: ${item.hint}`));
  }
  return row;
}

export function renderValidationReport(root, report) {
  root.replaceChildren();
  if (!report) {
    return;
  }

  const errors = Number(report.counts?.errors || 0);
  const warnings = Number(report.counts?.warnings || 0);
  const summary = document.createElement("div");
  summary.className = "dispatch-validation-summary";
  summary.append(
    text(
      "strong",
      `${errors} errores y ${warnings} advertencias en ${report.rows || 0} filas`,
    ),
  );

  if (report.valid) {
    summary.append(
      text(
        "p",
        warnings
          ? "El archivo es válido. Revisá las advertencias antes de continuar."
          : "El archivo cumple el contrato y está listo para guardarse.",
      ),
    );
  } else {
    summary.append(
      text(
        "p",
        "No se guardó. Corregí los errores y volvé a cargarlo.",
      ),
    );
  }
  root.append(summary);

  for (const group of groupProblems(report)) {
    const details = document.createElement("details");
    details.className = `dispatch-validation-group is-${group.severity}`;
    const summaryNode = document.createElement("summary");
    summaryNode.textContent = (
      `${group.items.length} ${group.items.length === 1 ? "caso" : "casos"} · `
      + group.title
    );
    details.append(summaryNode);

    const list = document.createElement("ol");
    group.items.slice(0, 5).forEach((item) => list.append(issueRow(item)));
    details.append(list);

    if (group.items.length > 5) {
      details.append(
        text(
          "small",
          `Se muestran 5 de ${group.items.length} casos de este tipo.`,
        ),
      );
    }
    root.append(details);
  }

  if (report.truncated) {
    root.append(
      text(
        "p",
        "Mostramos los primeros 100 problemas; corregí estos y volvé a validar.",
        "dispatch-alert",
      ),
    );
  }

  if (errors || warnings) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Descargar informe de errores (CSV)";
    button.onclick = () => {
      const rows = [
        ["tipo", "codigo", "fila", "columna", "valor", "mensaje", "como_corregir"],
        ...(report.errors || []).map((item) => [
          "error",
          item.code,
          item.row,
          item.column,
          item.value,
          item.message,
          item.hint,
        ]),
        ...(report.warnings || []).map((item) => [
          "advertencia",
          item.code,
          item.row,
          item.column,
          item.value,
          item.message,
          item.hint,
        ]),
      ];
      download(
        "dation_informe_validacion.csv",
        csv(rows),
        "text/csv;charset=utf-8",
      );
    };
    root.append(button);
  }
}
