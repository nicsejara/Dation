import {esc} from "./shared.mjs";
import {scopeFor} from "./lifecycle.mjs";

export const WORKFLOW_ACTION_CLASS = "d-button d-button--workflow";
let sequence = 0;

const paths = {
  orders: '<path d="M9 4h6v4H9zM9 6H5v15h14V6h-4M9 12h6M9 16h6"/>',
  attributes: '<path d="M5 4h14v17H5zM8 8h8M8 12h8M8 16h5"/>',
  owner: '<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
  fleet: '<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  success: '<path d="m5 12 4 4L19 6"/>',
  warning: '<path d="M12 3 2 21h20ZM12 9v5M12 17v1"/>',
  error: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16v1"/>',
  pending: '<circle cx="12" cy="12" r="8"/>',
  validating: '<path d="M21 12a9 9 0 1 1-3-6.7"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
};

function iconMarkup(name) {
  return '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    +(paths[name]||paths.pending)+'</svg>';
}

/** Shared label and trailing decorative arrow; action owners retain their hooks. */
export function workflowActionLabel(label) {
  return '<span>'+esc(String(label??"").replace(/\s*→\s*$/u,""))+'</span>'+iconMarkup("arrow");
}

function node(tag, text, className = "") {
  const element = document.createElement(tag);
  element.className = className;
  if (text != null) element.textContent = text;
  return element;
}

function icon(name) {
  const template = document.createElement("template");
  template.innerHTML = iconMarkup(name);
  return template.content.firstElementChild;
}

/** Layout only: one floating command surface, owned by the current view scope.
 * z-index 35 sits below menus (80), native dialogs and assistant overlays. */
export function bindWorkflowActionBarLayout(root,bar){
  const scope=scopeFor(root),viewport=window.visualViewport,frame=root.closest('.main');
  const properties=['--workflow-bar-space','--workflow-bar-left','--workflow-bar-width','--workflow-keyboard-inset'];
  function exposeFocus(){
    const field=document.activeElement;
    if(!root.contains(field)||bar.contains(field)||!field?.getBoundingClientRect)return;
    const r=field.getBoundingClientRect(),b=bar.getBoundingClientRect();
    if(!r.width||!b.width)return;
    let scroll=field.parentElement;
    while(scroll&&!(scroll.scrollHeight>scroll.clientHeight&&/(auto|scroll)/.test(getComputedStyle(scroll).overflowY)))scroll=scroll.parentElement;
    scroll ||= document.scrollingElement;
    const header=[...document.querySelectorAll('.topbar,.dda-workspace-nav-shell')].reduce((bottom,e)=>{
      const style=getComputedStyle(e),rect=e.getBoundingClientRect();
      return ['fixed','sticky'].includes(style.position)&&rect.top>=0?Math.max(bottom,rect.bottom):bottom;
    },0)+12;
    const bottom=Math.min(b.top-12,(frame?.getBoundingClientRect().bottom??b.top)-12);
    if(r.bottom>bottom)scroll.scrollTop+=r.bottom-bottom;
    else if(r.top<header)scroll.scrollTop-=header-r.top;
  }
  function measure(){
    const r=root.getBoundingClientRect();if(!r.width)return;
    const inset=Math.max(0,innerHeight-(viewport?.height||innerHeight)-(viewport?.offsetTop||0));
    const space=Math.ceil(bar.getBoundingClientRect().height)+40;
    frame?.classList.add('has-workflow-commands');
    frame?.classList.toggle('has-compact-workflow-commands',(viewport?.height||innerHeight)<540);
    bar.dataset.compact=String((viewport?.height||innerHeight)<540);
    frame?.style.setProperty('--workflow-command-space',space+'px');
    frame?.style.setProperty('--workflow-viewport-height',(viewport?.height||innerHeight)+'px');
    root.style.setProperty('--workflow-bar-left',r.left+'px');
    root.style.setProperty('--workflow-bar-width',r.width+'px');
    root.style.setProperty('--workflow-keyboard-inset',inset+'px');
    root.style.setProperty('--workflow-bar-space',space+'px');
    exposeFocus();
  }
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(measure):null;
  observer?.observe(bar);observer?.observe(root);
  root.addEventListener('focusin',exposeFocus);window.addEventListener('resize',measure);
  viewport?.addEventListener('resize',measure);viewport?.addEventListener('scroll',measure);
  measure();
  const dispose=()=>{observer?.disconnect();root.removeEventListener('focusin',exposeFocus);window.removeEventListener('resize',measure);viewport?.removeEventListener('resize',measure);viewport?.removeEventListener('scroll',measure);properties.forEach(p=>root.style.removeProperty(p));frame?.classList.remove('has-workflow-commands','has-compact-workflow-commands');frame?.style.removeProperty('--workflow-command-space');frame?.style.removeProperty('--workflow-viewport-height');};
  scope?.own(dispose);return dispose;
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
  const button = node("button", null, WORKFLOW_ACTION_CLASS);
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
    button.className = `${WORKFLOW_ACTION_CLASS} d-button--secondary ${variant === "data" ? "dispatch-pro-next-button" : ""}`;
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
