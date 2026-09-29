export const state = {
  activeView: "overview",
  datasets: [],
  runs: [],
  activeDataset: null,
  activeRun: null,
  objective: "min_cost",
  interpreter: null,
  services: {
    supabase: null,
    llm: null,
  },
};

export function setView(view) {
  state.activeView = view;
}

export function setDatasets(items) {
  state.datasets = Array.isArray(items) ? items : [];
}

export function setRuns(items) {
  state.runs = Array.isArray(items) ? items : [];
}

export function setActiveDataset(dataset) {
  state.activeDataset = dataset || null;
}

export function setActiveRun(run) {
  state.activeRun = run || null;
}

export function setObjective(objective) {
  state.objective = objective;
}

export function setInterpreter(status) {
  state.interpreter = status || null;
}
