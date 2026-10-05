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
    next.stale_predecessor = {
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
