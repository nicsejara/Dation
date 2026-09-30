export const state = {
  activeView: "inicio",
  activeDda: "logistics",
  datasets: [],
  runs: [],
  activeDataset: null,
  datasetProfile: null,
  activeRun: null,
  decisionMode: "preset",
  objective: "min_cost",
  weights: {
    cost: 0.7,
    trips: 0.3,
  },
  interpreter: null,
  explanation: null,
  messages: [],
  traceTab: "datasets",
  services: {
    supabase: null,
    llm: null,
  },
};

export function setView(view) {
  state.activeView = view;
}

export function setDatasets(items) {
  state.datasets = (
    Array.isArray(items)
      ? items
      : []
  );
}

export function setRuns(items) {
  state.runs = (
    Array.isArray(items)
      ? items
      : []
  );
}

export function setActiveDataset(
  dataset
) {
  state.activeDataset = (
    dataset || null
  );
}

export function setDatasetProfile(
  profile
) {
  state.datasetProfile = (
    profile || null
  );
}

export function setActiveRun(run) {
  state.activeRun = run || null;
}

export function setDecisionPreset(
  objective
) {
  state.decisionMode = "preset";
  state.objective = objective;

  if (objective === "min_trips") {
    state.weights = {
      cost: 0,
      trips: 1,
    };
  } else {
    state.objective = "min_cost";
    state.weights = {
      cost: 1,
      trips: 0,
    };
  }
}

export function setCustomMode() {
  state.decisionMode = "custom";
  state.objective = "custom";

  if (
    state.weights.cost === 1
    || state.weights.trips === 1
  ) {
    state.weights = {
      cost: 0.7,
      trips: 0.3,
    };
  }
}

export function setCostWeight(
  percent
) {
  const bounded = Math.max(
    0,
    Math.min(
      100,
      Math.round(Number(percent))
    )
  );

  state.weights = {
    cost: bounded / 100,
    trips: (100 - bounded) / 100,
  };
}

export function setInterpreter(
  status
) {
  state.interpreter = (
    status || null
  );
}

export function setExplanation(
  explanation
) {
  state.explanation = (
    explanation || null
  );
}

export function setMessages(
  messages
) {
  state.messages = (
    Array.isArray(messages)
      ? messages
      : []
  );
}

export function setTraceTab(tab) {
  state.traceTab = tab;
}

export function decisionConfiguration() {
  if (
    state.decisionMode === "custom"
  ) {
    return {
      mode: "custom",
      objective: "custom",
      weights: {
        cost: state.weights.cost,
        trips: state.weights.trips,
      },
    };
  }

  return {
    mode: "preset",
    objective: state.objective,
    weights: {
      cost: state.weights.cost,
      trips: state.weights.trips,
    },
  };
}

export function normalizeRunConfiguration(
  run
) {
  const raw = (
    run?.configuration_json || {}
  );
  const resultConfig = (
    run?.result_json?.configuration
    || {}
  );

  const mode = (
    raw.mode
    || resultConfig.mode
  );
  const objective = (
    raw.objective
    || resultConfig.objective
    || run?.result_json?.objective
    || "min_cost"
  );
  const weights = (
    raw.weights
    || resultConfig.weights
  );

  if (
    mode === "custom"
    || objective === "custom"
  ) {
    return {
      mode: "custom",
      objective: "custom",
      weights: {
        cost: Number(
          weights?.cost ?? 0.5
        ),
        trips: Number(
          weights?.trips ?? 0.5
        ),
      },
    };
  }

  if (
    objective === "min_trips"
  ) {
    return {
      mode: "preset",
      objective: "min_trips",
      weights: {
        cost: 0,
        trips: 1,
      },
    };
  }

  return {
    mode: "preset",
    objective: "min_cost",
    weights: {
      cost: 1,
      trips: 0,
    },
  };
}

export function restoreRunConfiguration(
  run
) {
  const config = (
    normalizeRunConfiguration(run)
  );

  state.decisionMode = config.mode;
  state.objective = config.objective;
  state.weights = config.weights;

  return config;
}
