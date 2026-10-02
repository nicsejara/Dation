import {date, num} from "../shared.mjs";
import {continueState, stepTone} from "./selectors.mjs";

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

function statusIcon(tone) {
  return {
    success: "✓",
    warning: "⚠",
    error: "⛔",
    pending: "○",
  }[tone] || "○";
}

function row(label, tone, detail) {
  const item = el("div", null, `dispatch-summary-row is-${tone}`);
  item.append(
    el("span", statusIcon(tone), "dispatch-summary-icon"),
    el("strong", label),
    el("small", detail),
  );
  return item;
}

export function createSummaryPanel(onNext) {
  const panel = el("aside", null, "dispatch-summary-panel");
  panel.append(el("h2", "Tu carga"));
  const rows = el("div", null, "dispatch-summary-rows");
  const next = document.createElement("button");
  next.type = "button";
  next.className = "dispatch-summary-next";
  next.textContent = "Configurar decisión →";
  next.onclick = onNext;
  const reason = el("p", "", "dispatch-summary-reason");
  const support = el(
    "small",
    "En el próximo paso elegís cuánto pesan costo, viajes y tiempo.",
    "dispatch-summary-support",
  );
  panel.append(rows, next, reason, support);

  function update({
    storageAvailable,
    orders,
    fleet,
    reports,
    preflight,
  }) {
    rows.replaceChildren();

    const ordersTone = stepTone({
      dataset: orders,
      report: reports.orders,
      kind: "orders",
    });
    const ordersProfile = orders?.profile_json?.profile
      || reports.orders?.profile;
    rows.append(
      row(
        "Órdenes",
        ordersTone,
        orders
          ? (
            `${num(orders.row_count)} · `
            + (
              ordersProfile?.date_from
              && ordersProfile?.date_to
                ? `${date(ordersProfile.date_from)} – ${date(ordersProfile.date_to)}`
                : "guardadas"
            )
          )
          : "Pendientes",
      ),
    );

    const fleetTone = stepTone({
      dataset: fleet,
      report: reports.fleet,
      kind: "fleet",
    });
    const fleetProfile = fleet?.profile_json?.profile
      || reports.fleet?.profile;
    rows.append(
      row(
        "Flota",
        fleetTone,
        fleet
          ? (
            `${fleet.label || fleet.original_filename} · `
            + `${num(fleetProfile?.types || fleet.row_count)} tipos`
          )
          : "Pendiente",
      ),
    );

    const reviewTone = stepTone({
      preflight,
      kind: "review",
    });
    const warnings = (preflight?.findings || []).filter(
      (item) => item.severity === "warning",
    ).length;
    rows.append(
      row(
        "Revisión",
        reviewTone,
        preflight
          ? (
            warnings
              ? `${warnings} avisos a revisar`
              : "Sin bloqueos"
          )
          : "Pendiente",
      ),
    );

    const state = continueState({
      storageAvailable,
      orders,
      fleet,
      reports,
      preflight,
    });
    next.disabled = !state.enabled;
    reason.textContent = state.message;
    return state;
  }

  return {panel, update, button: next};
}
