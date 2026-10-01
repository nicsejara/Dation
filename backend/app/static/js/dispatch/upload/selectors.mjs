export function groupProblems(report) {
  const items = [
    ...(report?.errors || []).map((item) => ({...item, severity: "error"})),
    ...(report?.warnings || []).map((item) => ({...item, severity: "warning"})),
  ];

  const groups = new Map();
  for (const item of items) {
    const key = item.code || "UNKNOWN";
    if (!groups.has(key)) {
      groups.set(key, {
        code: key,
        severity: item.severity,
        title: item.message || "Problema de validación",
        items: [],
      });
    }
    groups.get(key).items.push(item);
  }
  return [...groups.values()];
}

export function cardState({
  validating = false,
  report = null,
  dataset = null,
  saveError = null,
  storageAvailable = true,
} = {}) {
  if (validating) {
    return {
      key: "validando",
      label: "Validando…",
      tone: "pending",
    };
  }
  if (saveError) {
    return {
      key: "error_de_guardado",
      label: "Error al guardar",
      tone: "error",
    };
  }
  if (dataset) {
    const warnings = Number(report?.counts?.warnings || 0);
    return {
      key: warnings ? "con_advertencias" : "valido",
      label: warnings ? "Guardado con advertencias" : "Guardado y válido",
      tone: warnings ? "warning" : "success",
    };
  }
  if (report?.valid && !storageAvailable) {
    return {
      key: "guardado_pendiente",
      label: "Válido, aún no guardado",
      tone: "warning",
    };
  }
  if (report?.valid) {
    return {
      key: Number(report?.counts?.warnings || 0)
        ? "con_advertencias"
        : "valido",
      label: Number(report?.counts?.warnings || 0)
        ? "Válido con advertencias"
        : "Válido",
      tone: Number(report?.counts?.warnings || 0)
        ? "warning"
        : "success",
    };
  }
  if (report && !report.valid) {
    return {
      key: "invalido",
      label: "Hay errores",
      tone: "error",
    };
  }
  return {
    key: "sin_archivo",
    label: "Sin archivo",
    tone: "neutral",
  };
}

export function continueState({
  storageAvailable,
  orders,
  fleet,
  reports = {},
  preflight,
} = {}) {
  if (!storageAvailable) {
    return {
      enabled: false,
      message: "Falta activar el almacenamiento de Dispatch.",
    };
  }
  if (!orders) {
    if (reports.orders && !reports.orders.valid) {
      return {
        enabled: false,
        message: "Hay errores en las órdenes.",
      };
    }
    return {
      enabled: false,
      message: "Falta cargar o elegir las órdenes.",
    };
  }
  if (!fleet) {
    if (reports.fleet && !reports.fleet.valid) {
      return {
        enabled: false,
        message: "Hay errores en la flota.",
      };
    }
    return {
      enabled: false,
      message: "Falta cargar o elegir la flota.",
    };
  }
  if (!preflight) {
    return {
      enabled: false,
      message: "Estamos revisando la compatibilidad entre ambos archivos.",
    };
  }
  if (!preflight.valid) {
    return {
      enabled: false,
      message: "La revisión conjunta detectó errores que impiden continuar.",
    };
  }
  return {
    enabled: true,
    message: "Datos listos para configurar la decisión.",
  };
}

const PREFLIGHT_LABELS = {
  FINITE_FLEET: "Disponibilidad diaria limitada",
  UNKNOWN_CURRENT_VEHICLE: "Camión de referencia no encontrado",
  UNIT_EXCEEDS_CAPACITY: "Unidad sin capacidad disponible",
  UNAVOIDABLE_LATE: "Plazo no alcanzable",
  MANY_TRIPS: "Orden con muchos viajes",
  ORDER_WEIGHT_OUTLIER: "Peso de orden atípico",
};

export function preflightTitle(item) {
  return PREFLIGHT_LABELS[item?.code] || "Chequeo operativo";
}
