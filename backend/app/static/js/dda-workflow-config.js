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
})();
