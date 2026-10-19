import {createScope} from "./dispatch/lifecycle.mjs";
import {mountHomeCatalog} from "./home-dda-catalog.mjs";
import {mountDropdown} from "./platform/components.mjs";
import {currentLogisticsEnabled} from "./platform/entitlements.mjs";
import {
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
  renderActiveDataset,
  renderDatasetProfile,
  renderDatasetsTable,
  renderExplanation,
  renderHomeSummary,
  renderRunsTable,
  renderSystemStatus,
  renderTechnicalEvidence,
  renderWorkspaceDatasets,
  resetChat,
  showInlineStatus,
  toast,
} from "./ui.js";


let booting = true;
let libraryScope=null;


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


async function refreshDatasets(scope=libraryScope) {
  if(!scope?.active)return;
  const response = (
    await getDatasets(80,{signal:scope.signal})
  );

  if(!scope.active)return;
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


async function refreshRuns(scope=libraryScope) {
  if(!scope?.active)return;
  const response = (
    await getRuns(100,null,{signal:scope.signal})
  );

  if(!scope.active)return;
  setRuns(
    response.items || []
  );

  renderRunsTable(
    state.runs,
    state.datasets,
  );
}


async function refreshSummary(scope=libraryScope) {
  if(!scope?.active)return;
  const summary = (
    await getWorkspaceSummary({signal:scope.signal})
  );

  if(!scope.active)return;
  renderHomeSummary(
    summary,
    state.runs,
  );
}


async function refreshInterpreter(scope=libraryScope) {
  if(!scope?.active)return;
  try {
    const interpreter = (
      await getInterpreterStatus({signal:scope.signal})
    );

    if(!scope.active)return;
    setInterpreter(
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

    if(!scope.active)return;
    setInterpreter(
      unavailable
    );

    return unavailable;
  }
}


async function refreshSystemStatus(scope=libraryScope) {
  if(!scope?.active)return;
  let supabaseOk = false;

  try {
    const status = (
      await getSupabaseStatus({signal:scope.signal})
    );

    supabaseOk = Boolean(
      status?.ok
    );
  } catch {
    supabaseOk = false;
  }

  if(!scope.active)return;
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
  const exportButton = (
    $("#export-decision")
  );

  if (exportButton) {
    exportButton.disabled = true;
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

    if (['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(run.result_json?.schema_version)) {
      if(window.DationDispatch?.openRun)return window.DationDispatch.openRun(run.id);
      if (window.DationDispatch?.show) {
        window.DationDispatch.show(run);
      } else {
        const dispatch = await import('/static/js/dispatch/workspace.mjs');
        dispatch.show(run);
      }
      return;
    }

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

    navigate(
      "decision-dashboard"
    );

    if (
      typeof window
        .dationDashboardCompleted
      === "function"
    ) {
      window.dationDashboardCompleted(
        run,
        dataset,
        profile
      );
    }

    renderExplanation(
      savedExplanation
    );

    resetChat(
      state.messages
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

  booting = false;
  mountLibraryView(window.dationGetCurrentView?.());

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


function bindDecisionStageBridge() {
  async function consumeRun(
    run,
    dataset,
    profile,
  ) {
    if(['assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'].includes(run?.result_json?.schema_version)&&window.DationDispatch)return window.DationDispatch.openRun(run.id);
    if (!run || !dataset || !profile) {
      return;
    }

    navigate(
      "decision-dashboard"
    );

    setActiveDataset(dataset);
    setDatasetProfile(profile);
    setActiveRun(run);
    setExplanation(null);
    setMessages([]);

    restoreRunConfiguration(run);

    try {
      renderTechnicalEvidence(
        run
      );
    } catch (error) {
      console.warn(
        "No se pudo actualizar la evidencia técnica.",
        error,
      );
    }

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
  ) => (
    consumeRun(
      run,
      dataset,
      profile,
    )
  );

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

function bindInterpreterStateBridge() {
  window.addEventListener("dation:interpreter-explanation", (event) => {
    setExplanation(event.detail?.explanation || null);
  });
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


mountHomeCatalog(document.querySelector('[data-home-dda-catalog]'));
bindNavigation();
bindDatasetActions();
bindDecisionStageBridge();
bindInterpreterStateBridge();
bindRefreshActions();
bindGlobalErrors();

bootstrap();

function mountLibraryView(view){
  libraryScope?.dispose();libraryScope=null;
  if(!['traceability','settings','inicio'].includes(view))return;
  if(view==='inicio'||(view==='traceability'&&!currentLogisticsEnabled()))return;
  const panel=document.querySelector('[data-view-panel="'+view+'"]');if(!panel)return;
  const scope=libraryScope=createScope(view==='settings'?panel.querySelector('[data-platform-diagnostics]'):panel);
  if(view==='settings'){
    const trigger=panel.querySelector('[data-settings-help]');
    const help=panel.querySelector('#settings-status-help');
    if(trigger&&help){const dropdown=mountDropdown({trigger,panel:help});scope.own(()=>dropdown.dispose());}
  }
  if(view==='settings'&&window.dationSession?.identity?.membership?.access_role!=='admin')return;
  const work=view==='settings'?refreshInterpreter(scope).then(()=>scope.active&&refreshSystemStatus(scope)):Promise.all([refreshDatasets(scope),refreshRuns(scope),refreshSummary(scope)]);
  work.catch(error=>{if(scope.active)toast(error.message,'error');});
}
window.addEventListener('dation:view',event=>mountLibraryView(event.detail.view));
window.addEventListener('pagehide',()=>libraryScope?.dispose());
window.addEventListener('pageshow',event=>{if(event.persisted)mountLibraryView(window.dationGetCurrentView?.());});
