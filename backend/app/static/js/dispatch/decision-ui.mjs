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
    icon: "truck",
    question: "¿Qué vehículo ejecuta cada viaje programado?",
    output: "Vehículo asignado a cada viaje, listo para ejecutar",
    configureLabel: "Configurar asignación de vehículos →",
    implemented: false,
  }),
});

export const STATUS_UI = Object.freeze({
  available: Object.freeze({
    label: "Disponible",
    icon: "playCircle",
    tone: "available",
  }),
  running: Object.freeze({
    label: "Procesando",
    icon: "loader",
    tone: "running",
  }),
  review: Object.freeze({
    label: "Requiere revisión",
    icon: "alertTriangle",
    tone: "review",
  }),
  approved: Object.freeze({
    label: "Aprobada",
    icon: "checkCircle",
    tone: "approved",
  }),
  locked: Object.freeze({
    label: "En espera",
    icon: "clock",
    tone: "waiting",
  }),
  needs_data: Object.freeze({
    label: "En espera",
    icon: "clock",
    tone: "waiting",
  }),
  error: Object.freeze({
    label: "Requiere revisión",
    icon: "alertTriangle",
    tone: "review",
  }),
  stale: Object.freeze({
    label: "Requiere revisión",
    icon: "alertTriangle",
    tone: "review",
  }),
});

const ICONS = Object.freeze({
  packageCheck: '<path d="m16.5 9.4-9-5.2"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="M3.3 7 12 12l8.7-5"/><path d="M12 22V12"/><path d="m15.5 16 1.5 1.5 3-3"/>',
  calendarRange: '<path d="M8 2v4M16 2v4M3 10h18"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M7 15h4M13 18h4"/>',
  truck: '<path d="M10 17h4V5H2v12h3"/><path d="M14 9h4l4 4v4h-3"/><circle cx="7.5" cy="17.5" r="2.5"/><circle cx="16.5" cy="17.5" r="2.5"/>',
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
});

export function statusUi(status) {
  return STATUS_UI[status] || {
    label: "En espera",
    icon: "clock",
    tone: "waiting",
  };
}

export function iconSvg(name, className = "dispatch-map-icon") {
  return '<svg class="' + className + '" viewBox="0 0 24 24" aria-hidden="true">'
    + (ICONS[name] || ICONS.checkCircle)
    + '</svg>';
}
