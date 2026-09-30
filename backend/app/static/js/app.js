import {
  askRun,
  explainRun,
  getDatasetProfile,
  getDatasets,
  getInterpreterStatus,
  getRun,
  getRunInterpretation,
  getRuns,
  getSupabaseStatus,
  getWorkspaceSummary,
} from "./api.js";

import {
  restoreRunConfiguration,
  setActiveDataset,
  setActiveRun,
  setDatasetProfile,
  setDatasets,
  setExplanation,
  setInterpreter,
  setMessages,
  setRuns,
  setTraceTab,
  setView,
  state,
} from "./state.js";

import {
  $,
  $$,
  activateTraceTab,
  activateView,
  appendChatMessage,
  buildDecisionMarkdown,
  renderActiveDataset,
  renderDashboard,
  renderDatasetProfile,
  renderDatasetsTable,
  renderExplanation,
  renderHomeSummary,
  renderInterpreterMeta,
  renderRunsTable,
  renderSystemStatus,
  renderTechnicalEvidence,
  renderWorkspaceDatasets,
  resetChat,
  showInlineStatus,
  toast,
} from "./ui.js";


let booting = true;


function datasetById(id) {
  return (
    state.datasets.find(
      (item) => item.id === id
    )
    || null
  );
}


function navigate(
  view,
  stage = null,
) {
  setView(view);

  if (
    typeof window.dationNavigate
    === "function"
  ) {
    window.dationNavigate(
      view,
      stage,
    );
    return;
  }

  activateView(view);
}


function openTraceability(
  tab = "datasets"
) {
  setTraceTab(tab);
  activateTraceTab(tab);
  navigate("traceability");
}


async function refreshDatasets() {
  const response = (
    await getDatasets(80)
  );

  setDatasets(
    response.items || []
  );

  renderWorkspaceDatasets(
    state.datasets
  );

  renderDatasetsTable(
    state.datasets
  );

  if (state.activeDataset) {
    const fresh = datasetById(
      state.activeDataset.id
    );

    if (fresh) {
      setActiveDataset(fresh);
      renderActiveDataset(fresh);
    }
  }
}


async function refreshRuns() {
  const response = (
    await getRuns(100)
  );

  setRuns(
    response.items || []
  );

  renderRunsTable(
    state.runs,
    state.datasets,
  );
}


async function refreshSummary() {
  const summary = (
    await getWorkspaceSummary()
  );

  renderHomeSummary(
    summary,
    state.runs,
  );
}


async function refreshInterpreter() {
  try {
    const interpreter = (
      await getInterpreterStatus()
    );

    setInterpreter(
      interpreter
    );

    renderInterpreterMeta(
      interpreter
    );

    return interpreter;
  } catch {
    const unavailable = {
      configured: false,
      provider: "—",
      model: "—",
      knowledge_version: "—",
    };

    setInterpreter(
      unavailable
    );

    renderInterpreterMeta(
      unavailable
    );

    return unavailable;
  }
}


async function refreshSystemStatus() {
  let supabaseOk = false;

  try {
    const status = (
      await getSupabaseStatus()
    );

    supabaseOk = Boolean(
      status?.ok
    );
  } catch {
    supabaseOk = false;
  }

  state.services.supabase = (
    supabaseOk
  );

  state.services.llm = Boolean(
    state.interpreter?.configured
  );

  renderSystemStatus(
    supabaseOk,
    state.interpreter,
  );
}


async function refreshWorkspaceData(
  {
    notify = false,
  } = {},
) {
  try {
    await refreshDatasets();
    await refreshRuns();
    await refreshSummary();

    if (notify) {
      toast(
        "Información del workspace actualizada."
      );
    }
  } catch (error) {
    toast(
      "No se pudo actualizar el workspace: "
      + error.message,
      "error",
    );
  }
}


function clearDecisionState() {
  setActiveRun(null);
  setExplanation(null);
  setMessages([]);

  renderExplanation(null);
  renderTechnicalEvidence(null);
  resetChat([]);
  $("#download-json").disabled = true;
  $("#export-decision").disabled = true;
}


async function restoreHistoricalRun(
  runId
) {
  try {
    toast(
      "Reconstruyendo la decisión histórica…"
    );

    const run = (
      await getRun(runId)
    );

    const dataset = (
      datasetById(
        run.dataset_id
      )
    );

    if (!dataset) {
      throw new Error(
        "No se encontró el dataset asociado a esta corrida."
      );
    }

    setActiveDataset(
      dataset
    );

    restoreRunConfiguration(
      run
    );

    renderActiveDataset(
      dataset
    );

    renderWorkspaceDatasets(
      state.datasets
    );

    const [
      profile,
      interpretation,
    ] = await Promise.all([
      getDatasetProfile(
        dataset.id
      ),
      getRunInterpretation(
        run.id
      ).catch(
        () => ({
          explanation: null,
          messages: [],
        })
      ),
    ]);

    setDatasetProfile(
      profile
    );

    renderDatasetProfile(
      profile
    );

    setActiveRun(
      run
    );

    const savedExplanation = (
      interpretation?.explanation
        ?.response_json
      || null
    );

    setExplanation(
      savedExplanation
    );

    setMessages(
      interpretation?.messages
      || []
    );

    renderDashboard(
      run,
      profile,
    );

    renderExplanation(
      savedExplanation
    );

    resetChat(
      state.messages
    );

    renderInterpreterMeta(
      state.interpreter
    );

    navigate(
      "decision-dashboard"
    );

    toast(
      "Decisión histórica reconstruida."
    );
  } catch (error) {
    toast(
      "No se pudo abrir la decisión: "
      + error.message,
      "error",
    );
  }
}


async function bootstrap() {
  renderActiveDataset(null);
  renderDatasetProfile(null);
  renderTechnicalEvidence(null);
  resetChat([]);

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
    toast(
      "No se pudo inicializar el workspace: "
      + error.message,
      "error",
    );
  } finally {
    booting = false;
  }
}


function bindNavigation() {
  document.addEventListener(
    "click",
    (event) => {
      const viewButton = (
        event.target.closest(
          "[data-view], [data-view-target]"
        )
      );

      if (viewButton) {
        const view = (
          viewButton.dataset.view
          || viewButton.dataset.viewTarget
        );

        if (view) {
          navigate(view);
        }

        const traceTarget = (
          viewButton.dataset.traceTarget
        );

        if (traceTarget) {
          setTraceTab(
            traceTarget
          );
          activateTraceTab(
            traceTarget
          );
        }
      }
    }
  );

  const homeLogistics = $("#home-open-logistics");

  if (homeLogistics) {
    homeLogistics.addEventListener(
      "click",
      (event) => {
        event.preventDefault();
        event.stopPropagation();
        navigate(
          "logistics-overview",
          "dda",
        );
      }
    );
  }

  $("#back-to-config")
    .addEventListener(
      "click",
      () => navigate(
        "logistics-config"
      )
    );

  $$(".trace-tab")
    .forEach(
      (button) => {
        button.addEventListener(
          "click",
          () => {
            const tab = (
              button.dataset.traceTab
            );

            setTraceTab(tab);
            activateTraceTab(tab);
          }
        );
      }
    );
}


function bindDatasetActions() {
  document.addEventListener(
    "click",
    async (event) => {
      const runButton = (
        event.target.closest(
          "[data-open-run]"
        )
      );

      if (!runButton) {
        return;
      }

      runButton.disabled = true;
      runButton.textContent = (
        "Abriendo…"
      );

      await restoreHistoricalRun(
        runButton.dataset.openRun
      );

      runButton.disabled = false;
      runButton.textContent = (
        "Abrir decisión"
      );
    }
  );
}


function bindDataStageBridge() {
  function consumeDataStage(
    dataset,
    profile,
  ) {
    if (!dataset || !profile) {
      return;
    }

    setActiveDataset(dataset);
    setDatasetProfile(profile);
    clearDecisionState();
  }

  window.addEventListener(
    "dation:dataset-ready",
    (event) => {
      consumeDataStage(
        event.detail?.dataset,
        event.detail?.profile,
      );
    }
  );

  if (
    window.dationDataStage
      ?.activeDataset
    && window.dationDataStage
      ?.profile
  ) {
    consumeDataStage(
      window.dationDataStage
        .activeDataset,
      window.dationDataStage
        .profile,
    );
  }
}


function bindDecisionStageBridge() {
  async function consumeRun(
    run,
    dataset,
    profile,
  ) {
    if (!run || !dataset || !profile) {
      return;
    }

    setActiveDataset(dataset);
    setDatasetProfile(profile);
    setActiveRun(run);
    setExplanation(null);
    setMessages([]);

    restoreRunConfiguration(run);

    renderDashboard(
      run,
      profile,
    );

    renderExplanation(null);
    resetChat([]);

    renderInterpreterMeta(
      state.interpreter
    );

    navigate(
      "decision-dashboard"
    );

    try {
      await Promise.all([
        refreshRuns(),
        refreshSummary(),
        refreshDatasets(),
      ]);
    } catch (error) {
      console.warn(
        "No se pudo refrescar el workspace después de la corrida.",
        error,
      );
    }
  }

  window.dationConsumeDecisionRun = (
    run,
    dataset,
    profile,
  ) => {
    consumeRun(
      run,
      dataset,
      profile,
    );
  };

  window.addEventListener(
    "dation:run-ready",
    (event) => {
      consumeRun(
        event.detail?.run,
        event.detail?.dataset,
        event.detail?.profile,
      );
    }
  );

  if (
    window.dationDecisionStage
      ?.run
    && window.dationDecisionStage
      ?.dataset
    && window.dationDecisionStage
      ?.profile
  ) {
    consumeRun(
      window.dationDecisionStage.run,
      window.dationDecisionStage.dataset,
      window.dationDecisionStage.profile,
    );
  }
}

function bindInterpreter() {
  const generate = (
    $("#generate-explanation")
  );
  const progress = (
    $("#ai-progress")
  );
  const ask = (
    $("#ask-decision")
  );
  const question = (
    $("#decision-question")
  );

  generate.addEventListener(
    "click",
    async () => {
      if (!state.activeRun) {
        return;
      }

      generate.disabled = true;
      generate.textContent = (
        "Interpretando…"
      );

      showInlineStatus(
        progress,
        "Combinando evidencia calculada con la base de conocimiento versionada…",
        "loading",
      );

      try {
        const payload = (
          await explainRun(
            state.activeRun.id
          )
        );

        setExplanation(
          payload.explanation
        );

        renderExplanation(
          state.explanation
        );

        showInlineStatus(
          progress,
          "Interpretación generada y persistida.",
          "success",
        );

        generate.textContent = (
          "Regenerar interpretación"
        );
      } catch (error) {
        showInlineStatus(
          progress,
          error.message,
          "error",
        );
      } finally {
        generate.disabled = false;
      }
    }
  );

  $("#toggle-chat")
    .addEventListener(
      "click",
      () => {
        const panel = (
          $("#chat-panel")
        );

        const opening = (
          panel.classList.contains(
            "is-hidden"
          )
        );

        panel.classList.toggle(
          "is-hidden"
        );

        $("#toggle-chat")
          .textContent = (
            opening
              ? "Cerrar chat"
              : "Abrir chat con el intérprete"
          );

        if (opening) {
          question.focus();
        }
      }
    );

  $("#prompt-chips")
    .addEventListener(
      "click",
      (event) => {
        const chip = (
          event.target.closest(
            "button"
          )
        );

        if (!chip) {
          return;
        }

        question.value = (
          chip.textContent.trim()
        );
        question.focus();
      }
    );

  async function sendQuestion() {
    const text = (
      question.value.trim()
    );

    if (
      !state.activeRun
      || !text
    ) {
      return;
    }

    appendChatMessage(
      "user",
      text,
    );

    question.value = "";
    ask.disabled = true;
    ask.textContent = "…";

    const pendingId = (
      "pending-"
      + Date.now()
    );

    $("#chat-thread")
      .insertAdjacentHTML(
        "beforeend",
        `
          <div class="assistant-message" id="${pendingId}">
            <div class="message-avatar">D</div>
            <div>
              <strong>Dation Interpreter</strong>
              <p>Analizando la evidencia de esta decisión…</p>
            </div>
          </div>
        `,
      );

    try {
      const answer = (
        await askRun(
          state.activeRun.id,
          text,
        )
      );

      document
        .getElementById(
          pendingId
        )
        ?.remove();

      appendChatMessage(
        "assistant",
        answer.answer,
      );
    } catch (error) {
      document
        .getElementById(
          pendingId
        )
        ?.remove();

      appendChatMessage(
        "assistant",
        "No pude responder esta pregunta: "
        + error.message,
      );
    } finally {
      ask.disabled = false;
      ask.textContent = "↑";
      question.focus();
    }
  }

  ask.addEventListener(
    "click",
    sendQuestion,
  );

  question.addEventListener(
    "keydown",
    (event) => {
      if (
        (
          event.ctrlKey
          || event.metaKey
        )
        && event.key === "Enter"
      ) {
        event.preventDefault();
        sendQuestion();
      }
    }
  );
}


function downloadText(
  filename,
  content,
  mimeType,
) {
  const blob = new Blob(
    [content],
    {
      type: mimeType,
    },
  );

  const url = (
    URL.createObjectURL(blob)
  );

  const anchor = (
    document.createElement("a")
  );

  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(
    () => URL.revokeObjectURL(
      url
    ),
    500,
  );
}


function bindExports() {
  $("#download-json")
    .addEventListener(
      "click",
      () => {
        if (!state.activeRun) {
          return;
        }

        downloadText(
          (
            "dation-evidencia-"
            + state.activeRun.id
              .slice(0, 8)
            + ".json"
          ),
          JSON.stringify(
            state.activeRun
              .result_json,
            null,
            2,
          ),
          "application/json",
        );
      }
    );

  $("#export-decision")
    .addEventListener(
      "click",
      () => {
        if (
          !state.activeRun
          || !state.explanation
        ) {
          toast(
            "Generá primero la interpretación ejecutiva para exportar la decisión.",
            "error",
          );
          return;
        }

        const markdown = (
          buildDecisionMarkdown(
            state.activeRun,
            state.activeDataset,
            state.datasetProfile,
            state.explanation,
          )
        );

        downloadText(
          (
            "dation-decision-"
            + state.activeRun.id
              .slice(0, 8)
            + ".md"
          ),
          markdown,
          "text/markdown;charset=utf-8",
        );
      }
    );
}


function bindRefreshActions() {
  $("#datasets-refresh")
    .addEventListener(
      "click",
      () => refreshWorkspaceData({
        notify: true,
      })
    );

  $("#runs-refresh")
    .addEventListener(
      "click",
      () => refreshWorkspaceData({
        notify: true,
      })
    );
}


function bindGlobalErrors() {
  window.addEventListener(
    "unhandledrejection",
    (event) => {
      if (!booting) {
        toast(
          event.reason?.message
          || "Ocurrió un error inesperado.",
          "error",
        );
      }
    }
  );
}


bindNavigation();
bindDatasetActions();
bindDataStageBridge();
bindDecisionStageBridge();
bindInterpreter();
bindExports();
bindRefreshActions();
bindGlobalErrors();

bootstrap();
