function node(tag, value, className = "") {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  element.textContent = value;
  return element;
}

export function renderSystemBanner(root, status) {
  root.replaceChildren();
  if (!status || status.available) {
    root.hidden = true;
    return;
  }

  root.hidden = false;
  root.className = "dispatch-system-banner";
  const head = document.createElement("div");
  head.append(
    node("strong", "Activación pendiente"),
    node(
      "p",
      status.message
        || "Podés validar archivos, pero todavía no se pueden guardar.",
    ),
  );
  root.append(head);

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Ver diagnóstico del sistema";
  details.append(summary);

  const list = document.createElement("div");
  list.className = "dispatch-system-checks";
  for (const check of status.checks || []) {
    const item = document.createElement("article");
    const icon = check.ok === true ? "✓" : check.ok === false ? "!" : "i";
    item.append(
      node("span", icon, "dispatch-system-check-icon"),
      node("strong", check.label || "Chequeo"),
      node("p", check.detail || "Sin detalle"),
    );
    if (check.ok !== true && check.fix) {
      item.append(node("small", check.fix));
    }
    list.append(item);
  }
  details.append(list);
  root.append(details);
}
