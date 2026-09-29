import {
  askRun,
  explainRun,
  getDatasets,
  getInterpreterStatus,
  getRun,
  getRuns,
  getSupabaseStatus,
  getWorkspaceSummary,
  runDecision,
  uploadDataset,
} from "./api.js";

import {
  setActiveDataset,
  setActiveRun,
  setDatasets,
  setInterpreter,
  setObjective,
  setRuns,
  setView,
  state,
} from "./state.js";

import {
  $,
  $$,
  activateView,
  appendChatMessage,
  clearRunPresentation,
  hideInlineStatus,
  renderActiveDataset,
  renderDatasetsTable,
  renderExplanation,
  renderInterpreterMeta,
  renderObjective,
  renderOverviewRecentRuns,
  renderOverviewStats,
  renderRun,
  renderRunsTable,
  renderSystemStatus,
  renderWorkspaceDatasetList,
  showInlineStatus,
  toast,
  updateWorkflowFromState,
} from "./ui.js";

let booting = true;

function datasetById(id) {
  return state.datasets.find((item) => item.id === id) || null;
}

function navigate(view) {
  setView(view);
  activateView(view);
}

function resetChatThread() {
  const thread = $("#chat-thread");
  thread.innerHTML = `
    <div class="assistant-message">
      <div class="message-avatar">D</div>
      <div>
        <strong>Dation Interpreter</strong>
        <p>Esta conversación está anclada a la corrida activa. Podés preguntar por drivers, trade-offs, supuestos y diferencias entre escenarios.</p>
      </div>
    </div>
  `;
}

function selectDataset(dataset, { navigateToWorkspace = false } = {}) {
  setActiveDataset(dataset);
  setActiveRun(null);
  renderActiveDataset(dataset);
  renderWorkspaceDatasetList(state.datasets);
  clearRunPresentation();
  resetChatThread();
  renderInterpreterMeta(state.interpreter);

  if (navigateToWorkspace) {
    navigate("workspace");
    window.setTimeout(() => {
      $("#stage-decision").scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }, 180);
  }
}

async function refreshDatasets() {
  const response = await getDatasets(50);
  setDatasets(response.items || []);
  renderWorkspaceDatasetList(state.datasets);
  renderDatasetsTable(state.datasets);

  if (state.activeDataset) {
    const fresh = datasetById(state.activeDataset.id);
    if (fresh) {
      setActiveDataset(fresh);
      renderActiveDataset(fresh);
    }
  }
}

async function refreshRuns() {
  const response = await getRuns(60);
  setRuns(response.items || []);
  renderRunsTable(state.runs, state.datasets);
  renderOverviewRecentRuns(state.runs, state.datasets);
}

async function refreshSummary() {
  const summary = await getWorkspaceSummary();
  renderOverviewStats(summary);
}

async function refreshInterpreter() {
  try {
    const interpreter = await getInterpreterStatus();
    setInterpreter(interpreter);
    renderInterpreterMeta(interpreter);
    return interpreter;
  } catch (error) {
    setInterpreter({
      configured: false,
      provider: "—",
      model: "—",
      knowledge_version: "—",
    });
    renderInterpreterMeta(state.interpreter);
    return state.interpreter;
  }
}

async function refreshSystemStatus() {
  let supabaseOk = false;

  try {
    const status = await getSupabaseStatus();
    supabaseOk = Boolean(status?.ok);
  } catch {
    supabaseOk = false;
  }

  state.services.supabase = supabaseOk;
  state.services.llm = Boolean(state.interpreter?.configured);
  renderSystemStatus(supabaseOk, state.interpreter);
}

async function refreshWorkspaceData({ notify = false } = {}) {
  try {
    await refreshDatasets();
    await refreshRuns();
    await refreshSummary();

    if (notify) toast("Workspace data refreshed.");
  } catch (error) {
    toast(`Could not refresh workspace: ${error.message}`, "error");
  }
}

async function bootstrap() {
  renderActiveDataset(null);
  renderObjective(state.objective);
  updateWorkflowFromState();

  try {
    await Promise.all([
      refreshInterpreter(),
      refreshDatasets(),
    ]);

    await Promise.all([
      refreshRuns(),
      refreshSummary(),
    ]);

    await refreshSystemStatus();
  } catch (error) {
    toast(`Workspace initialization error: ${error.message}`, "error");
  } finally {
    booting = false;
  }
}

function bindNavigation() {
  document.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-view], [data-view-target]");

    if (viewButton) {
      const view =
        viewButton.dataset.view ||
        viewButton.dataset.viewTarget;

      if (view) navigate(view);
    }

    const scrollButton = event.target.closest("[data-scroll-target]");

    if (scrollButton) {
      const target = document.getElementById(scrollButton.dataset.scrollTarget);
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    }
  });

  $("#overview-start").addEventListener("click", () => navigate("workspace"));
  $("#overview-open-asset").addEventListener("click", () => navigate("workspace"));
}

function bindObjectiveSelector() {
  $("#objective-selector").addEventListener("click", (event) => {
    const card = event.target.closest("[data-objective]");
    if (!card) return;

    setObjective(card.dataset.objective);
    renderObjective(state.objective);
  });
}

function bindDatasetActions() {
  document.addEventListener("click", async (event) => {
    const useButton = event.target.closest("[data-use-dataset]");

    if (useButton) {
      const dataset = datasetById(useButton.dataset.useDataset);
      if (!dataset) {
        toast("Dataset could not be found in the current workspace.", "error");
        return;
      }

      selectDataset(dataset, { navigateToWorkspace: true });
      toast(`Using ${dataset.original_filename} as source evidence.`);
      return;
    }

    const runButton = event.target.closest("[data-open-run]");

    if (runButton) {
      const button = runButton;
      button.disabled = true;
      button.textContent = "Opening…";

      try {
        const run = await getRun(button.dataset.openRun);
        const dataset = datasetById(run.dataset_id);

        if (dataset) {
          setActiveDataset(dataset);
          renderActiveDataset(dataset);
          renderWorkspaceDatasetList(state.datasets);
        }

        const objective =
          run.configuration_json?.objective || "min_cost";
        setObjective(objective);
        renderObjective(objective);

        setActiveRun(run);
        renderRun(run);
        renderInterpreterMeta(state.interpreter);
        resetChatThread();

        navigate("workspace");

        window.setTimeout(() => {
          $("#stage-results").scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }, 180);
      } catch (error) {
        toast(`Could not open run: ${error.message}`, "error");
      } finally {
        button.disabled = false;
        button.textContent = "Open";
      }
    }
  });
}

function bindUpload() {
  const input = $("#dataset-file");
  const browseButton = $("#browse-file");
  const dropzone = $("#upload-dropzone");
  const progress = $("#upload-progress");

  browseButton.addEventListener("click", () => input.click());

  async function handleFile(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".csv")) {
      showInlineStatus(progress, "Only CSV files are accepted.", "error");
      return;
    }

    browseButton.disabled = true;
    browseButton.textContent = "Validating…";
    showInlineStatus(
      progress,
      "Validating schema and storing immutable source data…"
    );

    try {
      const result = await uploadDataset(file);
      const datasetId = result.duplicate
        ? result.existing_dataset.id
        : result.dataset.id;

      await refreshDatasets();

      const dataset = datasetById(datasetId);

      if (!dataset) {
        throw new Error("Dataset was stored but could not be reloaded.");
      }

      selectDataset(dataset);

      showInlineStatus(
        progress,
        result.duplicate
          ? "Dataset already existed. The stored version was reused."
          : `Dataset validated: ${result.validation.rows} rows, ${result.validation.columns} columns.`,
        "success"
      );

      await refreshSummary();
      toast(
        result.duplicate
          ? "Existing dataset selected."
          : "Dataset validated and stored successfully."
      );
    } catch (error) {
      showInlineStatus(progress, error.message, "error");
    } finally {
      browseButton.disabled = false;
      browseButton.textContent = "Select CSV file";
      input.value = "";
    }
  }

  input.addEventListener("change", () => handleFile(input.files?.[0]));

  ["dragenter", "dragover"].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    });
  });

  ["dragleave", "drop"].forEach((type) => {
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragging");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    handleFile(event.dataTransfer?.files?.[0]);
  });
}

function bindDecisionExecution() {
  const button = $("#run-decision");
  const progress = $("#run-progress");

  button.addEventListener("click", async () => {
    if (!state.activeDataset) return;

    button.disabled = true;
    button.innerHTML = "Running engine <span>…</span>";

    showInlineStatus(
      progress,
      "Cloud Run is retrieving the CSV, calculating all scenarios and persisting the DecisionResult…"
    );

    try {
      const run = await runDecision(
        state.activeDataset.id,
        state.objective
      );

      setActiveRun(run);
      renderRun(run);
      renderInterpreterMeta(state.interpreter);
      resetChatThread();

      showInlineStatus(
        progress,
        `Decision completed and persisted · Run ${run.id.slice(0, 8)}… · ${run.duration_ms} ms`,
        "success"
      );

      await Promise.all([
        refreshRuns(),
        refreshSummary(),
        refreshDatasets(),
      ]);

      window.setTimeout(() => {
        $("#stage-results").scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 120);
    } catch (error) {
      showInlineStatus(progress, error.message, "error");
    } finally {
      button.disabled = !state.activeDataset;
      button.innerHTML = 'Run decision <span>→</span>';
    }
  });
}

function bindInterpreter() {
  const explainButton = $("#generate-explanation");
  const progress = $("#ai-progress");
  const askButton = $("#ask-decision");
  const questionInput = $("#decision-question");

  explainButton.addEventListener("click", async () => {
    if (!state.activeRun) return;

    explainButton.disabled = true;
    explainButton.textContent = "Building insight…";

    showInlineStatus(
      progress,
      "Combining deterministic decision evidence with the versioned Logistics knowledge base…"
    );

    try {
      const explanation = await explainRun(state.activeRun.id);
      renderExplanation(explanation);

      showInlineStatus(
        progress,
        `Interpretation persisted · ${explanation.provider} · ${explanation.model}`,
        "success"
      );
    } catch (error) {
      showInlineStatus(progress, error.message, "error");
    } finally {
      explainButton.disabled = false;
      explainButton.textContent = "Generate executive insight";
    }
  });

  $("#prompt-chips").addEventListener("click", (event) => {
    const chip = event.target.closest("button");
    if (!chip) return;

    questionInput.value = chip.textContent.trim();
    questionInput.focus();
  });

  async function sendQuestion() {
    const question = questionInput.value.trim();

    if (!state.activeRun || !question) return;

    appendChatMessage("user", question);
    questionInput.value = "";
    askButton.disabled = true;
    askButton.textContent = "…";

    const pendingId = `pending-${Date.now()}`;
    const thread = $("#chat-thread");
    thread.insertAdjacentHTML(
      "beforeend",
      `
        <div class="assistant-message" id="${pendingId}">
          <div class="message-avatar">D</div>
          <div>
            <strong>Dation Interpreter</strong>
            <p>Reading the decision evidence…</p>
          </div>
        </div>
      `
    );
    thread.scrollTop = thread.scrollHeight;

    try {
      const answer = await askRun(state.activeRun.id, question);
      document.getElementById(pendingId)?.remove();
      appendChatMessage("assistant", answer.answer);
    } catch (error) {
      document.getElementById(pendingId)?.remove();
      appendChatMessage(
        "assistant",
        `I could not answer this question: ${error.message}`
      );
    } finally {
      askButton.disabled = false;
      askButton.textContent = "↑";
      questionInput.focus();
    }
  }

  askButton.addEventListener("click", sendQuestion);

  questionInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      sendQuestion();
    }
  });
}

function bindRefreshActions() {
  $("#workspace-refresh").addEventListener("click", () =>
    refreshWorkspaceData({ notify: true })
  );

  $("#datasets-refresh").addEventListener("click", () =>
    refreshWorkspaceData({ notify: true })
  );

  $("#runs-refresh").addEventListener("click", () =>
    refreshWorkspaceData({ notify: true })
  );
}

function bindGlobalErrors() {
  window.addEventListener("unhandledrejection", (event) => {
    if (!booting) {
      toast(
        event.reason?.message || "Unexpected workspace error.",
        "error"
      );
    }
  });
}

bindNavigation();
bindObjectiveSelector();
bindDatasetActions();
bindUpload();
bindDecisionExecution();
bindInterpreter();
bindRefreshActions();
bindGlobalErrors();

bootstrap();
