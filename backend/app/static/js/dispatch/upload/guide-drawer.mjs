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

export function createGuideDrawer(contracts) {
  document
    .querySelectorAll(".dispatch-guide-overlay")
    .forEach((node) => node.remove());

  const overlay = el("div", null, "dispatch-guide-overlay");
  overlay.hidden = true;

  const drawer = el("aside", null, "dispatch-guide");
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");
  drawer.setAttribute("aria-label", "Revisar columnas");

  const head = el("div", null, "dispatch-guide-head");
  const title = el("h2", "Revisar columnas");
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar");
  close.textContent = "×";
  head.append(title, close);

  const tabs = el("div", null, "dispatch-guide-tabs");
  const content = el("div", null, "dispatch-guide-content");
  drawer.append(head, tabs, content);
  overlay.append(drawer);
  document.body.append(overlay);

  let active = "orders";
  let opener = null;

  function renderContent() {
    content.replaceChildren();
    const contract = contracts.formats[active];
    const wrap = el("div", null, "dispatch-table-wrap");
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    [
      "Columna",
      "Para empezar",
      "Formato",
      "Ejemplo",
      "Se usa en",
      "Para qué sirve",
    ].forEach((value) => headRow.append(el("th", value)));
    thead.append(headRow);

    const tbody = document.createElement("tbody");
    contract.columns.forEach((column) => {
      const row = document.createElement("tr");
      const stageLabels = {
        assignment: "Asignación",
        scheduling: "Planificación",
        final_assignment: "Asignación final",
      };
      [
        column.name,
        column.required ? "Sí" : "Opcional",
        column.rule,
        column.example,
        (column.used_by || []).map((key) => stageLabels[key] || key).join(" · "),
        column.description,
      ].forEach((value) => row.append(el("td", value)));
      tbody.append(row);
    });
    table.append(thead, tbody);
    wrap.append(table);

    const rules = el(
      "p",
      (
        "CSV UTF-8 · hasta 10 MB · separador ; o , · "
        + "fechas AAAA-MM-DD o d/m/AAAA. "
        + "Sólo las columnas marcadas como Sí son necesarias para iniciar Asignación."
      ),
      "dispatch-guide-rules",
    );

    const template = document.createElement("a");
    template.href = `/api/dispatch/templates/${active}`;
    template.download = `${active}.csv`;
    template.className = "dispatch-template-button";
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
        renderTabs();
        renderContent();
      };
      tabs.append(button);
    });
  }

  function open(kind = "orders", source = null) {
    active = kind;
    opener = source;
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
    if (event.target === overlay) {
      hide();
    }
  };
  overlay.onkeydown = (event) => {
    if (event.key === "Escape") {
      hide();
      return;
    }
    if (event.key !== "Tab") {
      return;
    }
    const focusable = [
      ...drawer.querySelectorAll(
        "button, a[href], input, [tabindex]:not([tabindex='-1'])",
      ),
    ].filter((node) => !node.disabled);
    if (!focusable.length) {
      return;
    }
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
