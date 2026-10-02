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
  const row = document.createElement("tr");
  const values = [
    item.row || "—",
    item.column || "—",
    item.value ?? "—",
    item.hint || item.message || "Revisá el dato.",
  ];
  for (const value of values) {
    row.append(text("td", value));
  }
  return row;
}

export function renderValidationReport(root, report, state = null) {
  root.replaceChildren();
  if (!report) {
    return;
  }

  const errors = Number(report.counts?.errors || 0);
  const warnings = Number(report.counts?.warnings || 0);
  if (!errors && !warnings) {
    return;
  }

  const summary = text("div", "", "dispatch-validation-summary");
  if (errors) {
    summary.append(
      text(
        "strong",
        (
          `Encontramos ${errors} ${errors === 1 ? "error" : "errores"} `
          + `en ${report.rows || 0} filas.`
        ),
      ),
      text(
        "p",
        "No se guardó: corregilos y volvé a cargarlo.",
      ),
    );
  } else {
    summary.append(
      text(
        "strong",
        `${warnings} ${warnings === 1 ? "aviso" : "avisos"} para revisar`,
      ),
      text(
        "p",
        state?.saved
          ? "El archivo está guardado y podés continuar."
          : "El archivo es válido.",
      ),
    );
  }
  root.append(summary);

  for (const group of groupProblems(report)) {
    const details = document.createElement("details");
    details.className = `dispatch-validation-group is-${group.severity}`;
    const summaryNode = document.createElement("summary");
    summaryNode.textContent = (
      `${group.items.length} `
      + `${group.items.length === 1 ? "fila" : "filas"}: `
      + group.title
    );
    details.append(summaryNode);

    const wrap = text("div", "", "dispatch-table-wrap");
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["Fila", "Columna", "Valor", "Cómo corregirlo"].forEach(
      (value) => headRow.append(text("th", value)),
    );
    head.append(headRow);

    const body = document.createElement("tbody");
    group.items.slice(0, 5).forEach((item) => {
      body.append(issueRow(item));
    });
    table.append(head, body);
    wrap.append(table);
    details.append(wrap);

    if (group.items.length > 5) {
      const all = document.createElement("button");
      all.type = "button";
      all.textContent = `Ver las ${group.items.length} filas`;
      all.onclick = () => {
        body.replaceChildren();
        group.items.forEach((item) => body.append(issueRow(item)));
        all.remove();
      };
      details.append(all);
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

  const button = document.createElement("button");
  button.type = "button";
  button.className = "dispatch-text-action";
  button.textContent = "Descargar informe de errores (CSV)";
  button.onclick = () => {
    const rows = [
      [
        "tipo",
        "codigo",
        "fila",
        "columna",
        "valor",
        "mensaje",
        "como_corregir",
      ],
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
        "aviso",
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
