export function createDropCard(kind, contract) {
  const card = document.createElement("section");
  card.className = "dispatch-panel dispatch-upload-card";
  card.dataset.kind = kind;

  const head = document.createElement("div");
  head.className = "dispatch-upload-card-head";

  const titleWrap = document.createElement("div");
  const eyebrow = document.createElement("span");
  eyebrow.className = "dispatch-kicker";
  eyebrow.textContent = kind === "orders" ? "1 · Datos variables" : "2 · Capacidad operativa";

  const title = document.createElement("h2");
  title.textContent = contract.label;

  const role = document.createElement("p");
  role.textContent = contract.role;
  titleWrap.append(eyebrow, title, role);

  const status = document.createElement("span");
  status.className = "dispatch-upload-status is-neutral";
  status.textContent = "Sin archivo";
  head.append(titleWrap, status);

  const drop = document.createElement("button");
  drop.type = "button";
  drop.className = "dispatch-upload-drop";
  drop.setAttribute("aria-label", `Elegir archivo CSV de ${contract.label}`);
  const dropStrong = document.createElement("strong");
  dropStrong.textContent = "Arrastrá el CSV acá o elegilo desde tu equipo";
  const dropSmall = document.createElement("small");
  dropSmall.textContent = "CSV UTF-8 · hasta 10 MB · se valida antes de guardarse";
  drop.append(dropStrong, dropSmall);

  const file = document.createElement("input");
  file.type = "file";
  file.accept = ".csv,text/csv";
  file.hidden = true;

  const actions = document.createElement("div");
  actions.className = "dispatch-upload-links";
  const template = document.createElement("a");
  template.href = `/api/dispatch/templates/${kind}`;
  template.download = `${kind}.csv`;
  template.textContent = "Descargar plantilla";
  const example = document.createElement("a");
  example.href = `/api/dispatch/examples/${kind}`;
  example.download = `${kind}_ejemplo.csv`;
  example.textContent = "Descargar ejemplo completo";
  actions.append(template, example);

  const details = document.createElement("details");
  details.className = "dispatch-contract-details";
  const summary = document.createElement("summary");
  summary.textContent = "Ver columnas y reglas";
  details.append(summary);

  const wrap = document.createElement("div");
  wrap.className = "dispatch-table-wrap";
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  thead.innerHTML = (
    "<tr><th>Columna</th><th>Obligatoria</th><th>Formato / regla</th>"
    + "<th>Ejemplo</th><th>Para qué sirve</th></tr>"
  );
  const tbody = document.createElement("tbody");
  for (const column of contract.columns) {
    const tr = document.createElement("tr");
    for (const value of [
      column.name,
      column.required ? "Sí" : "No",
      column.rule,
      column.example,
      column.description,
    ]) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.append(thead, tbody);
  wrap.append(table);
  details.append(wrap);

  const fields = document.createElement("div");
  fields.className = "dispatch-upload-fields";
  const label = document.createElement("label");
  label.textContent = kind === "orders" ? "Etiqueta opcional" : "Etiqueta de la versión";
  const labelInput = document.createElement("input");
  labelInput.placeholder = kind === "orders" ? "Semana 40" : "Flota octubre";
  label.append(labelInput);
  fields.append(label);

  let defaultInput = null;
  if (kind === "fleet") {
    const defaultLabel = document.createElement("label");
    defaultLabel.className = "dispatch-check-label";
    defaultInput = document.createElement("input");
    defaultInput.type = "checkbox";
    defaultInput.checked = true;
    defaultLabel.append(
      defaultInput,
      document.createTextNode(" Usarla como flota vigente"),
    );
    fields.append(defaultLabel);
  }

  const profile = document.createElement("div");
  profile.className = "dispatch-upload-profile";

  const report = document.createElement("div");
  report.className = "dispatch-validation-report";
  report.setAttribute("aria-live", "polite");

  const library = document.createElement("div");
  library.className = "dispatch-library";

  card.append(
    head,
    drop,
    file,
    actions,
    details,
    fields,
    report,
    profile,
    library,
  );

  return {
    card,
    status,
    drop,
    file,
    labelInput,
    defaultInput,
    report,
    profile,
    library,
  };
}
