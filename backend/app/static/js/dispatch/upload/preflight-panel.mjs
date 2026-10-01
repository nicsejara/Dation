import {preflightTitle} from "./selectors.mjs";

function line(item, tone) {
  const article = document.createElement("article");
  article.className = `dispatch-preflight-item is-${tone}`;

  const mark = document.createElement("span");
  mark.className = "dispatch-preflight-mark";
  mark.textContent = tone === "error" ? "!" : tone === "warning" ? "!" : "✓";

  const body = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = preflightTitle(item);
  const detail = document.createElement("p");
  detail.textContent = [
    item.order_id ? `Orden ${item.order_id}.` : "",
    item.detail || "",
  ].filter(Boolean).join(" ");
  body.append(title, detail);
  article.append(mark, body);
  return article;
}

export function renderPreflight(root, preflight, orders, fleet) {
  root.replaceChildren();
  root.className = "dispatch-panel dispatch-preflight";

  const title = document.createElement("h2");
  title.textContent = "3 · Revisión conjunta";
  root.append(title);

  if (!orders || !fleet) {
    const p = document.createElement("p");
    p.textContent = "Cargá o elegí ambos archivos para revisar su compatibilidad.";
    root.append(p);
    return;
  }

  if (!preflight) {
    const p = document.createElement("p");
    p.textContent = "Revisando rutas, capacidad, referencias y plazos…";
    root.append(p);
    return;
  }

  if (
    !(preflight.errors || []).length
    && !(preflight.warnings || []).length
    && !(preflight.anomalies || []).length
  ) {
    root.append(
      line(
        {
          detail: "Los archivos son compatibles para iniciar la configuración.",
        },
        "success",
      ),
    );
  } else {
    for (const item of preflight.errors || []) {
      root.append(line(item, "error"));
    }
    for (const item of preflight.warnings || []) {
      root.append(line(item, "warning"));
    }
    for (const item of preflight.anomalies || []) {
      root.append(line(item, "warning"));
    }
  }

  const summary = document.createElement("div");
  summary.className = "dispatch-preflight-summary";
  const ordersText = document.createElement("p");
  ordersText.textContent = (
    `Órdenes: ${orders.label || orders.original_filename} · `
    + `${orders.row_count || 0} registros`
  );
  const fleetText = document.createElement("p");
  fleetText.textContent = (
    `Flota: ${fleet.label || fleet.original_filename}`
    + (fleet.is_default ? " · vigente" : "")
  );
  summary.append(ordersText, fleetText);
  root.append(summary);
}
