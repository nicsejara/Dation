import {esc,num,date} from "./shared.mjs";
import {STATUS, deriveDecisionNodes} from "./decision-case.mjs";

const LABELS = {
  [STATUS.AVAILABLE]: "Disponible",
  [STATUS.RUNNING]: "Procesando",
  [STATUS.REVIEW]: "En revisión",
  [STATUS.APPROVED]: "Aprobada",
  [STATUS.LOCKED]: "Bloqueada",
  [STATUS.NEEDS_DATA]: "Requiere datos",
  [STATUS.ERROR]: "Error",
  [STATUS.STALE]: "Desactualizada",
};

const COPY = {
  logistics_assignment: {
    kicker: "DECISIÓN 01",
    title: "Asignación de carga",
    question: "¿Cómo conviene construir los viajes y distribuir la carga?",
    output: "Viajes propuestos + distribución de carga",
  },
  logistics_scheduling: {
    kicker: "DECISIÓN 02",
    title: "Planificación",
    question: "¿Cuándo conviene ejecutar los viajes ya definidos?",
    output: "Calendario operativo + secuencia",
  },
  logistics_final_assignment: {
    kicker: "DECISIÓN 03",
    title: "Asignación final",
    question: "¿Qué camión y patente ejecuta cada viaje programado?",
    output: "Asignación física lista para ejecución",
  },
};

function missingText(decision) {
  const missing = decision?.missing || [];
  if (!missing.length) return null;
  return missing.map((item) => item.label).join(" · ");
}

function capabilityText(decision) {
  return (decision?.capabilities || [])
    .filter((item) => item.available)
    .map((item) => item.label);
}

function actionFor(nodeId, status) {
  if (nodeId === "logistics_assignment") {
    if (status === STATUS.AVAILABLE) {
      return {label: "Configurar decisión →", action: "configure"};
    }
    if (
      status === STATUS.RUNNING
      || status === STATUS.REVIEW
      || status === STATUS.APPROVED
      || status === STATUS.ERROR
    ) {
      return {label: "Ver decisión →", action: "open-result"};
    }
    if (status === STATUS.NEEDS_DATA) {
      return {label: "Completar datos", action: "data"};
    }
  }

  if (status === STATUS.NEEDS_DATA) {
    return {label: "Completar Data Pack", action: "data"};
  }

  if (status === STATUS.AVAILABLE) {
    return {label: "Motor en próxima fase", action: null};
  }

  return null;
}

function nodeCard(
  nodeId,
  node,
  decision,
) {
  const meta = COPY[nodeId];
  const action = actionFor(nodeId, node.status);
  const missing = missingText(decision);
  const capabilities = capabilityText(decision);

  return (
    '<article class="dispatch-map-node is-' + esc(node.status) + '">'
      + '<div class="dispatch-map-node__top">'
        + '<span class="dispatch-map-node__index">' + esc(meta.kicker) + '</span>'
        + '<span class="dispatch-map-state is-' + esc(node.status) + '">'
          + esc(LABELS[node.status] || node.status)
        + '</span>'
      + '</div>'
      + '<h2>' + esc(meta.title) + '</h2>'
      + '<p class="dispatch-map-node__question">' + esc(meta.question) + '</p>'
      + '<div class="dispatch-map-node__output">'
        + '<small>Resultado</small>'
        + '<strong>' + esc(meta.output) + '</strong>'
      + '</div>'
      + (
        capabilities.length
          ? '<div class="dispatch-map-node__chips">'
            + capabilities.map(
              (value) => '<span>✓ ' + esc(value) + '</span>',
            ).join("")
            + '</div>'
          : ''
      )
      + (
        missing
          ? '<details class="dispatch-map-node__missing">'
            + '<summary>Datos que faltan</summary>'
            + '<p>' + esc(missing) + '</p>'
            + '</details>'
          : ''
      )
      + (
        node.run_id
          ? '<small class="dispatch-map-node__run">Corrida '
            + esc(String(node.run_id).slice(0, 8)) + '…</small>'
          : ''
      )
      + (
        node.approved_at
          ? '<small class="dispatch-map-node__approved">Aprobada '
            + esc(date(node.approved_at))
            + '</small>'
          : ''
      )
      + (
        node.error
          ? '<p class="dispatch-map-node__error">' + esc(node.error) + '</p>'
          : ''
      )
      + (
        action
          ? '<button type="button" class="dispatch-map-node__action"'
            + (action.action ? ' data-map-action="' + esc(action.action) + '"' : ' disabled')
            + ' data-map-node="' + esc(nodeId) + '">'
            + esc(action.label)
            + '</button>'
          : ''
      )
    + '</article>'
  );
}

export function renderDecisionMap(
  root,
  {
    decisionCase,
    readiness,
    orders,
    fleet,
    onConfigure,
    onOpenResult,
    onData,
  },
) {
  const nodes = deriveDecisionNodes(decisionCase, readiness);
  const readinessMap = Object.fromEntries(
    (readiness?.decisions || []).map((item) => [item.id, item]),
  );
  const approved = Object.values(nodes).filter(
    (node) => node.status === STATUS.APPROVED,
  ).length;

  root.className = "dispatch dispatch-decision-map";
  root.innerHTML =
    '<header class="dispatch-map-hero">'
      + '<div>'
        + '<span class="dispatch-kicker">DECISION CASE</span>'
        + '<h1>Mapa de decisiones</h1>'
        + '<p>La información se transforma en decisiones encadenadas. Cada nivel se habilita cuando tiene datos suficientes y la decisión anterior fue validada.</p>'
      + '</div>'
      + '<div class="dispatch-map-case">'
        + '<small>Caso</small>'
        + '<strong>' + esc(String(decisionCase?.id || "—").slice(0, 8)) + '…</strong>'
        + '<span>' + num(approved) + ' de 3 aprobadas</span>'
      + '</div>'
    + '</header>'
    + (
      decisionCase?.stale_predecessor
        ? '<section class="dispatch-map-stale">'
          + '<span aria-hidden="true">↻</span>'
          + '<div><strong>Los datos cambiaron</strong>'
          + '<p>El caso anterior quedó marcado como desactualizado. Esta cadena usa las versiones de Orders y Fleet seleccionadas ahora.</p></div>'
        + '</section>'
        : ''
    )
    + '<section class="dispatch-map-evidence">'
      + '<div><small>Orders</small><strong>'
        + esc(orders?.original_filename || "—")
        + '</strong><span>' + num(orders?.row_count || 0) + ' registros</span></div>'
      + '<div><small>Fleet</small><strong>'
        + esc(fleet?.label || fleet?.original_filename || "—")
        + '</strong><span>' + num(fleet?.row_count || 0) + ' vehículos</span></div>'
      + '<button type="button" data-map-action="data">Cambiar datos</button>'
    + '</section>'
    + '<section class="dispatch-map-chain" aria-label="Cadena de decisiones">'
      + nodeCard(
          "logistics_assignment",
          nodes.logistics_assignment,
          readinessMap.logistics_assignment,
        )
      + '<div class="dispatch-map-connector" aria-hidden="true"><span></span><strong>01 → 02</strong></div>'
      + nodeCard(
          "logistics_scheduling",
          nodes.logistics_scheduling,
          readinessMap.logistics_scheduling,
        )
      + '<div class="dispatch-map-connector" aria-hidden="true"><span></span><strong>02 → 03</strong></div>'
      + nodeCard(
          "logistics_final_assignment",
          nodes.logistics_final_assignment,
          readinessMap.logistics_final_assignment,
        )
    + '</section>'
    + '<section class="dispatch-panel dispatch-map-principle">'
      + '<div><span class="dispatch-kicker">LÓGICA DE DESBLOQUEO</span><h2>Datos suficientes + decisión anterior aprobada</h2></div>'
      + '<p>Completar columnas futuras no ejecuta automáticamente una decisión. Dation separa disponibilidad de datos, ejecución del motor y validación humana.</p>'
    + '</section>';

  root.querySelectorAll("[data-map-action]").forEach((button) => {
    button.onclick = () => {
      const action = button.dataset.mapAction;
      if (action === "configure") onConfigure?.();
      if (action === "open-result") onOpenResult?.();
      if (action === "data") onData?.();
    };
  });
}
