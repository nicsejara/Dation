import {csv, download} from "../shared.mjs";
import {groupProblems} from "./selectors.mjs";

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

export function createValidationDrawer() {
  document
    .querySelectorAll(".dispatch-validation-overlay")
    .forEach((node) => node.remove());

  const overlay = el("div", null, "dispatch-validation-overlay");
  overlay.hidden = true;
  const drawer = el("aside", null, "dispatch-validation-drawer");
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-label", "Problemas de validación");

  const head = el("div", null, "dispatch-validation-head");
  const title = el("h2", "Revisar problemas");
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar");
  close.textContent = "×";
  head.append(title, close);

  const content = el("div", null, "dispatch-validation-content");
  drawer.append(head, content);
  overlay.append(drawer);
  document.body.append(overlay);

  let opener = null;

  function render(report, filename) {
    content.replaceChildren();

    if (filename) {
      content.append(el("p", `Archivo: ${filename}`));
    }

    const groups = groupProblems(report);
    if (!groups.length) {
      content.append(
        el("p", "No hay problemas técnicos para revisar."),
      );
      return;
    }

    groups.forEach((group) => {
      const section = el(
        "section",
        null,
        `dispatch-validation-group is-${group.severity}`,
      );
      section.append(
        el(
          "h3",
          (
            `${group.items.length} `
            + `${group.items.length === 1 ? "caso" : "casos"} · `
            + group.title
          ),
        ),
      );

      const wrap = el("div", null, "dispatch-table-wrap");
      const table = document.createElement("table");
      const thead = document.createElement("thead");
      const tr = document.createElement("tr");
      [
        "Fila",
        "Columna",
        "Problema",
        "Valor encontrado",
        "Cómo corregirlo",
      ].forEach((value) => tr.append(el("th", value)));
      thead.append(tr);

      const tbody = document.createElement("tbody");
      group.items.forEach((item) => {
        const row = document.createElement("tr");
        [
          item.row ?? "—",
          item.column ?? "—",
          item.message || item.detail || "Problema de validación",
          item.value ?? "—",
          item.hint || "Revisá el dato informado.",
        ].forEach((value) => row.append(el("td", value)));
        tbody.append(row);
      });
      table.append(thead, tbody);
      wrap.append(table);
      section.append(wrap);
      content.append(section);
    });

    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.className = "dispatch-text-action";
    downloadButton.textContent = "Descargar informe (CSV)";
    downloadButton.onclick = () => {
      const rows = [
        [
          "tipo",
          "codigo",
          "fila",
          "columna",
          "valor",
          "problema",
          "como_corregir",
        ],
        ...(report.errors || []).map((item) => [
          "error",
          item.code,
          item.row,
          item.column,
          item.value,
          item.message || item.detail,
          item.hint,
        ]),
        ...(report.warnings || []).map((item) => [
          "observacion",
          item.code,
          item.row,
          item.column,
          item.value,
          item.message || item.detail,
          item.hint,
        ]),
      ];
      download(
        "dation_validacion.csv",
        csv(rows),
        "text/csv;charset=utf-8",
      );
    };
    content.append(downloadButton);
  }

  function open({
    report,
    filename = null,
    source = null,
    heading = "Revisar problemas",
  }) {
    opener = source;
    title.textContent = heading;
    render(report, filename);
    overlay.hidden = false;
    document.body.classList.add("dispatch-drawer-open");
    close.focus();
  }

  function hide() {
    overlay.hidden = true;
    document.body.classList.remove("dispatch-drawer-open");
    opener?.focus();
  }

  close.onclick = hide;
  overlay.onclick = (event) => {
    if (event.target === overlay) {
      hide();
    }
  };
  overlay.onkeydown = (event) => {
    if (event.key === "Escape") {
      hide();
    }
  };

  return {open, close: hide};
}
