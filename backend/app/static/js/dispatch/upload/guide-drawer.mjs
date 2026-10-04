function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function columnState(column, report) {
  const item = report?.completeness?.[column.name];
  if (!report) {
    return {
      tone: "pending",
      label: "Pendiente",
    };
  }
  if (!item) {
    return {
      tone: column.required ? "error" : "neutral",
      label: column.required ? "Falta" : "No informada",
    };
  }
  if (!item.present) {
    return {
      tone: column.required ? "error" : "neutral",
      label: column.required ? "Falta" : "Opcional pendiente",
    };
  }
  if (!item.complete && column.required) {
    return {
      tone: "warning",
      label: "Incompleta",
    };
  }
  return {
    tone: "success",
    label: "Encontrada",
  };
}

export function createGuideDrawer(contracts) {
  document
    .querySelectorAll(".dispatch-guide-overlay")
    .forEach((node) => node.remove());

  const overlay = el("div", null, "dispatch-guide-overlay");
  overlay.hidden = true;

  const drawer = el("aside", null, "dispatch-guide dispatch-pro-guide");
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-label", "Ver columnas");

  const head = el("div", null, "dispatch-guide-head");
  const headCopy = el("div");
  headCopy.append(
    el("span", "ESTRUCTURA DEL ARCHIVO", "dispatch-pro-eyebrow"),
    el("h2", "Ver columnas"),
  );
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar");
  close.textContent = "×";
  head.append(headCopy, close);

  const tabs = el("div", null, "dispatch-guide-tabs");
  const content = el("div", null, "dispatch-guide-content");
  drawer.append(head, tabs, content);
  overlay.append(drawer);
  document.body.append(overlay);

  let active = "orders";
  let opener = null;
  let activeReport = null;

  function renderContent() {
    content.replaceChildren();
    const contract = contracts.formats[active];

    const intro = el("div", null, "dispatch-pro-guide-intro");
    intro.append(
      el(
        "p",
        active === "orders"
          ? "Revisá qué columnas necesita Órdenes y cuáles podés completar más adelante."
          : "Revisá qué columnas necesita Flota y cuáles podés completar más adelante.",
      ),
    );
    content.append(intro);

    const wrap = el("div", null, "dispatch-table-wrap");
    const table = document.createElement("table");
    table.className = "dispatch-pro-columns-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    [
      "Columna",
      "Tipo",
      "Requisito",
      "Estado",
      "Para qué sirve",
    ].forEach((value) => headRow.append(el("th", value)));
    thead.append(headRow);

    const tbody = document.createElement("tbody");
    contract.columns.forEach((column) => {
      const row = document.createElement("tr");
      const state = columnState(column, activeReport);
      const requirement = column.required ? "Mínima" : "Opcional";
      const status = el(
        "span",
        state.label,
        `dispatch-pro-column-state is-${state.tone}`,
      );

      const nameCell = el("td");
      nameCell.append(
        el("code", column.name, "dispatch-pro-column-name"),
      );
      const typeCell = el("td", column.type || column.rule || "—");
      const requirementCell = el("td", requirement);
      const stateCell = el("td");
      stateCell.append(status);
      const descriptionCell = el("td", column.description || "—");
      row.append(
        nameCell,
        typeCell,
        requirementCell,
        stateCell,
        descriptionCell,
      );
      tbody.append(row);
    });

    table.append(thead, tbody);
    wrap.append(table);

    const rules = el(
      "p",
      (
        "CSV UTF-8 · hasta 10 MB · separador ; o , · "
        + "fechas AAAA-MM-DD o d/m/AAAA. "
        + "Las columnas mínimas son las necesarias para iniciar Asignación."
      ),
      "dispatch-guide-rules",
    );

    const template = document.createElement("a");
    template.href = `/api/dispatch/templates/${active}`;
    template.download = `${active}.csv`;
    template.className = "dispatch-pro-secondary-button";
    template.textContent = "Descargar plantilla";

    content.append(rules, wrap, template);
  }

  function renderTabs() {
    tabs.replaceChildren();
    [
      ["orders", "Órdenes"],
      ["fleet", "Flota"],
    ].forEach(([key, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.setAttribute("aria-pressed", String(active === key));
      button.onclick = () => {
        active = key;
        activeReport = null;
        renderTabs();
        renderContent();
      };
      tabs.append(button);
    });
  }

  function open(kind = "orders", source = null, report = null) {
    active = kind;
    opener = source;
    activeReport = report;
    renderTabs();
    renderContent();
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
    if (event.target === overlay) hide();
  };
  overlay.onkeydown = (event) => {
    if (event.key === "Escape") {
      hide();
      return;
    }
    if (event.key !== "Tab") return;

    const focusable = [
      ...drawer.querySelectorAll(
        "button, a[href], input, [tabindex]:not([tabindex='-1'])",
      ),
    ].filter((node) => !node.disabled);
    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return {open, close: hide};
}
