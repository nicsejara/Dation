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
  runDecision,
  uploadDataset,
} from "./api.js";

import {
  decisionConfiguration,
  restoreRunConfiguration,
  setActiveDataset,
  setActiveRun,
  setCostWeight,
  setCustomMode,
  setDatasetProfile,
  setDatasets,
  setDecisionPreset,
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
  hideInlineStatus,
  renderActiveDataset,
  renderDashboard,
  renderDatasetProfile,
  renderDatasetsTable,
  renderDecisionConfiguration,
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
  updateExecutionReadiness,
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


async function loadDatasetProfile(
  dataset,
) {
  $("#data-config-state")
    .innerHTML = (
      '<span class="status-dot status-dot--pending"></span>'
      + " Analizando dataset"
    );

  try {
    const profile = (
      await getDatasetProfile(
        dataset.id
      )
    );

    setDatasetProfile(
      profile
    );

    renderDatasetProfile(
      profile
    );

    $("#data-config-state")
      .innerHTML = (
        '<span class="status-dot status-dot--live"></span>'
        + " Dataset válido"
      );

    updateExecutionReadiness();

    return profile;
  } catch (error) {
    setDatasetProfile(null);
    renderDatasetProfile(null);

    $("#data-config-state")
      .innerHTML = (
        '<span class="status-dot status-dot--danger"></span>'
        + " Perfil no disponible"
      );

    updateExecutionReadiness();

    throw error;
  }
}


async function selectDataset(
  dataset,
  {
    navigateToDda = false,
  } = {},
) {
  setActiveDataset(
    dataset
  );

  setDatasetProfile(null);
  clearDecisionState();

  renderActiveDataset(
    dataset
  );

  renderWorkspaceDatasets(
    state.datasets
  );

  if (navigateToDda) {
    navigate(
      "logistics-data"
    );
  }

  try {
    await loadDatasetProfile(
      dataset
    );

    if (navigateToDda) {
      window.setTimeout(
        () => {
          $("#dataset-profile-panel")
            ?.scrollIntoView({
              behavior: "smooth",
              block: "center",
            });
        },
        140,
      );
    }
  } catch (error) {
    toast(
      "El dataset fue seleccionado, pero no se pudo generar su perfil: "
      + error.message,
      "error",
    );
  }
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

    renderDecisionConfiguration();

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
  renderDecisionConfiguration();
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

  const continueToDecision = $("#continue-to-decision");

  if (continueToDecision) {
    continueToDecision.addEventListener(
      "click",
      () => {
        if (
          !state.activeDataset
          || !state.datasetProfile
        ) {
          toast(
            "Validá un dataset antes de configurar la decisión.",
            "error",
          );
          return;
        }

        navigate(
          "logistics-config"
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
      const useButton = (
        event.target.closest(
          "[data-use-dataset]"
        )
      );

      if (useButton) {
        const dataset = (
          datasetById(
            useButton.dataset
              .useDataset
          )
        );

        if (!dataset) {
          toast(
            "No se encontró el dataset seleccionado.",
            "error",
          );
          return;
        }

        await selectDataset(
          dataset,
          {
            navigateToDda: true,
          },
        );

        toast(
          dataset.original_filename
          + " quedó seleccionado como evidencia."
        );
        return;
      }

      const runButton = (
        event.target.closest(
          "[data-open-run]"
        )
      );

      if (runButton) {
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
    }
  );
}


function bindUpload() {
  const input = (
    $("#dataset-file")
  );
  const browse = (
    $("#browse-file")
  );
  const dropzone = (
    $("#upload-dropzone")
  );
  const progress = (
    $("#upload-progress")
  );

  browse.addEventListener(
    "click",
    () => input.click()
  );

  async function handleFile(file) {
    if (!file) {
      return;
    }

    if (
      !file.name
        .toLowerCase()
        .endsWith(".csv")
    ) {
      showInlineStatus(
        progress,
        "Sólo se admiten archivos CSV.",
        "error",
      );
      return;
    }

    browse.disabled = true;
    browse.textContent = (
      "Validando…"
    );

    showInlineStatus(
      progress,
      "Validando schema y almacenando evidencia original…",
      "loading",
    );

    try {
      const result = (
        await uploadDataset(file)
      );

      const datasetId = (
        result.duplicate
          ? result.existing_dataset.id
          : result.dataset.id
      );

      await refreshDatasets();

      const dataset = (
        datasetById(
          datasetId
        )
      );

      if (!dataset) {
        throw new Error(
          "El dataset se almacenó, pero no pudo recargarse."
        );
      }

      await selectDataset(
        dataset
      );

      showInlineStatus(
        progress,
        result.duplicate
          ? (
            "El archivo ya existía. "
            + "Se reutilizó el dataset almacenado."
          )
          : (
            "Dataset validado correctamente: "
            + `${result.validation.rows} filas y `
            + `${result.validation.columns} columnas.`
          ),
        "success",
      );

      await refreshSummary();

      toast(
        result.duplicate
          ? "Dataset existente reutilizado."
          : "Dataset validado y almacenado."
      );
    } catch (error) {
      showInlineStatus(
        progress,
        error.message,
        "error",
      );
    } finally {
      browse.disabled = false;
      browse.textContent = (
        "Seleccionar archivo CSV"
      );
      input.value = "";
    }
  }

  input.addEventListener(
    "change",
    () => handleFile(
      input.files?.[0]
    )
  );

  [
    "dragenter",
    "dragover",
  ].forEach(
    (type) => {
      dropzone.addEventListener(
        type,
        (event) => {
          event.preventDefault();
          dropzone.classList.add(
            "is-dragging"
          );
        }
      );
    }
  );

  [
    "dragleave",
    "drop",
  ].forEach(
    (type) => {
      dropzone.addEventListener(
        type,
        (event) => {
          event.preventDefault();
          dropzone.classList.remove(
            "is-dragging"
          );
        }
      );
    }
  );

  dropzone.addEventListener(
    "drop",
    (event) => {
      handleFile(
        event.dataTransfer
          ?.files?.[0]
      );
    }
  );
}


function bindDecisionConfiguration() {
  $("#decision-mode-grid")
    .addEventListener(
      "click",
      (event) => {
        const card = (
          event.target.closest(
            "[data-decision-mode]"
          )
        );

        if (!card) {
          return;
        }

        if (
          card.dataset
            .decisionMode
          === "custom"
        ) {
          setCustomMode();
        } else {
          setDecisionPreset(
            card.dataset.objective
          );
        }

        renderDecisionConfiguration();
      }
    );

  $("#cost-weight-slider")
    .addEventListener(
      "input",
      (event) => {
        setCostWeight(
          event.target.value
        );
        renderDecisionConfiguration();
      }
    );
}


function bindDecisionExecution() {
  const button = (
    $("#run-decision")
  );

  const progress = (
    $("#run-progress")
  );

  button.addEventListener(
    "click",
    async () => {
      if (
        !state.activeDataset
        || !state.datasetProfile
      ) {
        return;
      }

      button.disabled = true;
      button.classList.add(
        "is-loading"
      );
      button.textContent = (
        "Calculando decisión…"
      );

      showInlineStatus(
        progress,
        "Analizando alternativas y persistiendo la evidencia de la corrida…",
        "loading",
      );

      try {
        const run = await runDecision(
          state.activeDataset.id,
          decisionConfiguration(),
        );

        setActiveRun(run);
        setExplanation(null);
        setMessages([]);

        renderDashboard(
          run,
          state.datasetProfile,
        );

        renderExplanation(null);
        resetChat([]);

        renderInterpreterMeta(
          state.interpreter
        );

        showInlineStatus(
          progress,
          "Decisión calculada y persistida correctamente.",
          "success",
        );

        await Promise.all([
          refreshRuns(),
          refreshSummary(),
          refreshDatasets(),
        ]);

        navigate(
          "decision-dashboard"
        );
      } catch (error) {
        showInlineStatus(
          progress,
          error.message,
          "error",
        );
      } finally {
        button.classList.remove(
          "is-loading"
        );
        button.textContent = (
          "Ejecutar decisión"
        );
        updateExecutionReadiness();
      }
    }
  );
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
bindUpload();
bindDecisionConfiguration();
bindDecisionExecution();
bindInterpreter();
bindExports();
bindRefreshActions();
bindGlobalErrors();

bootstrap();
