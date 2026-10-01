import {date, num} from "../shared.mjs";

function empty(message) {
  const p = document.createElement("p");
  p.className = "dispatch-library-empty";
  p.textContent = message;
  return p;
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
  },
) {
  root.replaceChildren();

  const heading = document.createElement("div");
  heading.className = "dispatch-library-heading";
  const title = document.createElement("strong");
  title.textContent = (
    kind === "orders"
      ? "Cargas anteriores"
      : "Versiones de flota"
  );
  heading.append(title);
  root.append(heading);

  const search = document.createElement("input");
  search.type = "search";
  search.value = query;
  search.placeholder = (
    kind === "orders"
      ? "Buscar cargas anteriores…"
      : "Buscar versiones de flota…"
  );
  search.setAttribute("aria-label", search.placeholder);
  let timer = null;
  search.oninput = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(
      () => onSearch(search.value.trim()),
      250,
    );
  };
  root.append(search);

  if (!items?.length) {
    root.append(
      empty(
        query
          ? "No encontramos cargas que coincidan con la búsqueda."
          : (
            kind === "orders"
              ? "Todavía no hay órdenes guardadas."
              : "Todavía no hay versiones de flota guardadas."
          ),
      ),
    );
    return;
  }

  const list = document.createElement("div");
  list.className = "dispatch-library-list";

  for (const item of items) {
    const row = document.createElement("article");
    row.className = "dispatch-library-row";
    if (selected?.id === item.id) {
      row.classList.add("is-selected");
    }

    const info = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = item.label || item.original_filename;
    const meta = document.createElement("small");
    meta.textContent = [
      item.created_at ? date(item.created_at.slice(0, 10)) : null,
      item.row_count != null ? `${num(item.row_count)} registros` : null,
      item.is_default ? "Vigente" : null,
    ].filter(Boolean).join(" · ");
    info.append(name, meta);

    const actions = document.createElement("div");
    actions.className = "dispatch-library-actions";

    const use = document.createElement("button");
    use.type = "button";
    use.textContent = selected?.id === item.id ? "En uso" : "Usar";
    use.disabled = selected?.id === item.id;
    use.onclick = () => onSelect(item);
    actions.append(use);

    if (kind === "fleet" && !item.is_default) {
      const makeDefault = document.createElement("button");
      makeDefault.type = "button";
      makeDefault.textContent = "Marcar vigente";
      makeDefault.onclick = () => onMakeDefault(item);
      actions.append(makeDefault);
    }

    if (!(kind === "fleet" && item.is_default)) {
      const archive = document.createElement("button");
      archive.type = "button";
      archive.textContent = "Archivar";
      archive.onclick = () => onArchive(item);
      actions.append(archive);
    }

    row.append(info, actions);
    list.append(row);
  }

  root.append(list);
}
