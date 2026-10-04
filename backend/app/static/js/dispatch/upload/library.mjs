import {num} from "../shared.mjs";

function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function domainRows(kind, item) {
  if (item.row_count == null) return "—";
  const label = kind === "orders"
    ? (Number(item.row_count) === 1 ? "orden" : "órdenes")
    : (Number(item.row_count) === 1 ? "vehículo" : "vehículos");
  return `${num(item.row_count)} ${label}`;
}

function dateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("es-AR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function datasetStatus(item) {
  const report = item.profile_json || null;
  const errors = Number(report?.counts?.errors || 0);
  const warnings = Number(report?.counts?.warnings || 0);
  if (errors) return ["Para corregir", "error"];
  if (warnings) return ["Listo con avisos", "warning"];
  if (report?.valid || item.id) return ["Listo", "success"];
  return ["Pendiente", "pending"];
}

export function createPreviousDrawer() {
  document
    .querySelectorAll(".dispatch-previous-overlay")
    .forEach((node) => node.remove());

  const overlay = el("div", null, "dispatch-previous-overlay");
  overlay.hidden = true;

  const drawer = el(
    "aside",
    null,
    "dispatch-previous-drawer dispatch-pro-previous-drawer",
  );
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");

  const head = el("div", null, "dispatch-previous-head");
  const headCopy = el("div");
  const title = el("h2", "");
  headCopy.append(
    el("span", "HISTORIAL DE DATOS", "dispatch-pro-eyebrow"),
    title,
  );
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar selector");
  close.textContent = "×";
  head.append(headCopy, close);

  const search = document.createElement("input");
  search.type = "search";
  search.placeholder = "Buscar por nombre de archivo";
  search.setAttribute("aria-label", search.placeholder);

  const list = el("div", null, "dispatch-previous-list");
  drawer.append(head, search, list);
  overlay.append(drawer);
  document.body.append(overlay);

  let opener = null;
  let current = [];
  let selectedId = null;
  let onSelect = null;
  let kind = "orders";

  function render() {
    list.replaceChildren();
    const query = search.value.trim().toLowerCase();
    const items = current.filter((item) => {
      if (!query) return true;
      return [
        item.label,
        item.original_filename,
      ].some((value) => (
        String(value || "").toLowerCase().includes(query)
      ));
    });

    if (!items.length) {
      list.append(
        el(
          "p",
          kind === "orders"
            ? "Todavía no tenés cargas de Órdenes guardadas."
            : "Todavía no tenés flotas guardadas.",
          "dispatch-library-empty",
        ),
      );
      return;
    }

    const table = el("div", null, "dispatch-pro-history-table");
    const header = el("div", null, "dispatch-pro-history-row is-header");
    ["Archivo", "Fecha", "Datos", "Estado", ""].forEach((value) => (
      header.append(el("span", value))
    ));
    table.append(header);

    items.forEach((item) => {
      const selected = item.id === selectedId;
      const row = el(
        "article",
        null,
        `dispatch-pro-history-row ${selected ? "is-selected" : ""}`,
      );
      const name = el("div", null, "dispatch-pro-history-name");
      name.append(
        el("span", "CSV", "dispatch-pro-library-file-icon"),
        el("strong", item.original_filename || item.label || "Archivo"),
      );
      const [label, tone] = datasetStatus(item);
      const status = el(
        "span",
        label,
        `dispatch-pro-library-state is-${tone}`,
      );

      const use = document.createElement("button");
      use.type = "button";
      use.className = "dispatch-pro-secondary-button";
      use.textContent = selected ? "En uso" : "Usar";
      use.disabled = selected;
      use.onclick = async () => {
        await onSelect?.(item);
        hide();
      };

      row.append(
        name,
        el("span", dateTime(item.created_at)),
        el("span", domainRows(kind, item)),
        status,
        use,
      );
      table.append(row);
    });
    list.append(table);
  }

  function open(options) {
    kind = options.kind;
    current = options.items || [];
    selectedId = options.selected?.id || null;
    onSelect = options.onSelect;
    opener = options.source || null;
    title.textContent = kind === "orders"
      ? "Historial completo de Órdenes"
      : "Historial completo de Flota";
    search.hidden = current.length <= 5;
    search.value = "";
    render();
    overlay.hidden = false;
    document.body.classList.add("dispatch-drawer-open");
    close.focus();
  }

  function hide() {
    overlay.hidden = true;
    document.body.classList.remove("dispatch-drawer-open");
    opener?.focus();
  }

  search.oninput = render;
  close.onclick = hide;
  overlay.onclick = (event) => {
    if (event.target === overlay) hide();
  };
  overlay.onkeydown = (event) => {
    if (event.key === "Escape") hide();
  };

  return {open, close: hide};
}
