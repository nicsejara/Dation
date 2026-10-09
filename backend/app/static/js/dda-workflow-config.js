(function () {
  var steps = [
    {
      id: "data",
      number: 1,
      label: "Carga de datos",
      view: "logistics-data"
    },
    {
      id: "map",
      number: 2,
      label: "Mapa de decisiones",
      view: "logistics-map"
    },
    {
      id: "config",
      number: 3,
      label: "Configurar decisión",
      view: "logistics-config"
    },
    {
      id: "dashboard",
      number: 4,
      label: "Dashboard",
      view: "decision-dashboard"
    }
  ].map(function (step) {
    return Object.freeze(step);
  });

  window.DationDdaFlow = Object.freeze({
    id: "logistics",
    label: "DDA Logística",
    steps: Object.freeze(steps)
  });

  // The decision-configuration layer is part of the DDA shell, not a
  // side effect of an individual screen. Dynamic import keeps this classic
  // bootstrap backward compatible while guaranteeing that Scheduling phases
  // 1–4 are loaded before the user reaches Configurar decisión.
  import("./dda-variable-config.js?v=scheduling-execution-phase4-v1")
    .catch(function (error) {
      console.error("No se pudo iniciar la configuración compartida de decisiones.", error);
    });
})();