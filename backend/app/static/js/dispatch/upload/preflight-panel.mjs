import {chart, csv, download, num} from "../shared.mjs";

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

function icon(severity) {
  return {
    error: "⛔",
    warning: "⚠",
    info: "ℹ",
    success: "✓",
  }[severity] || "ℹ";
}

function itemsDetails(finding) {
  if (!finding.items?.length) {
    return null;
  }
  const details = document.createElement("details");
  details.className = "dispatch-finding-details";
  const summary = document.createElement("summary");
  summary.textContent = "Ver detalle";
  details.append(summary);

  const wrap = el("div", null, "dispatch-table-wrap");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Orden / fecha", "Detalle"].forEach(
    (value) => headRow.append(el("th", value)),
  );
  head.append(headRow);
  const body = document.createElement("tbody");
  finding.items.forEach((item) => {
    const row = document.createElement("tr");
    row.append(
      el("td", item.order_id || item.date || "—"),
      el(
        "td",
        [
          item.route,
          item.detail,
        ].filter(Boolean).join(" · ")
        || (
          item.kg != null
            ? `${num(item.kg / 1000, 1)} t`
            : "—"
        ),
      ),
    );
    body.append(row);
  });
  table.append(head, body);
  wrap.append(table);
  details.append(wrap);

  if (finding.id === "late_orders") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "dispatch-text-action";
    button.textContent = "Descargar lista";
    button.onclick = () => {
      const rows = [
        ["orden", "ruta", "detalle"],
        ...finding.items.map((item) => [
          item.order_id,
          item.route,
          item.detail,
        ]),
      ];
      download(
        "ordenes_con_demora.csv",
        csv(rows),
        "text/csv;charset=utf-8",
      );
    };
    details.append(button);
  }
  return details;
}

function capacityChart(root, capacity) {
  if (!capacity?.days?.length || !capacity.own_capacity_kg_per_day) {
    return;
  }
  const section = el("div", null, "dispatch-capacity-check");
  section.append(el("h3", "Demanda vs. capacidad propia por día"));
  const chartRoot = el("div", null, "dispatch-chart dispatch-capacity-chart");
  section.append(chartRoot);

  chart(chartRoot, {
    tooltip: {
      trigger: "axis",
      renderMode: "richText",
      valueFormatter: (value) => `${num(value / 1000, 1)} t`,
    },
    grid: {
      left: 58,
      right: 18,
      top: 30,
      bottom: 54,
    },
    xAxis: {
      type: "category",
      data: capacity.days.map((item) => item.date.slice(5)),
      axisLabel: {rotate: 35},
    },
    yAxis: {
      type: "value",
      axisLabel: {
        formatter: (value) => `${num(value / 1000)} t`,
      },
    },
    series: [
      {
        name: "Demanda",
        type: "bar",
        data: capacity.days.map((item) => ({
          value: item.kg,
          itemStyle: {
            color: item.over ? "#c48722" : "#5c63d8",
          },
        })),
      },
      {
        name: "Capacidad propia",
        type: "line",
        symbol: "none",
        lineStyle: {
          type: "dashed",
          width: 2,
        },
        data: capacity.days.map(
          () => capacity.own_capacity_kg_per_day,
        ),
      },
    ],
  });

  section.append(
    el(
      "p",
      (
        "Referencia simple: capacidad × camiones disponibles por día. "
        + "No incluye el viaje de vuelta ni los plazos."
      ),
      "dispatch-chart-note",
    ),
  );

  const tableDetails = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Ver como tabla";
  tableDetails.append(summary);
  const wrap = el("div", null, "dispatch-table-wrap");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Fecha", "Órdenes", "Demanda", "Capacidad", "Relación"].forEach(
    (value) => headRow.append(el("th", value)),
  );
  head.append(headRow);
  const body = document.createElement("tbody");
  capacity.days.forEach((item) => {
    const row = document.createElement("tr");
    [
      item.date,
      num(item.orders),
      `${num(item.kg / 1000, 1)} t`,
      `${num(capacity.own_capacity_kg_per_day / 1000, 1)} t`,
      item.ratio == null ? "—" : `${num(item.ratio, 1)}×`,
    ].forEach((value) => row.append(el("td", value)));
    body.append(row);
  });
  table.append(head, body);
  wrap.append(table);
  tableDetails.append(wrap);
  section.append(tableDetails);
  root.append(section);
}

export function renderPreflight(root, preflight, orders, fleet) {
  root.replaceChildren();
  root.className = "dispatch-panel dispatch-preflight";
  root.id = "dispatch-upload-review";
  root.append(el("h2", "3 · Revisión conjunta"));

  if (!orders || !fleet) {
    root.append(
      el(
        "p",
        "Cargá o elegí ambos archivos para revisar su compatibilidad.",
      ),
    );
    return;
  }

  if (!preflight) {
    root.append(
      el(
        "p",
        "Revisando rutas, capacidad, referencias y plazos…",
      ),
    );
    return;
  }

  const findings = preflight.findings || [];
  const head = el("div", null, "dispatch-preflight-head");
  const errors = findings.filter((item) => item.severity === "error").length;
  const warnings = findings.filter(
    (item) => item.severity === "warning",
  ).length;
  head.append(
    el(
      "span",
      `${errors} errores · ${warnings} avisos`,
      errors ? "is-error" : warnings ? "is-warning" : "is-success",
    ),
  );
  root.append(head);

  const list = el("div", null, "dispatch-findings");
  if (!findings.length) {
    const item = el("article", null, "dispatch-finding is-success");
    item.append(
      el("span", "✓", "dispatch-finding-icon"),
      el("strong", "Los archivos son compatibles"),
    );
    list.append(item);
  }

  findings.forEach((finding) => {
    const item = el(
      "article",
      null,
      `dispatch-finding is-${finding.severity}`,
    );
    const copy = el("div");
    copy.append(el("strong", finding.title));
    if (finding.consequence) {
      copy.append(el("p", finding.consequence));
    }
    const details = itemsDetails(finding);
    if (details) {
      copy.append(details);
    }
    item.append(
      el("span", icon(finding.severity), "dispatch-finding-icon"),
      copy,
    );
    list.append(item);
  });
  root.append(list);
  capacityChart(root, preflight.capacity_check);
}
