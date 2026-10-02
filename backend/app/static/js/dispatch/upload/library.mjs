import {date, num} from "../shared.mjs";

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

export function createPreviousDrawer() {
  document
    .querySelectorAll(".dispatch-previous-overlay")
    .forEach((node) => node.remove());

  const overlay = el("div", null, "dispatch-previous-overlay");
  overlay.hidden = true;

  const drawer = el("aside", null, "dispatch-previous-drawer");
  drawer.setAttribute("role", "dialog");
  drawer.setAttribute("aria-modal", "true");

  const head = el("div", null, "dispatch-previous-head");
  const title = el("h2", "");
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "Cerrar selector");
  close.textContent = "×";
  head.append(title, close);

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
      if (!query) {
        return true;
      }
      return [
        item.label,
        item.original_filename,
      ].some((value) => String(value || "").toLowerCase().includes(query));
    });

    if (!items.length) {
      list.append(
        el(
          "p",
          "No encontramos archivos guardados para esta búsqueda.",
          "dispatch-library-empty",
        ),
      );
      return;
    }

    items.forEach((item) => {
      const row = el("article", null, "dispatch-previous-row");
      const info = el("div");
      info.append(
        el("strong", item.original_filename || item.label || "Archivo"),
        el(
          "small",
          [
            item.size_bytes != null
              ? `${num(item.size_bytes / 1024, 1)} KB`
              : null,
            item.row_count != null
              ? `${num(item.row_count)} registros`
              : null,
            item.created_at
              ? `cargado ${date(item.created_at.slice(0, 10))}`
              : null,
          ].filter(Boolean).join(" · "),
        ),
      );

      const use = document.createElement("button");
      use.type = "button";
      use.textContent = item.id === selectedId ? "En uso" : "Usar";
      use.disabled = item.id === selectedId;
      use.onclick = async () => {
        await onSelect?.(item);
        hide();
      };
      row.append(info, use);
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
      ? "Usar una carga anterior"
      : "Usar una flota guardada";
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
