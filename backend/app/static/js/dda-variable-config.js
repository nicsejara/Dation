import "./dispatch/assignment-filter-collapse.mjs?v=scope-filter-collapse-v1";
import "./dispatch/scheduling-config-v2.mjs?v=scheduling-rule-editor-phase3-v1";
import "./dispatch/scheduling-execution-phase4.mjs?v=scheduling-execution-phase4-v1";

(function(){
  "use strict";

  var variables={
    trips:Object.freeze({
      id:"trips",
      label:"Viajes",
      status:"active",
      description:"Cantidad de viajes necesarios para entregar todo."
    }),
    cost:Object.freeze({
      id:"cost",
      label:"Costo",
      status:"active",
      description:"Costo total de los viajes según tu flota."
    }),
    own_fleet:Object.freeze({
      id:"own_fleet",
      label:"Flota propia",
      status:"active",
      description:"Uso de vehículos propios frente a recursos tercerizados."
    }),
    co2:Object.freeze({
      id:"co2",
      label:"CO₂",
      status:"consolidating",
      description:"Hoy se informa como estimación; todavía no se ofrece como criterio activo."
    }),
    time:Object.freeze({
      id:"time",
      label:"Tiempo",
      status:"active",
      description:"Plazo total hasta completar las entregas."
    }),
    risk:Object.freeze({
      id:"risk",
      label:"Riesgo",
      status:"consolidating",
      description:"Se suma a medida que se consolide el modelo."
    }),
    service:Object.freeze({
      id:"service",
      label:"Servicio",
      status:"consolidating",
      description:"Se suma a medida que se consolide el modelo."
    })
  };

  window.DationDecisionVariables=Object.freeze(variables);
})();