export function groupProblems(report) {
  const items = [
    ...(report?.errors || []).map((item) => ({
      ...item,
      severity: "error",
    })),
    ...(report?.warnings || []).map((item) => ({
      ...item,
      severity: "warning",
    })),
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

export function deriveCardState({
  validation = null,
  saved = null,
  error = null,
  dirty = false,
  validating = false,
  storageAvailable = true,
  duplicate = false,
} = {}) {
  if (validating) {
    return {
      key: "validando",
      label: "Validando…",
      tone: "pending",
      message: "Leyendo y revisando el archivo.",
    };
  }

  if (error) {
    return {
      key: "error_de_guardado",
      label: "⛔ No se pudo guardar",
      tone: "error",
      message: "El archivo es válido, pero no se pudo guardar. Reintentá.",
    };
  }

  if (validation?.detected_format === "legacy_mixed") {
    return {
      key: "formato_anterior",
      label: "⛔ Formato anterior",
      tone: "error",
      message: "Separalo en órdenes y flota con las plantillas nuevas.",
    };
  }

  if (Number(validation?.counts?.errors || 0) > 0) {
    return {
      key: "invalido",
      label: "⛔ Con errores",
      tone: "error",
      message: "No se guardó. Corregí los errores y volvé a cargarlo.",
    };
  }

  if (duplicate && saved) {
    return {
      key: "reutilizado",
      label: "✓ Ya cargado",
      tone: "success",
      message: "Usamos la versión que ya estaba guardada.",
    };
  }

  if (validation?.valid && !saved && !storageAvailable) {
    return {
      key: "valido_sin_guardar",
      label: "✓ Válido · ⏳ Sin guardar",
      tone: "warning",
      message: "Falta activar el almacenamiento.",
    };
  }

  if (saved) {
    const warnings = Number(validation?.counts?.warnings || 0);
    return warnings
      ? {
        key: "con_avisos",
        label: "⚠ Guardado con avisos",
        tone: "warning",
        message: "Guardado. Revisá los avisos.",
      }
      : {
        key: dirty ? "editado" : "valido",
        label: "✓ Guardado y válido",
        tone: "success",
        message: "Listo.",
      };
  }

  if (validation?.valid) {
    return {
      key: "valido",
      label: "✓ Válido",
      tone: "success",
      message: "Listo para guardar.",
    };
  }

  return {
    key: "sin_archivo",
    label: "○ Sin archivo",
    tone: "neutral",
    message: null,
  };
}

export const cardState = deriveCardState;

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
      message: "Falta activar el almacenamiento de datos.",
    };
  }

  if (!orders) {
    if (Number(reports.orders?.counts?.errors || 0) > 0) {
      return {
        enabled: false,
        message: "Corregí los errores de las órdenes.",
      };
    }
    return {
      enabled: false,
      message: "Falta cargar las órdenes.",
    };
  }

  if (!fleet) {
    if (Number(reports.fleet?.counts?.errors || 0) > 0) {
      return {
        enabled: false,
        message: "Corregí los errores de la flota.",
      };
    }
    return {
      enabled: false,
      message: "Falta cargar la flota.",
    };
  }

  if (!preflight) {
    return {
      enabled: false,
      message: "Estamos revisando la compatibilidad entre ambos archivos.",
    };
  }

  const blockers = preflight.readiness?.blockers || [];
  if (!preflight.valid || blockers.length) {
    return {
      enabled: false,
      message: preflight.readiness?.reason
        || "La revisión conjunta detectó errores que impiden continuar.",
    };
  }

  const warnings = (preflight.findings || []).filter(
    (item) => item.severity === "warning",
  ).length;
  return {
    enabled: true,
    message: warnings
      ? `${warnings} avisos: podés continuar.`
      : "Todo listo para continuar.",
  };
}

export function stepTone({
  dataset,
  report,
  preflight,
  kind,
} = {}) {
  if (kind === "review") {
    if (!preflight) {
      return "pending";
    }
    if (!preflight.valid) {
      return "error";
    }
    return (preflight.findings || []).some(
      (item) => item.severity === "warning",
    )
      ? "warning"
      : "success";
  }

  if (Number(report?.counts?.errors || 0) > 0) {
    return "error";
  }
  if (!dataset) {
    return "pending";
  }
  return Number(report?.counts?.warnings || 0) > 0
    ? "warning"
    : "success";
}
