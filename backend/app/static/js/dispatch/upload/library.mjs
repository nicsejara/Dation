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

function tons(kg) {
  return `${num((kg || 0) / 1000, 1)} t`;
}

function metaFor(kind, item) {
  const profile = item.profile_json?.profile || {};
  if (kind === "orders") {
    return [
      `${num(item.row_count)} órdenes`,
      profile.total_weight_kg != null
        ? tons(profile.total_weight_kg)
        : null,
      profile.routes != null
        ? `${num(profile.routes)} rutas`
        : null,
      item.created_at
        ? `cargado ${date(item.created_at.slice(0, 10))}`
        : null,
    ].filter(Boolean).join(" · ");
  }
  return [
    profile.types != null
      ? `${num(profile.types)} tipos`
      : null,
    profile.own_units_per_day != null
      ? `${num(profile.own_units_per_day)} propios/día`
      : null,
    item.is_default ? "Vigente" : null,
  ].filter(Boolean).join(" · ");
}

export function renderLibrary(
  root,
  {
    kind,
    items,
    selected,
    query = "",
    onSelect,
    onArchive,
    onSearch,
    onMakeDefault,
    onUndo,
  },
) {
  root.replaceChildren();

  const details = document.createElement("details");
  details.className = "dispatch-library-details";
  const summary = document.createElement("summary");
  summary.textContent = kind === "orders"
    ? `Usar una carga anterior (${items?.length || 0})`
    : `Cambiar flota o subir una nueva versión (${items?.length || 0})`;
  details.append(summary);

  if ((items?.length || 0) > 5) {
    const search = document.createElement("input");
    search.type = "search";
    search.value = query;
    search.placeholder = "Buscar por nombre…";
    search.setAttribute("aria-label", search.placeholder);
    let timer = null;
    search.oninput = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(
        () => onSearch(search.value.trim()),
        250,
      );
    };
    details.append(search);
  }

  if (!items?.length) {
    details.append(
      el(
        "p",
        kind === "orders"
          ? "Todavía no hay órdenes guardadas."
          : "Todavía no hay versiones de flota guardadas.",
        "dispatch-library-empty",
      ),
    );
    root.append(details);
    return;
  }

  const list = el("div", null, "dispatch-library-list");
  for (const item of items) {
    const row = el("article", null, "dispatch-library-row");
    if (selected?.id === item.id) {
      row.classList.add("is-selected");
    }

    const info = el("div");
    info.append(
      el("strong", item.label || item.original_filename),
      el("small", metaFor(kind, item)),
      el("small", item.original_filename, "dispatch-muted-file"),
    );

    const actions = el("div", null, "dispatch-library-actions");
    const use = document.createElement("button");
    use.type = "button";
    use.textContent = selected?.id === item.id ? "En uso" : "Usar";
    use.disabled = selected?.id === item.id;
    use.onclick = () => onSelect(item);
    actions.append(use);

    if (kind === "fleet" && !item.is_default) {
      const makeDefault = document.createElement("button");
      makeDefault.type = "button";
      makeDefault.className = "dispatch-text-action";
      makeDefault.textContent = "Marcar vigente";
      makeDefault.onclick = () => onMakeDefault(item);
      actions.append(makeDefault);
    }

    if (!(kind === "fleet" && item.is_default)) {
      const menu = document.createElement("details");
      menu.className = "dispatch-row-menu";
      const menuSummary = document.createElement("summary");
      menuSummary.setAttribute("aria-label", "Más acciones");
      menuSummary.textContent = "⋯";
      menu.append(menuSummary);
      const archive = document.createElement("button");
      archive.type = "button";
      archive.textContent = "Archivar";
      archive.onclick = async () => {
        await onArchive(item);
        menu.open = false;
        const undo = el(
          "div",
          "Carga archivada.",
          "dispatch-undo",
        );
        const undoButton = document.createElement("button");
        undoButton.type = "button";
        undoButton.textContent = "Deshacer";
        undoButton.onclick = () => onUndo(item);
        undo.append(undoButton);
        root.prepend(undo);
        window.setTimeout(() => undo.remove(), 8000);
      };
      menu.append(archive);
      actions.append(menu);
    }

    row.append(info, actions);
    list.append(row);
  }
  details.append(list);
  root.append(details);
}
