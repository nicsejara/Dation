const TECHNICAL_PREFLIGHT_CODES = new Set([
  "UNKNOWN_CURRENT_VEHICLE",
  "PREFLIGHT_REQUEST_FAILED",
]);

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
        title: item.message || item.detail || "Problema de validación",
        items: [],
      });
    }
    groups.get(key).items.push(item);
  }
  return [...groups.values()];
}

export function technicalPreflightErrors(preflight) {
  if (!preflight) {
    return [];
  }
  return (preflight.errors || []).filter(
    (item) => TECHNICAL_PREFLIGHT_CODES.has(item.code),
  );
}

export function deriveCardState({
  report = null,
  dataset = null,
  saveError = null,
  phase = "idle",
  storageAvailable = true,
  duplicate = false,
} = {}) {
  if (phase === "uploading") {
    return {
      key: "uploading",
      label: "Subiendo archivo…",
      tone: "pending",
    };
  }

  if (phase === "processing") {
    return {
      key: "processing",
      label: "Validando estructura…",
      tone: "pending",
    };
  }

  if (saveError) {
    return {
      key: "save_error",
      label: "⛔ No se pudo guardar",
      tone: "error",
    };
  }

  if (report?.detected_format === "legacy_mixed") {
    return {
      key: "legacy",
      label: "⛔ Archivo equivocado",
      tone: "error",
    };
  }

  const errors = Number(report?.counts?.errors || 0);
  const warnings = Number(report?.counts?.warnings || 0);

  if (errors > 0) {
    return {
      key: "error",
      label: (
        `⛔ ${errors} ${errors === 1 ? "problema" : "problemas"}`
      ),
      tone: "error",
    };
  }

  if (report?.valid && !dataset && !storageAvailable) {
    return {
      key: "valid_not_saved",
      label: "✓ Archivo válido · sin guardar",
      tone: "warning",
    };
  }

  if (duplicate && dataset) {
    return {
      key: "duplicate",
      label: "✓ Archivo válido",
      tone: "success",
    };
  }

  if (report?.valid || dataset) {
    if (warnings > 0) {
      return {
        key: "warning",
        label: (
          `⚠ Archivo válido con ${warnings} `
          + `${warnings === 1 ? "observación" : "observaciones"}`
        ),
        tone: "warning",
      };
    }
    return {
      key: "valid",
      label: "✓ Archivo correcto",
      tone: "success",
    };
  }

  return {
    key: "empty",
    label: "Pendiente de carga",
    tone: "neutral",
  };
}

export function continueState({
  storageAvailable,
  orders,
  fleet,
  reports = {},
  preflight,
  phases = {},
  saveErrors = {},
} = {}) {
  if (!storageAvailable) {
    return {
      enabled: false,
      message: "Falta activar el almacenamiento de datos.",
      kind: "pending",
    };
  }

  if (phases.orders !== "idle" || phases.fleet !== "idle") {
    return {
      enabled: false,
      message: "Esperá a que termine la validación de los archivos.",
      kind: "pending",
    };
  }

  if (saveErrors.orders || saveErrors.fleet) {
    return {
      enabled: false,
      message: "Hay un archivo válido que todavía no pudo guardarse.",
      kind: "error",
    };
  }

  if (!orders) {
    const errors = Number(reports.orders?.counts?.errors || 0);
    return {
      enabled: false,
      message: errors
        ? "Corregí los problemas del archivo de órdenes."
        : "Falta cargar el archivo de órdenes.",
      kind: errors ? "error" : "pending",
    };
  }

  if (!fleet) {
    const errors = Number(reports.fleet?.counts?.errors || 0);
    return {
      enabled: false,
      message: errors
        ? "Corregí los problemas del archivo de flota."
        : "Falta cargar el archivo de flota.",
      kind: errors ? "error" : "pending",
    };
  }

  if (!reports.orders?.valid || !reports.fleet?.valid) {
    return {
      enabled: false,
      message: "Ambos archivos deben superar la validación técnica.",
      kind: "error",
    };
  }

  if (!preflight) {
    return {
      enabled: false,
      message: "Comprobando la compatibilidad mínima entre ambos archivos.",
      kind: "pending",
    };
  }

  const relationErrors = technicalPreflightErrors(preflight);
  if (relationErrors.length) {
    return {
      enabled: false,
      message: "Hay referencias entre los archivos que necesitás corregir.",
      kind: "error",
    };
  }

  return {
    enabled: true,
    message: "Los dos archivos superaron las validaciones necesarias.",
    kind: "success",
  };
}
