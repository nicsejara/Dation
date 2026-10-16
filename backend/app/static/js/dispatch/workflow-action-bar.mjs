let sequence = 0;

function node(tag, text, className = "") {
  const element = document.createElement(tag);
  element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

function icon(name) {
  const paths = {
    orders: '<path d="M9 4h6v4H9zM9 6H5v15h14V6h-4M9 12h6M9 16h6"/>',
    fleet: '<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    success: '<path d="m5 12 4 4L19 6"/>',
    warning: '<path d="M12 3 2 21h20ZM12 9v5M12 17v1"/>',
    error: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16v1"/>',
    pending: '<circle cx="12" cy="12" r="8"/>',
    validating: '<path d="M21 12a9 9 0 1 1-3-6.7"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  };
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = paths[name] || paths.pending;
  return svg;
}

/** One stable action node; callers retain validation and continuation ownership. */
export function createWorkflowActionBar({label, onContinue, onProblem, onSelect, variant = "data"}) {
  const bar = node("section", null, "d-workflow-action-bar");
  bar.setAttribute("aria-label", `${label}: acciones`);
  const meta = node("div", null, "d-workflow-action-bar__meta");
  const message = node("span", "Completá tu Data Pack.");
  message.id = `workflow-action-message-${++sequence}`;
  message.setAttribute("role", "status");
  meta.append(node("strong", label), message);
  const files = node(variant === "configuration" ? "nav" : "div", null, "d-workflow-action-bar__items");
  if (variant === "configuration") files.setAttribute("aria-label", "Resumen de configuración");
  files.addEventListener("focusin", event => {
    const item = event.target.closest(".d-workflow-action-bar__chip");
    if (!item) return;
    const control = item.getBoundingClientRect(), viewport = files.getBoundingClientRect();
    if (control.right > viewport.right - 6) files.scrollLeft += control.right - viewport.right + 6;
    else if (control.left < viewport.left + 6) files.scrollLeft -= viewport.left + 6 - control.left;
  });
  const button = node("button", null, "d-button d-button--workflow");
  button.type = "button";
  button.disabled = true;
  button.setAttribute("aria-describedby", message.id);
  let action = null;
  button.addEventListener("click", () => { if (!button.disabled) action?.(); });
  const actions = node("div", null, "d-workflow-action-bar__actions");
  actions.append(files, button);
  bar.append(meta, actions);

  function update(result, {items = [], missingCount = 0, busy = false, storageAvailable = true} = {}) {
    const state = busy ? "validating" : result.enabled ? "ready" : result.kind;
    bar.dataset.state = state;
    actions.dataset.contextCount = String(items.length);
    actions.style.setProperty("--workflow-context-count", String(Math.max(1, items.length)));
    files.hidden = items.length === 0;
    button.setAttribute("aria-busy", String(busy));
    files.replaceChildren(...items.map(({key, label: title, tone, value, target}) => {
      if (variant === "configuration") {
        const item = node("button", null, "d-workflow-action-bar__item d-workflow-action-bar__chip");
        item.type = "button";
        item.dataset.summaryTarget = target;
        item.addEventListener("click", () => onSelect?.(target));
        item.append(node("small", title), node("strong", value));
        return item;
      }
      const item = node("span", null, `d-workflow-action-bar__item is-${tone}`);
      const status = {success:"listo", warning:"con avisos", error:"con errores", validating:"validando", pending:"pendiente"}[tone];
      item.append(icon(key), node("span", `${title}: ${status}`), icon(tone));
      return item;
    }));
    message.textContent = result.message;
    action = null;
    button.disabled = true;
    button.className = `d-button d-button--workflow d-button--secondary ${variant === "data" ? "dispatch-pro-next-button" : ""}`;
    let title;
    if (variant === "configuration") {
      title = "Revisar y ejecutar";
      button.disabled = false;
      button.classList.replace("d-button--secondary", "d-button--primary");
    } else if (busy) title = "Validando archivos…";
    else if (!storageAvailable) title = "Servicio no disponible";
    else if (result.enabled) {
      title = "Seleccioná tu decisión";
      button.classList.replace("d-button--secondary", "d-button--primary");
      button.disabled = false;
      action = onContinue;
    } else if (result.kind === "error") {
      title = "Corregir problema";
      button.disabled = false;
      action = onProblem;
    } else if (missingCount) title = `Falta${missingCount === 1 ? "" : "n"} ${missingCount} archivo${missingCount === 1 ? "" : "s"}`;
    else title = "Comprobando archivos…";
    button.replaceChildren(node("span", title), icon(variant === "configuration" || result.enabled ? "arrow" : state === "error" ? "error" : busy ? "validating" : "pending"));
  }
  update({kind:"pending", enabled:false, message:"Completá tu Data Pack."}, {missingCount:2});
  return {bar, button, update};
}
