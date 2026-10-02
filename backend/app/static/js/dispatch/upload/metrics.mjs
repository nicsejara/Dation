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

function dateRange(profile) {
  if (!profile?.date_from || !profile?.date_to) {
    return "—";
  }
  const start = date(profile.date_from);
  const end = date(profile.date_to);
  return `${start.replace(/ de 2026$/, "")} – ${end}`;
}

function metric(value, label, detail) {
  const card = el("article", null, "dispatch-understood-metric");
  card.append(
    el("strong", value),
    el("span", label),
  );
  if (detail) {
    card.append(el("small", detail));
  }
  return card;
}

function detectedChips(root, report) {
  const detected = report?.detected;
  if (!detected) {
    return;
  }
  const chips = el("div", null, "dispatch-detected");
  [
    `Separador ${detected.delimiter || "—"}`,
    detected.encoding,
    detected.date_format
      ? `Fechas ${detected.date_format}`
      : null,
    `${detected.columns || report.columns} columnas`,
  ].filter(Boolean).forEach((value) => {
    chips.append(el("span", value));
  });
  root.append(chips);
}

function preview(root, report) {
  if (!report?.preview?.rows?.length) {
    return;
  }
  const details = document.createElement("details");
  details.className = "dispatch-preview";
  const summary = document.createElement("summary");
  summary.textContent = (
    `Vista previa (${report.preview.shown} de ${report.rows} filas)`
  );
  details.append(summary);

  const wrap = el("div", null, "dispatch-table-wrap");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  report.preview.columns.forEach((column) => {
    headRow.append(el("th", `✓ ${column}`));
  });
  head.append(headRow);

  const body = document.createElement("tbody");
  report.preview.rows.forEach((row) => {
    const tr = document.createElement("tr");
    report.preview.columns.forEach((column) => {
      tr.append(el("td", row[column] ?? ""));
    });
    body.append(tr);
  });
  table.append(head, body);
  wrap.append(table);
  details.append(wrap);
  root.append(details);
}

export function renderUnderstood(root, kind, report) {
  root.replaceChildren();
  if (!report?.valid || !report.profile) {
    return;
  }

  const section = el("section", null, "dispatch-understood");
  section.append(el("h3", "Qué entendimos de tu archivo"));

  if (kind === "orders") {
    const profile = report.profile;
    const metrics = el("div", null, "dispatch-understood-grid");
    const mix = profile.priority_mix || {};
    metrics.append(
      metric(
        num(report.rows),
        "Órdenes",
        `${num(profile.total_units)} unidades`,
      ),
      metric(
        tons(profile.total_weight_kg),
        "Peso total",
        `La mayor: ${tons(profile.max_order_kg)}`,
      ),
      metric(
        num(profile.routes),
        "Rutas",
        `${num(profile.origins)} orígenes → ${num(profile.destinations)} destinos`,
      ),
      metric(
        dateRange(profile),
        "Período",
        (
          `${profile.daily?.length || 0} `
          + `${profile.daily?.length === 1 ? "día" : "días"}`
        ),
      ),
    );

    const priority = metric(
      `${num(mix.High)} / ${num(mix.Normal)} / ${num(mix.Low)}`,
      "Prioridad",
      "Alta / Normal / Baja",
    );
    priority.classList.add("dispatch-understood-metric--wide");
    metrics.append(priority);

    const days = profile.delivery_days || {};
    metrics.append(
      metric(
        `${num(days.min)}–${num(days.max)} días`,
        "Plazos",
        "Entrega máxima informada",
      ),
    );
    section.append(metrics);
    detectedChips(section, report);
    preview(section, report);
  } else {
    const profile = report.profile;
    section.append(
      el(
        "p",
        (
          `${num(profile.types)} tipos · `
          + `${num(profile.own_units_per_day)} camiones propios por día · `
          + `${tons(profile.own_capacity_kg_per_day)} de capacidad propia diaria · `
          + (
            profile.has_third_party
              ? "con tercerizados sin límite"
              : "sin tercerizados"
          )
        ),
        "dispatch-fleet-summary",
      ),
    );

    const wrap = el("div", null, "dispatch-table-wrap");
    const table = document.createElement("table");
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["Camión", "Propiedad", "Capacidad", "Por día"].forEach(
      (value) => headRow.append(el("th", value)),
    );
    head.append(headRow);
    const body = document.createElement("tbody");

    for (const vehicle of profile.fleet || []) {
      const tr = document.createElement("tr");
      [
        vehicle.vehicle_type,
        vehicle.ownership === "own" ? "Propio" : "Tercerizado",
        tons(vehicle.capacity_kg),
        vehicle.units_available == null
          ? "Sin límite"
          : num(vehicle.units_available),
      ].forEach((value) => tr.append(el("td", value)));
      body.append(tr);
    }
    table.append(head, body);
    wrap.append(table);
    section.append(wrap);

    const detail = document.createElement("details");
    detail.className = "dispatch-fleet-detail";
    const summary = document.createElement("summary");
    summary.textContent = "Ver detalle de costos y velocidad";
    detail.append(summary);
    const detailWrap = el("div", null, "dispatch-table-wrap");
    const detailTable = document.createElement("table");
    const detailHead = document.createElement("thead");
    const detailHeadRow = document.createElement("tr");
    ["Camión", "Costo/km", "Costo fijo", "Velocidad"].forEach(
      (value) => detailHeadRow.append(el("th", value)),
    );
    detailHead.append(detailHeadRow);
    const detailBody = document.createElement("tbody");
    for (const vehicle of profile.fleet || []) {
      const tr = document.createElement("tr");
      [
        vehicle.vehicle_type,
        num(vehicle.cost_per_km, 2),
        num(vehicle.fixed_trip_cost, 2),
        `${num(vehicle.avg_speed_kmh)} km/h`,
      ].forEach((value) => tr.append(el("td", value)));
      detailBody.append(tr);
    }
    detailTable.append(detailHead, detailBody);
    detailWrap.append(detailTable);
    detail.append(detailWrap);
    section.append(detail);

    detectedChips(section, report);
  }

  root.append(section);
}
