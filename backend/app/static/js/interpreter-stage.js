(function () {
  "use strict";

  var EXECUTION_STORAGE_KEY = (
    "dation.logistics.execution.v1"
  );

  var F = (
    window.DationDashboardFormatters
    || {
      normalizeBusinessText: function (value) {
        return String(value || "");
      },
      objectiveLabel: function () {
        return "Objetivo";
      }
    }
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
    var fab = $("#dation-chat-fab");

    if (generate) {
      generate.disabled = !enabled;
    }

    if (ask) {
      ask.disabled = !enabled;
    }

    if (toggle) {
      toggle.disabled = !enabled;
    }

    if (fab) {
      fab.disabled = !enabled;
    }
  }

  function cleanText(value) {
    return F.normalizeBusinessText(
      value == null ? "" : value
    );
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
            + escapeHtml(
                cleanText(item)
              )
            + "</li>"
          );
        }).join("")
      + "</ul>"
    );
  }

  function currentConfiguration() {
    var context = executionContext();
    var run = (
      context
      && context.run
    );

    return (
      run
      && (
        run.configuration_json
        || (
          run.result_json
          && run.result_json
            .configuration
        )
      )
    )
    || {};
  }

  function summaryTitle() {
    return (
      "Recomendación: "
      + F.objectiveLabel(
          currentConfiguration()
        )
          .replace(/^Minimizar/, "minimizar")
          .replace(/^Objetivo/, "objetivo")
    );
  }

  function copyableExplanationText(
    explanation
  ) {
    if (!explanation) {
      return "";
    }

    var lines = [
      summaryTitle(),
      "",
      cleanText(
        explanation.executive_summary
      ),
      "",
      "Recomendación:",
      cleanText(
        explanation.recommendation
      ),
      "",
      "Por qué:",
      cleanText(
        explanation.why_recommended
      ),
      "",
      "Principales drivers:",
      (
        explanation.key_drivers
        || []
      ).map(function (item) {
        return (
          "- " + cleanText(item)
        );
      }).join("\n"),
      "",
      "Trade-offs:",
      (
        explanation.tradeoffs
        || []
      ).map(function (item) {
        return (
          "- " + cleanText(item)
        );
      }).join("\n"),
      "",
      "Supuestos:",
      (
        explanation.assumptions
        || []
      ).map(function (item) {
        return (
          "- " + cleanText(item)
        );
      }).join("\n"),
      "",
      "Riesgos y limitaciones:",
      (
        explanation.caveats
        || []
      ).map(function (item) {
        return (
          "- " + cleanText(item)
        );
      }).join("\n")
    ];

    return lines.join("\n");
  }

  function renderExplanation(
    explanation
  ) {
    var container = (
      $("#executive-insight")
    );
    var title = (
      $("#ai-summary-title")
    );
    var copyButton = (
      $("#copy-explanation")
    );

    if (!container) {
      return;
    }

    if (!explanation) {
      container.classList.add(
        "is-hidden"
      );

      if (copyButton) {
        copyButton.disabled = true;
      }

      return;
    }

    if (title) {
      title.textContent = (
        summaryTitle()
      );
    }

    var risk = (
      explanation.caveats
      && explanation.caveats.length
        ? explanation.caveats[0]
        : (
          explanation.assumptions
          && explanation.assumptions.length
            ? explanation.assumptions[0]
            : "La recomendación depende de los supuestos del modelo."
        )
    );

    var summaryBullets = [
      cleanText(
        explanation.recommendation
      ),
      cleanText(
        explanation.executive_summary
      ),
      cleanText(risk)
    ];

    container.innerHTML = (
      '<div class="ai-summary-card">'
      + "<h3>En resumen</h3>"
      + '<ul class="ai-summary-list">'
      + summaryBullets.map(
        function (item) {
          return (
            "<li>"
            + escapeHtml(item)
            + "</li>"
          );
        }
      ).join("")
      + "</ul>"
      + "</div>"
      + '<div class="ai-accordion">'
      + "<details open>"
      + "<summary>Por qué esta recomendación</summary>"
      + '<div class="ai-accordion__body"><p>'
      + escapeHtml(
          cleanText(
            explanation.why_recommended
          )
        )
      + "</p></div>"
      + "</details>"
      + "<details>"
      + "<summary>Principales drivers</summary>"
      + '<div class="ai-accordion__body">'
      + listHtml(
          explanation.key_drivers
        )
      + "</div>"
      + "</details>"
      + "<details>"
      + "<summary>Trade-offs</summary>"
      + '<div class="ai-accordion__body">'
      + listHtml(
          explanation.tradeoffs
        )
      + "</div>"
      + "</details>"
      + "<details>"
      + "<summary>Supuestos</summary>"
      + '<div class="ai-accordion__body">'
      + listHtml(
          explanation.assumptions
        )
      + "</div>"
      + "</details>"
      + "<details>"
      + "<summary>Riesgos y limitaciones</summary>"
      + '<div class="ai-accordion__body">'
      + listHtml(
          explanation.caveats
        )
      + "</div>"
      + "</details>"
      + "</div>"
    );

    container.classList.remove(
      "is-hidden"
    );

    if (copyButton) {
      copyButton.disabled = false;
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

    var displayedContent = (
      role === "assistant"
        ? cleanText(content)
        : content
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
      + escapeHtml(
          displayedContent
        )
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

      if (savedExplanation) {
        window.dispatchEvent(
          new CustomEvent(
            "dation:interpreter-explanation",
            {
              detail: {
                explanation: savedExplanation
              }
            }
          )
        );
      }

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
    var details = $("#details-ai");

    try {
      var status = await request(
        "/api/system/llm-status"
      );

      state.status = status;

      if (details) {
        details.textContent = (
          status.configured
            ? (
              status.provider
              + " · "
              + status.model
              + " · conocimiento "
              + status.knowledge_version
            )
            : "No configurado"
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

      if (details) {
        details.textContent = (
          "No disponible"
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

      window.dispatchEvent(
        new CustomEvent(
          "dation:interpreter-explanation",
          {
            detail: {
              explanation: state.explanation
            }
          }
        )
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

  function setChatOpen(open) {
    var panel = $("#chat-panel");
    var button = $("#toggle-chat");
    var fab = $("#dation-chat-fab");
    var question = (
      $("#decision-question")
    );

    if (!panel || !button) {
      return;
    }

    panel.classList.toggle(
      "is-hidden",
      !open
    );

    button.classList.toggle(
      "is-open",
      open
    );

    button.setAttribute(
      "aria-expanded",
      open ? "true" : "false"
    );

    if (fab) {
      fab.setAttribute(
        "aria-expanded",
        open ? "true" : "false"
      );
      fab.classList.toggle(
        "is-open",
        open
      );
    }

    if (open && question) {
      window.setTimeout(
        function () {
          question.focus();
        },
        80
      );
    }
  }

  function toggleChat() {
    var panel = $("#chat-panel");

    if (!panel) {
      return;
    }

    setChatOpen(
      panel.classList.contains(
        "is-hidden"
      )
    );
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
    var fab = $("#dation-chat-fab");
    var copy = $("#copy-explanation");
    var ask = $("#ask-decision");
    var close = $("#chat-close");
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

    if (fab) {
      fab.addEventListener(
        "click",
        toggleChat
      );
    }

    if (copy) {
      copy.addEventListener(
        "click",
        function () {
          var text = (
            copyableExplanationText(
              state.explanation
            )
          );

          if (
            text
            && navigator.clipboard
            && navigator.clipboard
              .writeText
          ) {
            navigator.clipboard
              .writeText(text);

            copy.textContent = (
              "Copiado"
            );

            window.setTimeout(
              function () {
                copy.textContent = (
                  "Copiar"
                );
              },
              1200
            );
          }
        }
      );
    }

    if (ask) {
      ask.addEventListener(
        "click",
        sendQuestion
      );
    }

    if (close) {
      close.addEventListener(
        "click",
        function () {
          setChatOpen(false);
        }
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

    document.addEventListener(
      "keydown",
      function (event) {
        if (event.key === "Escape") {
          setChatOpen(false);
        }
      }
    );

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