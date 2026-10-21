import {resolveNodeDestination} from './decision-target.mjs';
export const NODE_IDS = [
  "logistics_assignment",
  "logistics_scheduling",
  "logistics_final_assignment",
];

export const STATUS = {
  AVAILABLE: "available",
  RUNNING: "running",
  REVIEW: "review",
  APPROVED: "approved",
  LOCKED: "locked",
  NEEDS_DATA: "needs_data",
  ERROR: "error",
  STALE: "stale",
};

export function inputSignature(orders, fleet) {
  if (!orders?.id || !fleet?.id) return null;
  return orders.id + ":" + fleet.id;
}

function nodeState(status) {
  return {
    status,
    run_id: null,
    latest_run_id: null,
    approved_run_id: null,
    run_count: 0,
    latest_execution_status: null,
    approved_at: null,
    error: null,
  };
}

export function createDecisionCase(
  caseId,
  orders,
  fleet,
  now = new Date().toISOString(),
) {
  const signature = inputSignature(orders, fleet);
  if (!signature) return null;

  return {
    schema_version: "decision_case_v2",
    id: caseId,
    domain: "logistics",
    signature,
    created_at: now,
    updated_at: now,
    inputs: {
      orders_dataset_id: orders.id,
      fleet_dataset_id: fleet.id,
    },
    stale_predecessor: null,
    nodes: {
      logistics_assignment: nodeState(STATUS.AVAILABLE),
      logistics_scheduling: nodeState(STATUS.LOCKED),
      logistics_final_assignment: nodeState(STATUS.LOCKED),
    },
  };
}

export function replaceInputs(
  current,
  nextCaseId,
  orders,
  fleet,
  now = new Date().toISOString(),
) {
  const next = createDecisionCase(
    nextCaseId,
    orders,
    fleet,
    now,
  );
  if (!next) return null;

  if (current?.signature && current.signature !== next.signature) {
    // Replacing both files can create intermediate local cases before the map is
    // opened. Keep the last durable predecessor, not an unpersisted intermediate.
    next.stale_predecessor = (!current.persisted && current.stale_predecessor) || {
      id: current.id,
      status: STATUS.STALE,
      signature: current.signature,
      updated_at: current.updated_at || current.created_at,
      approved_run_id: (
        current.nodes?.logistics_assignment?.approved_run_id
        || (
          current.nodes?.logistics_assignment?.status === STATUS.APPROVED
            ? current.nodes.logistics_assignment.run_id
            : null
        )
      ),
    };
  }
  return next;
}

export function getCaseTransitionNotice({decisionCase,predecessor,transitionCaseId}={}){
  const previous=decisionCase?.stale_predecessor;
  const verified=predecessor?.decision_case;
  if(!decisionCase?.id||transitionCaseId!==decisionCase.id||!previous?.id
    ||previous.id===decisionCase.id||verified?.id!==previous.id
    ||!previous.signature||verified.signature!==previous.signature
    ||decisionCase.signature===previous.signature)return null;
  return {caseId:decisionCase.id,predecessorId:previous.id};
}

export function transitionNode(
  current,
  nodeId,
  status,
  patch = {},
  now = new Date().toISOString(),
) {
  if (!current || !NODE_IDS.includes(nodeId)) return current;
  return {
    ...current,
    schema_version: "decision_case_v2",
    updated_at: now,
    nodes: {
      ...current.nodes,
      [nodeId]: {
        ...nodeState(nodeId === "logistics_assignment" ? STATUS.AVAILABLE : STATUS.LOCKED),
        ...current.nodes[nodeId],
        ...patch,
        status,
      },
    },
  };
}

function readinessById(readiness) {
  return Object.fromEntries(
    (readiness?.decisions || []).map((item) => [item.id, item]),
  );
}

const RUNTIME_STATES = [
  STATUS.RUNNING,
  STATUS.REVIEW,
  STATUS.APPROVED,
  STATUS.ERROR,
  STATUS.STALE,
];

export function deriveDecisionNodes(current, readiness) {
  const evidence = readinessById(readiness);
  const nodes = structuredClone(
    current?.nodes || createDecisionCase(
      "preview",
      {id: "orders"},
      {id: "fleet"},
    ).nodes,
  );

  const assignmentEvidence = evidence.logistics_assignment;
  const assignment = nodes.logistics_assignment;

  if (!RUNTIME_STATES.includes(assignment.status)) {
    assignment.status = assignmentEvidence?.data_ready
      ? STATUS.AVAILABLE
      : STATUS.NEEDS_DATA;
  }

  const scheduling = nodes.logistics_scheduling;
  const schedulingEvidence = evidence.logistics_scheduling;
  if (
    assignment.status === STATUS.APPROVED
    && !RUNTIME_STATES.includes(scheduling.status)
  ) {
    scheduling.status = schedulingEvidence?.data_ready
      ? STATUS.AVAILABLE
      : STATUS.NEEDS_DATA;
  } else if (
    assignment.status !== STATUS.APPROVED
    && !RUNTIME_STATES.includes(scheduling.status)
  ) {
    scheduling.status = STATUS.LOCKED;
  }

  const finalAssignment = nodes.logistics_final_assignment;
  const finalEvidence = evidence.logistics_final_assignment;
  if (
    scheduling.status === STATUS.APPROVED
    && !RUNTIME_STATES.includes(finalAssignment.status)
  ) {
    finalAssignment.status = finalEvidence?.data_ready
      ? STATUS.AVAILABLE
      : STATUS.NEEDS_DATA;
  } else if (
    scheduling.status !== STATUS.APPROVED
    && !RUNTIME_STATES.includes(finalAssignment.status)
  ) {
    finalAssignment.status = STATUS.LOCKED;
  }

  return nodes;
}

export function caseRef(current, nodeId = "logistics_assignment") {
  if (!current?.id) return null;
  return {
    case_id: current.id,
    node_id: nodeId,
  };
}


export function nextDecisionId(nodeId){
  const index=NODE_IDS.indexOf(nodeId);
  return index>=0?NODE_IDS[index+1]||null:null;
}

export function continuationState(current,nodeId,runId,readiness,metadata){
  const node=current?.nodes?.[nodeId];
  if(node?.status!==STATUS.APPROVED||String(node.approved_run_id||node.run_id)!==String(runId))return null;
  const next=nextDecisionId(nodeId);
  if(!next)return {state:'finished',message:'No hay otra decisión pendiente en este caso.'};
  const meta=metadata[next];
  if(!meta?.implemented)return {state:'unavailable',nodeId:next,message:'Decisión aprobada. La siguiente etapa todavía no está disponible.'};
  const nextNode=deriveDecisionNodes(current,readiness)[next];
  const target=resolveNodeDestination(next,nextNode);
  if(target)return {state:nextNode.status===STATUS.APPROVED?'finished':nextNode.status,nodeId:next,label:'Continuar con '+(next==='logistics_scheduling'?'Planificación':meta.short)+' →',target};
  const evidence=readinessById(readiness)[next];
  if(!evidence?.data_ready)return {state:'needs_data',nodeId:next,message:'Faltan datos para '+meta.label+': '+(evidence?.missing||[]).map(item=>item.label||item.column).filter(Boolean).join(', ')+'. Podés iniciar una nueva decisión con un Data Pack completo.'};
  if(nextNode?.status!==STATUS.AVAILABLE)return {state:nextNode?.status||'unavailable',nodeId:next,message:meta.label+(nextNode?.status===STATUS.RUNNING?' se está ejecutando.':nextNode?.status===STATUS.REVIEW?' tiene una corrida para revisar.':' requiere una nueva corrida.')+' Abrí su análisis en la barra de decisiones.'};
  return {state:'available',nodeId:next,label:'Continuar con '+(next==='logistics_scheduling'?'Planificación':meta.short)+' →'};
}
