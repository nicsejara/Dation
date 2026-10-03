import {esc,num,date} from "./shared.mjs";
import {STATUS, deriveDecisionNodes} from "./decision-case.mjs";
import {renderDecisionReadiness} from "./upload/readiness-panel.mjs?v=decision-map-phase1-v1";

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
    ) {
      return {
        label: status === STATUS.RUNNING ? "Ver ejecución →" : "Abrir análisis →",
        action: "open-result",
      };
    }
    if (status === STATUS.ERROR) {
      return {label: "Revisar y reintentar →", action: "configure"};
    }
    if (status === STATUS.NEEDS_DATA) {
      return {label: "Completar datos", action: "data"};
    }
  }

  if (nodeId === "logistics_scheduling") {
    if (status === STATUS.AVAILABLE) {
      return {label: "Configurar planificación →", action: "configure"};
    }
    if (
      status === STATUS.RUNNING
      || status === STATUS.REVIEW
      || status === STATUS.APPROVED
    ) {
      return {
        label: status === STATUS.RUNNING ? "Ver ejecución →" : "Abrir análisis →",
        action: "open-result",
      };
    }
    if (status === STATUS.ERROR) {
      return {label: "Revisar y reintentar →", action: "configure"};
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

function nextActionable(nodes) {
  const order = [
    "logistics_assignment",
    "logistics_scheduling",
    "logistics_final_assignment",
  ];

  for (const nodeId of order) {
    const node = nodes[nodeId];
    const action = actionFor(nodeId, node.status);
    if (
      node.status !== STATUS.APPROVED
      && action?.action
    ) {
      return {
        nodeId,
        node,
        meta: COPY[nodeId],
        action,
      };
    }
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
            + esc(date(String(node.approved_at).slice(0, 10)))
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
  const next = nextActionable(nodes);

  root.className = "dispatch dispatch-decision-map";
  root.innerHTML =
    '<header class="dispatch-map-hero">'
      + '<div>'
        + '<span class="dispatch-kicker">DECISION CASE</span>'
        + '<h1>Flujo de decisiones</h1>'
        + '<p>Continuá el caso desde acá. Podés configurar la próxima decisión disponible o volver a abrir el análisis de una decisión ya aprobada.</p>'
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
    + '<section data-map-readiness></section>'
    + (
      next
        ? '<section class="dispatch-next-step">'
          + '<div class="dispatch-next-step__index">' + esc(next.meta.kicker) + '</div>'
          + '<div><span class="dispatch-kicker">SIGUIENTE PASO</span>'
          + '<h2>' + esc(next.meta.title) + '</h2>'
          + '<p>' + esc(next.meta.question) + '</p></div>'
          + '<button type="button" data-map-action="' + esc(next.action.action) + '" data-map-node="' + esc(next.nodeId) + '">'
            + esc(next.action.label)
          + '</button>'
        + '</section>'
        : '<section class="dispatch-next-step is-complete">'
          + '<div class="dispatch-next-step__index">✓</div>'
          + '<div><span class="dispatch-kicker">CASO AL DÍA</span><h2>No hay otra decisión ejecutable en esta versión</h2>'
          + '<p>Podés volver a abrir cualquiera de las decisiones aprobadas desde las tarjetas del flujo o desde el panel de análisis.</p></div>'
        + '</section>'
    )
    + '<div class="dispatch-map-chain-head"><div><span class="dispatch-kicker">JERARQUÍA DE DECISIONES</span><h2>Una decisión habilita la siguiente</h2></div><p>El output aprobado de cada nivel pasa a ser evidencia de entrada del nivel siguiente. Las decisiones aprobadas quedan disponibles para volver a abrir su dashboard.</p></div>'
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
      + '<div><span class="dispatch-kicker">CÓMO AVANZA EL CASO</span><h2>Aprobar una decisión habilita la siguiente</h2></div>'
      + '<p>El flujo conserva las decisiones ya validadas y sólo habilita el siguiente motor cuando están disponibles sus datos y su dependencia anterior fue aprobada.</p>'
    + '</section>';

  const readinessRoot = root.querySelector("[data-map-readiness]");
  if (readinessRoot) {
    renderDecisionReadiness(readinessRoot, readiness);
  }

  root.querySelectorAll("[data-map-action]").forEach((button) => {
    button.onclick = () => {
      const action = button.dataset.mapAction;
      const nodeId = button.dataset.mapNode;
      if (action === "configure") onConfigure?.(nodeId);
      if (action === "open-result") onOpenResult?.(nodeId);
      if (action === "data") onData?.();
    };
  });
}
