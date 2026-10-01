import {api, date, num, post} from "../shared.mjs";
import {createDropCard} from "./dropcard.mjs";
import {renderLibrary} from "./library.mjs";
import {renderPreflight} from "./preflight-panel.mjs";
import {cardState, continueState} from "./selectors.mjs";
import {renderSystemBanner} from "./system-banner.mjs";
import {renderValidationReport} from "./validation-report.mjs";

const MAX_BYTES = 10 * 1024 * 1024;

function element(tag, text, className = "") {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text != null) {
    node.textContent = text;
  }
  return node;
}

function setCardStatus(refs, state) {
  refs.status.className = `dispatch-upload-status is-${state.tone}`;
  refs.status.textContent = state.label;
}

function profileFor(dataset) {
  return dataset?.profile_json?.profile || null;
}

function renderProfile(root, kind, dataset, report) {
  root.replaceChildren();
  const profile = dataset ? profileFor(dataset) : report?.profile;
  if (!profile) {
    return;
  }

  const title = element(
    "strong",
    dataset
      ? dataset.label || dataset.original_filename
      : "Perfil del archivo validado",
  );
  root.append(title);

  if (kind === "orders") {
    root.append(
      element(
        "p",
        [
          `${num(dataset?.row_count ?? report?.rows)} registros`,
          `${num(profile.total_units)} unidades`,
          `${num(profile.total_weight_kg)} kg`,
          `${num(profile.routes)} rutas`,
          profile.date_from && profile.date_to
            ? `${date(profile.date_from)} – ${date(profile.date_to)}`
            : null,
        ].filter(Boolean).join(" · "),
      ),
    );
    return;
  }

  const tableWrap = element("div", null, "dispatch-table-wrap");
  const table = document.createElement("table");
  const head = document.createElement("thead");
  head.innerHTML = (
    "<tr><th>Camión</th><th>Propiedad</th><th>Capacidad</th>"
    + "<th>Salidas/día</th></tr>"
  );
  const body = document.createElement("tbody");
  for (const vehicle of profile.fleet || []) {
    const row = document.createElement("tr");
    const values = [
      vehicle.vehicle_type,
      vehicle.ownership === "own" ? "Propio" : "Tercerizado",
      `${num(vehicle.capacity_kg)} kg`,
      vehicle.units_available == null ? "Sin límite" : num(vehicle.units_available),
    ];
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
  table.append(head, body);
  tableWrap.append(table);
  root.append(tableWrap);
}

function makeExplainer() {
  const section = element("section", null, "dispatch-panel dispatch-how");
  section.append(
    element("h2", "Cómo funciona"),
    element(
      "p",
      (
        "Las órdenes indican qué hay que despachar y cambian en cada corrida. "
        + "La flota describe con qué camiones contás y se puede reutilizar."
      ),
    ),
  );

  const steps = element("div", null, "dispatch-how-steps");
  [
    ["1", "Descargá la plantilla"],
    ["2", "Completá tus datos sin cambiar los encabezados"],
    ["3", "Subí el CSV; se valida antes de guardarse"],
    ["4", "Revisá advertencias y pasá a configurar"],
  ].forEach(([number, text]) => {
    const item = element("article");
    item.append(
      element("span", number),
      element("strong", text),
    );
    steps.append(item);
  });
  section.append(steps);

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Formato y validaciones";
  details.append(summary);
  details.append(
    element(
      "p",
      (
        "Formato aceptado: CSV UTF-8, separador coma o punto y coma, máximo 10 MB, "
        + "encabezado en la primera fila. Fechas AAAA-MM-DD o d/m/AAAA. "
        + "Los decimales usan punto; con punto y coma también se admite coma decimal."
      ),
    ),
    element(
      "p",
      (
        "Dation valida columnas, tipos, rangos, identificadores duplicados, rutas, "
        + "distancias y compatibilidad entre órdenes y flota. Los archivos válidos "
        + "se guardan en almacenamiento privado con una huella para detectar duplicados."
      ),
    ),
    element(
      "p",
      "Los errores bloquean el avance. Las advertencias se muestran, pero permiten continuar.",
    ),
  );
  section.append(details);
  return section;
}

function clientFileProblem(file) {
  if (!file?.name?.toLowerCase().endsWith(".csv")) {
    return "Sólo se admiten archivos con extensión .csv.";
  }
  if (file.size > MAX_BYTES) {
    return "El archivo supera el límite de 10 MB.";
  }
  return null;
}

export async function mountUploadScreen(
  root,
  {
    state,
    persist,
    runPreflight,
    onNext,
    isReady,
  },
) {
  const local = {
    status: null,
    contracts: null,
    reports: {
      orders: null,
      fleet: null,
    },
    validating: {
      orders: false,
      fleet: false,
    },
    saveErrors: {
      orders: null,
      fleet: null,
    },
    libraries: {
      orders: [],
      fleet: [],
    },
  };

  root.replaceChildren();
  root.className = "dispatch dispatch-upload-screen";

  const heading = element("header", null, "dispatch-upload-heading");
  const meta = element("div", null, "dispatch-upload-heading-meta");
  meta.append(
    element("span", "DDA Logística", "dispatch-kicker"),
    element("span", "Paso 1 de 3", "dispatch-step-chip"),
  );
  heading.append(
    meta,
    element("h1", "Cargar datos"),
    element(
      "p",
      "Para calcular el plan necesitamos dos archivos CSV: qué hay que entregar y con qué camiones.",
    ),
  );

  const banner = element("section");
  banner.hidden = true;
  const grid = element("div", null, "dispatch-data-grid");
  const preflightRoot = element("section", null, "dispatch-panel");
  const footer = element("div", null, "dispatch-footer dispatch-upload-footer");
  const footerText = element("div");
  footerText.append(
    element("strong", "Preparando datos"),
    element("p", "Cargando contratos y estado del sistema…"),
  );
  const next = element("button", "Configurar decisión →");
  next.type = "button";
  next.disabled = true;
  footer.append(footerText, next);

  root.append(
    heading,
    banner,
    makeExplainer(),
    grid,
    preflightRoot,
    footer,
  );

  let refs = {};

  function updateFooter() {
    const result = continueState({
      storageAvailable: Boolean(local.status?.available),
      orders: state.orders,
      fleet: state.fleet,
      reports: local.reports,
      preflight: state.preflight,
    });
    footerText.querySelector("strong").textContent = (
      result.enabled ? "Datos listos" : "Configuración pendiente"
    );
    footerText.querySelector("p").textContent = result.message;
    next.disabled = !result.enabled;
    window.dationSetDataReady(Boolean(result.enabled && isReady()));
  }

  function updateCard(kind) {
    const card = refs[kind];
    if (!card) {
      return;
    }
    const dataset = state[kind];
    const report = local.reports[kind];
    setCardStatus(
      card,
      cardState({
        validating: local.validating[kind],
        report,
        dataset,
        saveError: local.saveErrors[kind],
        storageAvailable: Boolean(local.status?.available),
      }),
    );
    renderValidationReport(card.report, report);
    renderProfile(card.profile, kind, dataset, report);
  }

  async function refreshPreflight() {
    state.preflight = null;
    renderPreflight(preflightRoot, null, state.orders, state.fleet);
    updateFooter();

    if (!state.orders || !state.fleet || !local.status?.available) {
      return;
    }

    try {
      await runPreflight();
    } catch (error) {
      state.preflight = {
        valid: false,
        errors: [
          {
            code: "PREFLIGHT_ERROR",
            detail: error.message,
          },
        ],
        warnings: [],
        anomalies: [],
      };
    }

    renderPreflight(
      preflightRoot,
      state.preflight,
      state.orders,
      state.fleet,
    );
    updateFooter();
  }

  async function loadLibrary(kind) {
    if (!local.status?.available) {
      local.libraries[kind] = [];
      renderLibrary(refs[kind].library, {
        kind,
        items: [],
        selected: state[kind],
        onSelect: () => {},
        onArchive: () => {},
      });
      return;
    }

    try {
      const response = await api(
        `/api/datasets?type=${kind}&limit=20&offset=0`,
      );
      local.libraries[kind] = response.items || [];

      if (state[kind]) {
        state[kind] = (
          local.libraries[kind].find((item) => item.id === state[kind].id)
          || null
        );
      }
      if (kind === "fleet" && !state.fleet) {
        state.fleet = (
          local.libraries.fleet.find((item) => item.is_default)
          || null
        );
      }
      persist();

      renderLibrary(refs[kind].library, {
        kind,
        items: local.libraries[kind],
        selected: state[kind],
        onSelect: async (dataset) => {
          state[kind] = dataset;
          local.reports[kind] = dataset.profile_json || null;
          local.saveErrors[kind] = null;
          persist();
          updateCard(kind);
          await refreshPreflight();
          await loadLibrary(kind);
        },
        onArchive: async (dataset) => {
          try {
            await post(`/api/datasets/${dataset.id}/archive`, {});
            if (state[kind]?.id === dataset.id) {
              state[kind] = null;
              persist();
            }
            await loadLibrary(kind);
            updateCard(kind);
            await refreshPreflight();
          } catch (error) {
            local.saveErrors[kind] = error.message;
            updateCard(kind);
          }
        },
      });
    } catch (error) {
      refs[kind].library.replaceChildren(
        element(
          "p",
          `No se pudo cargar la biblioteca: ${error.message}`,
          "dispatch-alert",
        ),
      );
    }
  }

  async function saveValid(kind, file) {
    if (!local.status?.available) {
      updateCard(kind);
      updateFooter();
      return;
    }

    const form = new FormData();
    form.append("file", file);
    form.append(
      "label",
      refs[kind].labelInput.value.trim() || file.name,
    );
    if (kind === "fleet" && state.fleet?.id) {
      form.append("parent_dataset_id", state.fleet.id);
    }

    try {
      const stored = await api(
        `/api/datasets/upload?dataset_type=${kind}`,
        {
          method: "POST",
          body: form,
        },
      );
      const dataset = stored.dataset || stored.existing_dataset;
      state[kind] = dataset;
      local.saveErrors[kind] = null;
      persist();

      if (
        kind === "fleet"
        && refs[kind].defaultInput?.checked
      ) {
        await post(`/api/datasets/${dataset.id}/default`, {});
      }

      if (stored.duplicate) {
        const note = element(
          "p",
          (
            "Este archivo ya estaba cargado"
            + (dataset.created_at
              ? ` el ${date(dataset.created_at.slice(0, 10))}`
              : "")
            + ": se reutilizó esa versión."
          ),
          "dispatch-upload-note",
        );
        refs[kind].report.prepend(note);
      }

      await loadLibrary(kind);
      updateCard(kind);
      await refreshPreflight();
    } catch (error) {
      local.saveErrors[kind] = error.message;
      updateCard(kind);
      updateFooter();
    }
  }

  async function handleFile(kind, file) {
    const problem = clientFileProblem(file);
    if (problem) {
      local.reports[kind] = {
        valid: false,
        rows: 0,
        errors: [
          {
            code: "INVALID_FILE",
            message: problem,
            hint: "Elegí un CSV válido de hasta 10 MB.",
          },
        ],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
      updateCard(kind);
      updateFooter();
      return;
    }

    local.validating[kind] = true;
    local.saveErrors[kind] = null;
    updateCard(kind);

    try {
      const form = new FormData();
      form.append("file", file);
      const report = await api(
        `/api/datasets/validate?dataset_type=${kind}`,
        {
          method: "POST",
          body: form,
        },
      );
      local.reports[kind] = report;
      if (report.valid) {
        await saveValid(kind, file);
      }
    } catch (error) {
      local.reports[kind] = {
        valid: false,
        rows: 0,
        errors: [
          {
            code: "VALIDATION_REQUEST_FAILED",
            message: error.message,
            hint: "Reintentá la carga. Si persiste, revisá la conexión.",
          },
        ],
        warnings: [],
        counts: {errors: 1, warnings: 0},
        truncated: false,
      };
    } finally {
      local.validating[kind] = false;
      updateCard(kind);
      updateFooter();
    }
  }

  try {
    const [status, contracts] = await Promise.all([
      api("/api/dispatch/status"),
      api("/api/dispatch/contracts"),
    ]);
    local.status = status;
    local.contracts = contracts;
    state.available = Boolean(status.available);
    renderSystemBanner(banner, status);

    for (const kind of ["orders", "fleet"]) {
      refs[kind] = createDropCard(
        kind,
        contracts.formats[kind],
      );
      grid.append(refs[kind].card);

      refs[kind].drop.onclick = () => refs[kind].file.click();
      refs[kind].file.onchange = () => {
        handleFile(kind, refs[kind].file.files?.[0]);
        refs[kind].file.value = "";
      };
      refs[kind].drop.ondragover = (event) => {
        event.preventDefault();
        refs[kind].drop.classList.add("is-dragging");
      };
      refs[kind].drop.ondragleave = () => {
        refs[kind].drop.classList.remove("is-dragging");
      };
      refs[kind].drop.ondrop = (event) => {
        event.preventDefault();
        refs[kind].drop.classList.remove("is-dragging");
        handleFile(kind, event.dataTransfer?.files?.[0]);
      };

      if (state[kind]?.profile_json) {
        local.reports[kind] = state[kind].profile_json;
      }
      updateCard(kind);
    }

    await Promise.all([
      loadLibrary("orders"),
      loadLibrary("fleet"),
    ]);
    updateCard("orders");
    updateCard("fleet");
    await refreshPreflight();
  } catch (error) {
    state.available = false;
    local.status = {
      available: false,
      checks: [],
      message: (
        "No pudimos consultar el estado del sistema. "
        + "Podés reintentar recargando la pantalla."
      ),
    };
    renderSystemBanner(banner, local.status);
    preflightRoot.replaceChildren(
      element("p", error.message, "dispatch-alert"),
    );
    updateFooter();
  }

  next.onclick = () => {
    if (!next.disabled) {
      onNext();
    }
  };
}
