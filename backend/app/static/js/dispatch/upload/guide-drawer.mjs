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
  drawer.setAttribute("aria-label", "Guía de formato");

  const head = el("div", null, "dispatch-guide-head");
  head.append(el("h2", "Guía de formato"));
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar guía");
  close.textContent = "×";
  head.append(close);

  const tabs = el("div", null, "dispatch-guide-tabs");
  const content = el("div", null, "dispatch-guide-content");
  drawer.append(head, tabs, content);
  overlay.append(drawer);
  document.body.append(overlay);

  let active = "orders";
  let opener = null;

  function renderFormat(kind) {
    content.replaceChildren();
    const contract = contracts.formats[kind];
    content.append(
      el(
        "p",
        kind === "orders"
          ? "Las órdenes cambian en cada corrida."
          : "La flota se carga una vez y se reutiliza.",
      ),
    );

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "dispatch-text-action";
    copy.textContent = "Copiar encabezados";
    copy.onclick = async () => {
      const headers = contract.columns.map((column) => column.name).join(";");
      await navigator.clipboard.writeText(headers);
      copy.textContent = "Encabezados copiados";
      window.setTimeout(() => {
        copy.textContent = "Copiar encabezados";
      }, 1500);
    };
    content.append(copy);

    const wrap = el("div", null, "dispatch-table-wrap");
    const table = document.createElement("table");
    const headRow = document.createElement("tr");
    ["Columna", "Obligatoria", "Formato", "Ejemplo", "Para qué sirve"].forEach(
      (value) => headRow.append(el("th", value)),
    );
    const thead = document.createElement("thead");
    thead.append(headRow);
    const tbody = document.createElement("tbody");
    contract.columns.forEach((column) => {
      const row = document.createElement("tr");
      [
        column.name,
        column.required ? "Sí" : "No",
        column.rule,
        column.example,
        column.description,
      ].forEach((value) => row.append(el("td", value)));
      tbody.append(row);
    });
    table.append(thead, tbody);
    wrap.append(table);
    content.append(wrap);

    content.append(
      el("h3", "Reglas rápidas"),
      el(
        "p",
        "CSV UTF-8 · separador ; o , · hasta 10 MB · fechas AAAA-MM-DD o d/m/AAAA.",
      ),
      el("h3", "Glosario"),
      el(
        "p",
        (
          "Propio: camión con disponibilidad diaria limitada. "
          + "Tercerizado: capacidad externa. Plazo: días máximos para entregar."
        ),
      ),
    );

    const actions = el("div", null, "dispatch-upload-links");
    const template = document.createElement("a");
    template.href = `/api/dispatch/templates/${kind}`;
    template.textContent = "↓ Descargar plantilla";
    const example = document.createElement("a");
    example.href = `/api/dispatch/examples/${kind}`;
    example.textContent = "↗ Descargar ejemplo";
    actions.append(template, example);
    content.append(actions);
  }

  function renderErrors() {
    content.replaceChildren();
    const items = [
      [
        "Formato anterior",
        "Aparecen órdenes y flota en el mismo CSV.",
        "Separá la información con las dos plantillas nuevas.",
      ],
      [
        "Fecha inexistente",
        "Una fecha como 31/02/2026 no existe.",
        "Usá AAAA-MM-DD o d/m/AAAA con día primero.",
      ],
      [
        "Distancia inconsistente",
        "La misma ruta aparece con dos distancias.",
        "Elegí una distancia única para esa ruta.",
      ],
      [
        "ID repetido",
        "Dos filas usan el mismo identificador.",
        "Asigná un ID único a cada registro.",
      ],
      [
        "Disponibilidad vacía",
        "Un camión propio no informa units_available.",
        "Indicá cuántos pueden salir por día.",
      ],
    ];
    items.forEach(([title, symptom, fix]) => {
      const article = el("article", null, "dispatch-guide-error");
      article.append(
        el("strong", title),
        el("p", symptom),
        el("small", `Cómo resolverlo: ${fix}`),
      );
      content.append(article);
    });
  }

  function renderTabs() {
    tabs.replaceChildren();
    [
      ["orders", "Órdenes"],
      ["fleet", "Flota"],
      ["errors", "Errores frecuentes"],
    ].forEach(([key, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.setAttribute("aria-pressed", String(active === key));
      button.onclick = () => {
        active = key;
        renderTabs();
        if (key === "errors") {
          renderErrors();
        } else {
          renderFormat(key);
        }
      };
      tabs.append(button);
    });
  }

  function hide() {
    overlay.hidden = true;
    document.body.classList.remove("dispatch-guide-open");
    opener?.focus();
  }

  function open(kind = "orders", source = null) {
    active = kind;
    opener = source;
    renderTabs();
    if (kind === "errors") {
      renderErrors();
    } else {
      renderFormat(kind);
    }
    overlay.hidden = false;
    document.body.classList.add("dispatch-guide-open");
    close.focus();
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
        "button, a[href], input, summary, [tabindex]:not([tabindex='-1'])",
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
