function el(tag, value, className = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value != null) node.textContent = value;
  return node;
}

function missingLabel(item) {
  const source = item.dataset === "orders" ? "Órdenes" : "Flota";
  return `${source} · ${item.label}`;
}

function capabilityChips(capabilities = []) {
  const wrap = el("div", null, "dispatch-readiness-capabilities");
  capabilities.forEach((capability) => {
    const chip = el(
      "span",
      `${capability.available ? "✓" : "○"} ${capability.label}`,
      `dispatch-readiness-chip ${capability.available ? "is-ready" : "is-muted"}`,
    );
    if (!capability.available && capability.missing?.length) {
      chip.title = (
        "Se habilita al completar: "
        + capability.missing.map(missingLabel).join(", ")
      );
    }
    wrap.append(chip);
  });
  return wrap;
}

function decisionCard(decision) {
  const card = el(
    "article",
    null,
    `dispatch-readiness-card is-${decision.state}`,
  );

  const index = el(
    "span",
    String(decision.level).padStart(2, "0"),
    "dispatch-readiness-level",
  );
  const copy = el("div", null, "dispatch-readiness-copy");
  const state = el(
    "span",
    decision.state === "available"
      ? "● Disponible"
      : decision.data_ready
        ? "🔒 Datos listos · requiere decisión previa"
        : "🔒 Requiere datos opcionales",
    `dispatch-readiness-state is-${decision.state}`,
  );

  copy.append(
    state,
    el("h3", decision.label),
    el("p", decision.question),
  );

  if (decision.capabilities?.length) {
    copy.append(capabilityChips(decision.capabilities));
  }

  if (decision.missing?.length) {
    const details = document.createElement("details");
    details.className = "dispatch-readiness-missing";
    const summary = document.createElement("summary");
    summary.textContent = (
      `Completar más adelante · ${decision.missing.length} `
      + `${decision.missing.length === 1 ? "dato" : "datos"}`
    );
    const list = el("div", null, "dispatch-readiness-missing-list");
    decision.missing.forEach((item) => {
      list.append(el("span", missingLabel(item)));
    });
    details.append(summary, list);
    copy.append(details);
  } else if (decision.unlock_reason && decision.state === "locked") {
    copy.append(
      el("small", decision.unlock_reason, "dispatch-readiness-unlock"),
    );
  }

  card.append(index, copy);
  return card;
}

export function renderDecisionReadiness(root, readiness) {
  root.replaceChildren();
  root.className = "dispatch-panel dispatch-readiness-panel";

  const head = el("div", null, "dispatch-readiness-head");
  const copy = el("div");
  copy.append(
    el("span", "DECISION READINESS", "dispatch-kicker"),
    el("h2", "Qué decisiones habilitan estos datos"),
    el(
      "p",
      (
        "No necesitás completar toda la plantilla para empezar. "
        + "Dation usa sólo los datos requeridos por cada nivel de decisión."
      ),
    ),
  );
  const badge = el(
    "span",
    readiness
      ? `${readiness.summary?.data_ready || 0} de 3 con datos suficientes`
      : "Esperando Data Pack",
    "dispatch-readiness-badge",
  );
  head.append(copy, badge);
  root.append(head);

  if (!readiness) {
    root.append(
      el(
        "p",
        "Cargá Órdenes y Flota para analizar la ruta de decisiones.",
        "dispatch-readiness-empty",
      ),
    );
    return;
  }

  const chain = el("div", null, "dispatch-readiness-chain");
  readiness.decisions.forEach((decision, index) => {
    chain.append(decisionCard(decision));
    if (index < readiness.decisions.length - 1) {
      chain.append(
        el("span", "↓", "dispatch-readiness-connector"),
      );
    }
  });
  root.append(chain);

  const note = el("div", null, "dispatch-readiness-note");
  note.append(
    el("strong", "Data Pack progresivo"),
    el(
      "p",
      (
        "Las columnas opcionales pueden agregarse en una nueva versión "
        + "de los mismos CSV cuando quieras desbloquear decisiones posteriores."
      ),
    ),
  );
  root.append(note);
}