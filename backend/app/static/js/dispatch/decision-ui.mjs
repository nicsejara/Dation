import "../dda-variable-config.js?v=assignment-config-v2";

export const DECISION_ORDER = [
  "logistics_assignment",
  "logistics_scheduling",
  "logistics_final_assignment",
];

export const DECISION_META = Object.freeze({
  logistics_assignment: Object.freeze({
    index: "01",
    label: "Asignación de carga",
    short: "Asignación de carga",
    progressLabel: "Asignación de carga",
    icon: "packageCheck",
    question: "¿Cómo conviene armar los viajes y repartir la carga?",
    output: "Viajes propuestos + distribución de carga",
    configureLabel: "Configurar asignación →",
    implemented: true,
  }),
  logistics_scheduling: Object.freeze({
    index: "02",
    label: "Planificación de despachos",
    short: "Planificación de despachos",
    progressLabel: "Planificación",
    icon: "calendarRange",
    question: "¿Cuándo conviene ejecutar los viajes ya definidos?",
    output: "Calendario operativo + secuencia",
    configureLabel: "Configurar planificación →",
    implemented: true,
  }),
  logistics_final_assignment: Object.freeze({
    index: "03",
    label: "Asignación de vehículos",
    short: "Asignación de vehículos",
    progressLabel: "Vehículos",
    icon: "truck",
    question: "¿Qué vehículo ejecuta cada viaje programado?",
    output: "Vehículo asignado a cada viaje, listo para ejecutar",
    configureLabel: "Configurar asignación de vehículos →",
    implemented: false,
  }),
});

export const STATUS_UI = Object.freeze({
  available: Object.freeze({label:"Disponible",icon:"playCircle",tone:"available",description:"La decisión puede configurarse ahora."}),
  running: Object.freeze({label:"Procesando",icon:"loader",tone:"running",description:"Dation está procesando esta decisión."}),
  review: Object.freeze({label:"Requiere revisión",icon:"alertTriangle",tone:"review",description:"El resultado está listo para revisar."}),
  approved: Object.freeze({label:"Aprobada",icon:"checkCircle",tone:"approved",description:"La decisión fue aprobada y queda registrada en el caso."}),
  locked: Object.freeze({label:"En espera",icon:"clock",tone:"waiting",description:"Se habilita cuando se cumple la dependencia anterior."}),
  needs_data: Object.freeze({label:"En espera",icon:"clock",tone:"waiting",description:"Necesita completar datos antes de continuar."}),
  error: Object.freeze({label:"Requiere revisión",icon:"alertTriangle",tone:"review",description:"La ejecución necesita revisión antes de continuar."}),
  stale: Object.freeze({label:"Requiere revisión",icon:"alertTriangle",tone:"review",description:"Los datos cambiaron y la decisión debe revisarse."}),
});

const ICONS = Object.freeze({
  packageCheck: '<path d="m16.5 9.4-9-5.2"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/><path d="m15.5 16 1.5 1.5 3-3"/>',
  calendarRange: '<path d="M8 2v4M16 2v4M3 10h18"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M7 15h4M13 18h4"/>',
  calendarClock: '<path d="M8 2v4M16 2v4M3 10h8"/><rect x="3" y="4" width="18" height="18" rx="2"/><circle cx="16" cy="16" r="4"/><path d="M16 14v2l1.5 1"/>',
  truck: '<path d="M10 17h4V5H2v12h3"/><path d="M14 9h4l4 4v4h-3"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="16.5" cy="17.5" r="2.5"/>',
  route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h5.5a3.5 3.5 0 0 0 0-7h-5a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  dollarSign: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  scale: '<path d="m16 16 3-8 3 8a5 5 0 0 1-6 0ZM2 16l3-8 3 8a5 5 0 0 1-6 0ZM7 21h10M12 3v18M3 7h18"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 18 2 18 2c1 5.5-.5 11.5-5 14.5"/><path d="M2 21c0-3 1.85-5.36 5.08-6.94C9.46 12.9 12 10 13 8"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  filter: '<path d="M4 5h16l-6 7v5l-4 2v-7Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  shuffle: '<path d="M16 3h5v5"/><path d="M4 20 21 3"/><path d="M21 16v5h-5"/><path d="m15 15 6 6"/><path d="M4 4l5 5"/>',
  handshake: '<path d="m11 17 2 2a2 2 0 0 0 3-3l-3-3"/><path d="m14 14 2.5 2.5a2 2 0 0 0 3-3L15 9"/><path d="M3 7l5-3 4 3-3 3a2 2 0 0 0 3 3l3-3"/><path d="m2 8 4 8 3-2M22 8l-4 8-2-1"/>',
  layoutDashboard: '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
  messageCircleQuestion: '<path d="M21 12a8 8 0 0 1-8 8H7l-4 2 1.4-4.2A8 8 0 1 1 21 12Z"/><path d="M9.6 9a2.5 2.5 0 0 1 4.8 1c0 1.8-2.4 2-2.4 3.5M12 17h.01"/>',
  slidersHorizontal: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/>',
  playCircle: '<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
  alertTriangle: '<path d="M12 3 2.5 20h19Z"/><path d="M12 9v4M12 17h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  loader: '<path d="M21 12a9 9 0 1 1-3-6.7"/>',
  folderOpen: '<path d="M3 19V6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v2"/><path d="m3 19 2.2-7h17.3l-2.2 7H3Z"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  clipboardList: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5M9 9h6M9 13h6M9 17h4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  refresh: '<path d="M20 7h-5V2"/><path d="M20 7a8 8 0 1 0 2 5"/>',
  clipboardCheck: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4.5V3h6v1.5"/><path d="m9 13 2 2 4-4"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  rotate: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  mousePointer: '<path d="m4 3 7 17 2-7 7-2Z"/><path d="m13 13 6 6"/>',
  sliders: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3"/><path d="M1 14h6M9 8h6M17 16h6"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m14 7 5 5-5 5"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  columns: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1"/>',
});

export function statusUi(status) {
  return STATUS_UI[status] || {
    label: "En espera",
    icon: "clock",
    tone: "waiting",
    description: "La decisión está esperando sus condiciones de habilitación.",
  };
}

export function iconSvg(name, className = "dispatch-map-icon") {
  return '<svg class="' + className + '" viewBox="0 0 24 24" aria-hidden="true">'
    + (ICONS[name] || ICONS.checkCircle)
    + '</svg>';
}
