(function () {
  "use strict";

  var EXECUTION_STORAGE_KEY = (
    "dation.logistics.execution.v1"
  );

  var state = {
    runId: null,
    status: null,
    explanation: null,
    messages: []
  };

  function $(selector) {
    return document.querySelector(
      selector
    );
  }

  function escapeHtml(value) {
    return String(
      value == null ? "" : value
    )
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function request(
    url,
    options
  ) {
    var response = await fetch(
      url,
      Object.assign(
        {
          credentials: "same-origin"
        },
        options || {}
      )
    );

    var contentType = (
      response.headers.get(
        "content-type"
      )
      || ""
    );

    var payload = (
      contentType.includes(
        "application/json"
      )
        ? await response.json()
        : await response.text()
    );

    if (!response.ok) {
      var detail = (
        typeof payload === "object"
        && payload
          ? (
            payload.detail
            || JSON.stringify(payload)
          )
          : (
            payload
            || response.statusText
          )
      );

      throw new Error(detail);
    }

    return payload;
  }

  function executionContext() {
    if (
      window.dationDashboardContext
      && window.dationDashboardContext.runId
    ) {
      return window.dationDashboardContext;
    }

    try {
      var raw = sessionStorage.getItem(
        EXECUTION_STORAGE_KEY
      );

      return raw
        ? JSON.parse(raw)
        : null;
    } catch (error) {
      return null;
    }
  }

  function currentRunId() {
    var context = executionContext();

    if (
      context
      && context.runId
    ) {
      return context.runId;
    }

    try {
      return new URLSearchParams(
        window.location.search
      ).get("run");
    } catch (error) {
      return null;
    }
  }

  function showStatus(
    message,
    type
  ) {
    var node = $("#ai-progress");

    if (!node) {
      return;
    }

    node.textContent = message;
    node.className = "inline-status";

    if (type) {
      node.classList.add(
        "is-" + type
      );
    }
  }

  function hideStatus() {
    var node = $("#ai-progress");

    if (node) {
      node.textContent = "";
      node.className = (
        "inline-status is-hidden"
      );
    }
  }

  function setControlsEnabled(enabled) {
    var generate = (
      $("#generate-explanation")
    );
    var ask = $("#ask-decision");
    var toggle = $("#toggle-chat");

    if (generate) {
      generate.disabled = !enabled;
    }

    if (ask) {
      ask.disabled = !enabled;
    }

    if (toggle) {
      toggle.disabled = !enabled;
    }
  }

  function listHtml(items) {
    var values = (
      Array.isArray(items)
        ? items
        : []
    );

    if (!values.length) {
      return (
        "<p>No se identificaron elementos "
        + "materiales para esta sección.</p>"
      );
    }

    return (
      "<ul>"
      + values.map(function (item) {
          return (
            "<li>"
            + escapeHtml(item)
            + "</li>"
          );
        }).join("")
      + "</ul>"
    );
  }

  function renderExplanation(
    explanation
  ) {
    var container = (
      $("#executive-insight")
    );

    if (!container) {
      return;
    }

    if (!explanation) {
      container.classList.add(
        "is-hidden"
      );
      return;
    }

    container.innerHTML = (
      '<div class="insight-hero">'
      + '<span class="section-kicker">Resumen ejecutivo</span>'
      + "<h3>"
      + escapeHtml(
          explanation.recommendation
        )
      + "</h3>"
      + "<p>"
      + escapeHtml(
          explanation.executive_summary
        )
      + "</p>"
      + "</div>"
      + '<div class="insight-grid">'
      + '<div class="insight-column">'
      + '<div class="insight-section"><h4>Por qué aparece esta recomendación</h4><p>'
      + escapeHtml(
          explanation.why_recommended
        )
      + "</p></div>"
      + '<div class="insight-section"><h4>Principales drivers</h4>'
      + listHtml(
          explanation.key_drivers
        )
      + "</div>"
      + '<div class="insight-section"><h4>Trade-offs</h4>'
      + listHtml(
          explanation.tradeoffs
        )
      + "</div></div>"
      + '<div class="insight-column">'
      + '<div class="insight-section"><h4>Impacto de negocio</h4>'
      + '<div class="insight-impact">'
      + "<div><span>Costo</span><strong>"
      + escapeHtml(
          explanation.business_impact
          && explanation.business_impact.cost
        )
      + "</strong></div>"
      + "<div><span>Viajes</span><strong>"
      + escapeHtml(
          explanation.business_impact
          && explanation.business_impact.trips
        )
      + "</strong></div>"
      + "<div><span>Distancia</span><strong>"
      + escapeHtml(
          explanation.business_impact
          && explanation.business_impact.distance
        )
      + "</strong></div>"
      + "</div></div>"
      + '<div class="insight-section"><h4>Supuestos relevantes</h4>'
      + listHtml(
          explanation.assumptions
        )
      + "</div>"
      + '<div class="insight-section"><h4>Caveats</h4>'
      + listHtml(
          explanation.caveats
        )
      + "</div></div></div>"
    );

    container.classList.remove(
      "is-hidden"
    );

    var exportButton = (
      $("#export-decision")
    );

    if (exportButton) {
      exportButton.disabled = false;
    }
  }

  function appendMessage(
    role,
    content
  ) {
    var thread = $("#chat-thread");

    if (!thread) {
      return;
    }

    var className = (
      role === "user"
        ? "user-message"
        : "assistant-message"
    );

    var avatar = (
      role === "user"
        ? "T"
        : "D"
    );

    var label = (
      role === "user"
        ? "Vos"
        : "Dation Interpreter"
    );

    thread.insertAdjacentHTML(
      "beforeend",
      '<div class="'
      + className
      + '"><div class="message-avatar">'
      + avatar
      + "</div><div><strong>"
      + label
      + "</strong><p>"
      + escapeHtml(content)
      + "</p></div></div>"
    );

    thread.scrollTop = (
      thread.scrollHeight
    );
  }

  function renderMessages(messages) {
    var thread = $("#chat-thread");

    if (!thread) {
      return;
    }

    thread.innerHTML = "";

    (
      Array.isArray(messages)
        ? messages
        : []
    ).forEach(function (message) {
      appendMessage(
        message.role,
        message.content
      );
    });
  }

  async function loadSavedInterpretation(
    runId
  ) {
    try {
      var payload = await request(
        "/api/runs/"
        + encodeURIComponent(runId)
        + "/interpretation"
      );

      var savedExplanation = (
        payload
        && payload.explanation
        && payload.explanation
          .response_json
          ? payload.explanation
              .response_json
          : null
      );

      state.explanation = (
        savedExplanation
      );

      state.messages = (
        payload
        && Array.isArray(
          payload.messages
        )
          ? payload.messages
          : []
      );

      renderExplanation(
        savedExplanation
      );

      renderMessages(
        state.messages
      );

      var generate = (
        $("#generate-explanation")
      );

      if (
        generate
        && savedExplanation
      ) {
        generate.textContent = (
          "Regenerar resumen IA"
        );
      }
    } catch (error) {
      console.warn(
        "No se pudo recuperar la interpretación guardada.",
        error
      );
    }
  }

  async function attachRun(runId) {
    if (!runId) {
      state.runId = null;
      setControlsEnabled(false);
      return;
    }

    state.runId = runId;

    setControlsEnabled(
      Boolean(
        state.status
        && state.status.configured
      )
    );

    await loadSavedInterpretation(
      runId
    );
  }

  async function refreshStatus() {
    var meta = $("#ai-dashboard-meta");

    try {
      var status = await request(
        "/api/system/llm-status"
      );

      state.status = status;

      if (meta) {
        meta.textContent = (
          status.configured
            ? (
              status.provider
              + " · "
              + status.model
              + " · Knowledge "
              + status.knowledge_version
            )
            : "Intérprete IA no configurado"
        );
      }

      setControlsEnabled(
        Boolean(
          status.configured
          && state.runId
        )
      );
    } catch (error) {
      state.status = {
        configured: false
      };

      if (meta) {
        meta.textContent = (
          "Intérprete IA no disponible"
        );
      }

      setControlsEnabled(false);
    }
  }

  async function generateExplanation() {
    var button = (
      $("#generate-explanation")
    );

    if (!state.runId) {
      showStatus(
        "No hay una corrida activa para interpretar.",
        "error"
      );
      return;
    }

    button.disabled = true;
    button.textContent = (
      "Interpretando…"
    );

    showStatus(
      "Analizando el DecisionResult y la base de conocimiento versionada…",
      "loading"
    );

    try {
      var payload = await request(
        "/api/runs/"
        + encodeURIComponent(
            state.runId
          )
        + "/explain",
        {
          method: "POST"
        }
      );

      state.explanation = (
        payload.explanation
      );

      renderExplanation(
        state.explanation
      );

      showStatus(
        "Resumen ejecutivo generado y persistido.",
        "success"
      );

      button.textContent = (
        "Regenerar resumen IA"
      );
    } catch (error) {
      showStatus(
        error.message,
        "error"
      );
    } finally {
      button.disabled = (
        !state.status
        || !state.status.configured
      );
    }
  }

  function toggleChat() {
    var panel = $("#chat-panel");
    var button = $("#toggle-chat");
    var question = (
      $("#decision-question")
    );

    if (!panel || !button) {
      return;
    }

    var opening = (
      panel.classList.contains(
        "is-hidden"
      )
    );

    panel.classList.toggle(
      "is-hidden"
    );

    button.textContent = (
      opening
        ? "Cerrar chat"
        : "Abrir chat"
    );

    if (opening && question) {
      question.focus();
    }
  }

  async function sendQuestion() {
    var question = (
      $("#decision-question")
    );
    var ask = $("#ask-decision");

    if (
      !state.runId
      || !question
      || !ask
    ) {
      return;
    }

    var text = (
      question.value.trim()
    );

    if (!text) {
      return;
    }

    appendMessage(
      "user",
      text
    );

    question.value = "";
    ask.disabled = true;
    ask.textContent = "…";

    var pendingId = (
      "interpreter-pending-"
      + Date.now()
    );

    var thread = $("#chat-thread");

    if (thread) {
      thread.insertAdjacentHTML(
        "beforeend",
        '<div class="assistant-message" id="'
        + pendingId
        + '"><div class="message-avatar">D</div><div>'
        + "<strong>Dation Interpreter</strong>"
        + "<p>Analizando la evidencia de esta decisión…</p>"
        + "</div></div>"
      );
    }

    try {
      var payload = await request(
        "/api/runs/"
        + encodeURIComponent(
            state.runId
          )
        + "/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": (
              "application/json"
            )
          },
          body: JSON.stringify({
            question: text
          })
        }
      );

      var pending = (
        document.getElementById(
          pendingId
        )
      );

      if (pending) {
        pending.remove();
      }

      appendMessage(
        "assistant",
        payload.answer
      );
    } catch (error) {
      var failedPending = (
        document.getElementById(
          pendingId
        )
      );

      if (failedPending) {
        failedPending.remove();
      }

      appendMessage(
        "assistant",
        (
          "No pude responder esta pregunta: "
          + error.message
        )
      );
    } finally {
      ask.disabled = false;
      ask.textContent = "↑";
      question.focus();
    }
  }

  function bindControls() {
    var generate = (
      $("#generate-explanation")
    );
    var toggle = $("#toggle-chat");
    var ask = $("#ask-decision");
    var question = (
      $("#decision-question")
    );
    var chips = $("#prompt-chips");

    if (generate) {
      generate.addEventListener(
        "click",
        generateExplanation
      );
    }

    if (toggle) {
      toggle.addEventListener(
        "click",
        toggleChat
      );
    }

    if (ask) {
      ask.addEventListener(
        "click",
        sendQuestion
      );
    }

    if (question) {
      question.addEventListener(
        "keydown",
        function (event) {
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

    if (chips) {
      chips.addEventListener(
        "click",
        function (event) {
          var chip = (
            event.target.closest(
              "button"
            )
          );

          if (
            !chip
            || !question
          ) {
            return;
          }

          question.value = (
            chip.textContent.trim()
          );
          question.focus();
        }
      );
    }
  }

  async function boot() {
    bindControls();
    setControlsEnabled(false);

    state.runId = currentRunId();

    await refreshStatus();

    if (state.runId) {
      await attachRun(
        state.runId
      );
    }

    hideStatus();
  }

  window.addEventListener(
    "dation:dashboard-completed",
    function (event) {
      var run = (
        event.detail
        && event.detail.run
      );

      if (run && run.id) {
        attachRun(run.id);
      }
    }
  );

  window.addEventListener(
    "dation:run-ready",
    function (event) {
      var run = (
        event.detail
        && event.detail.run
      );

      if (run && run.id) {
        attachRun(run.id);
      }
    }
  );

  if (
    document.readyState
    === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      {
        once: true
      }
    );
  } else {
    boot();
  }
})();