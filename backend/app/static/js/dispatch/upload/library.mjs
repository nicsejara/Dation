import {date, num} from "../shared.mjs";

function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function domainRows(kind, item) {
  if (item.row_count == null) return null;
  const label = kind === "orders"
    ? (Number(item.row_count) === 1 ? "orden" : "órdenes")
    : (Number(item.row_count) === 1 ? "vehículo" : "vehículos");
  return `${num(item.row_count)} ${label}`;
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

    items.forEach((item) => {
      const row = el(
        "article",
        null,
        `dispatch-previous-row ${item.id === selectedId ? "is-selected" : ""}`,
      );
      const icon = el("span", "CSV", "dispatch-pro-library-file-icon");
      const info = el("div");
      info.append(
        el("strong", item.original_filename || item.label || "Archivo"),
        el(
          "small",
          [
            domainRows(kind, item),
            item.created_at
              ? `cargado ${date(item.created_at.slice(0, 10))}`
              : null,
          ].filter(Boolean).join(" · "),
        ),
      );

      const use = document.createElement("button");
      use.type = "button";
      use.className = "dispatch-pro-secondary-button";
      use.textContent = item.id === selectedId ? "En uso" : "Usar";
      use.disabled = item.id === selectedId;
      use.onclick = async () => {
        await onSelect?.(item);
        hide();
      };
      row.append(icon, info, use);
      list.append(row);
    });
  }

  function open(options) {
    kind = options.kind;
    current = options.items || [];
    selectedId = options.selected?.id || null;
    onSelect = options.onSelect;
    opener = options.source || null;
    title.textContent = kind === "orders"
      ? "Tus cargas anteriores"
      : "Tus flotas guardadas";
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
