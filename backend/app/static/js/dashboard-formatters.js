(function (root, factory) {
  var api = factory();

  if (
    typeof module === "object"
    && module.exports
  ) {
    module.exports = api;
  }

  root.DationDashboardFormatters = api;
})(
  typeof window !== "undefined"
    ? window
    : globalThis,
  function () {
    "use strict";

    var SCENARIO_LABELS = {
      baseline: "Asignación actual",
      min_cost: "Costo mínimo",
      min_trips: "Viajes mínimos",
      custom: "Objetivo personalizado"
    };

    var OBJECTIVE_LABELS = {
      min_cost: "Minimizar costo total",
      min_trips: "Minimizar cantidad de viajes",
      custom: "Objetivo personalizado"
    };

    function finite(value) {
      if (
        value === null
        || value === undefined
        || value === ""
      ) {
        return null;
      }

      var number = Number(value);

      return Number.isFinite(number)
        ? number
        : null;
    }

    function formatNumber(
      value,
      digits
    ) {
      var number = finite(value);

      if (number === null) {
        return "—";
      }

      var maxDigits = (
        digits === undefined
          ? 0
          : Number(digits)
      );

      return new Intl.NumberFormat(
        "es-AR",
        {
          minimumFractionDigits: 0,
          maximumFractionDigits: (
            Number.isFinite(maxDigits)
              ? maxDigits
              : 0
          )
        }
      ).format(number);
    }

    function formatCurrency(value) {
      var number = finite(value);

      if (number === null) {
        return "—";
      }

      return (
        "$ "
        + formatNumber(
          Math.round(number),
          0
        )
      );
    }

    function formatCurrencyCompact(
      value
    ) {
      var number = finite(value);

      if (number === null) {
        return "—";
      }

      var absolute = Math.abs(number);
      var sign = number < 0 ? "−" : "";

      if (absolute >= 1000000) {
        return (
          sign
          + "$ "
          + formatNumber(
              absolute / 1000000,
              1
            )
          + " M"
        );
      }

      if (absolute >= 1000) {
        return (
          sign
          + "$ "
          + formatNumber(
              absolute / 1000,
              1
            )
          + " mil"
        );
      }

      return (
        sign
        + "$ "
        + formatNumber(
            absolute,
            0
          )
      );
    }

    function formatPercent(
      value,
      options
    ) {
      var number = finite(value);

      if (number === null) {
        return "—";
      }

      options = options || {};

      var signed = (
        options.signed !== false
      );

      var prefix = "";

      if (signed && number > 0) {
        prefix = "+";
      }

      if (number < 0) {
        prefix = "−";
      }

      return (
        prefix
        + formatNumber(
            Math.abs(number),
            (
              options.digits === undefined
                ? 1
                : options.digits
            )
          )
        + " %"
      );
    }

    function formatKm(
      value,
      digits
    ) {
      var number = finite(value);

      if (number === null) {
        return "—";
      }

      return (
        formatNumber(
          number,
          digits === undefined
            ? 0
            : digits
        )
        + " km"
      );
    }

    function cleanMonth(value) {
      return String(value || "")
        .replace(".", "")
        .toLowerCase();
    }

    function formatDate(value) {
      if (!value) {
        return "—";
      }

      var parsed = new Date(value);

      if (
        Number.isNaN(
          parsed.getTime()
        )
      ) {
        return String(value);
      }

      var date = new Intl.DateTimeFormat(
        "es-AR",
        {
          day: "2-digit",
          month: "short",
          year: "numeric"
        }
      )
        .format(parsed)
        .replace(/\./g, "");

      var time = new Intl.DateTimeFormat(
        "es-AR",
        {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false
        }
      ).format(parsed);

      return date + ", " + time;
    }

    function parseDateOnly(value) {
      if (!value) {
        return null;
      }

      var parsed = new Date(
        String(value).length <= 10
          ? String(value) + "T00:00:00"
          : value
      );

      return Number.isNaN(
        parsed.getTime()
      )
        ? null
        : parsed;
    }

    function formatDateRange(
      start,
      end
    ) {
      var from = parseDateOnly(start);
      var to = parseDateOnly(end);

      if (!from && !to) {
        return "—";
      }

      if (!from || !to) {
        return (
          formatDate(
            from || to
          ).split(",")[0]
        );
      }

      var startDay = from.getDate();
      var endDay = to.getDate();

      var startMonth = cleanMonth(
        new Intl.DateTimeFormat(
          "es-AR",
          {
            month: "short"
          }
        ).format(from)
      );

      var endMonth = cleanMonth(
        new Intl.DateTimeFormat(
          "es-AR",
          {
            month: "short"
          }
        ).format(to)
      );

      var startYear = from.getFullYear();
      var endYear = to.getFullYear();

      if (
        startMonth === endMonth
        && startYear === endYear
      ) {
        return (
          startDay
          + "–"
          + endDay
          + " "
          + endMonth
          + " "
          + endYear
        );
      }

      if (startYear === endYear) {
        return (
          startDay
          + " "
          + startMonth
          + " – "
          + endDay
          + " "
          + endMonth
          + " "
          + endYear
        );
      }

      return (
        startDay
        + " "
        + startMonth
        + " "
        + startYear
        + " – "
        + endDay
        + " "
        + endMonth
        + " "
        + endYear
      );
    }

    function normalizeVehicleCode(
      value
    ) {
      return String(value || "")
        .trim()
        .toUpperCase()
        .replace(/[\s-]+/g, "_")
        .replace(/^TRUCK_?/, "TRUCK_");
    }

    function vehicleLabel(value) {
      var normalized = (
        normalizeVehicleCode(value)
      );

      var suffix = (
        normalized
          .replace(/^TRUCK_?/, "")
          .replace(/^CAMI[ÓO]N_?/, "")
      );

      if (
        suffix === "S"
        || suffix === "M"
        || suffix === "L"
      ) {
        return "Camión " + suffix;
      }

      return String(value || "—")
        .replaceAll("_", " ");
    }

    function scenarioLabel(value) {
      return (
        SCENARIO_LABELS[value]
        || String(value || "—")
          .replaceAll("_", " ")
      );
    }

    function objectiveLabel(config) {
      var objective = (
        config
        && config.mode === "custom"
          ? "custom"
          : config
            && config.objective
      );

      return (
        OBJECTIVE_LABELS[objective]
        || "Objetivo no informado"
      );
    }

    function weightLabel(config) {
      var weights = (
        config
        && config.weights
        || {}
      );

      var cost = finite(weights.cost);
      var trips = finite(weights.trips);

      if (
        cost === null
        || trips === null
      ) {
        return "—";
      }

      return (
        formatNumber(cost * 100, 0)
        + " % costo · "
        + formatNumber(trips * 100, 0)
        + " % viajes"
      );
    }

    function normalizeBusinessText(
      value
    ) {
      if (!value) {
        return "";
      }

      var text = String(value);

      text = text
        .replace(/\bTRUCK[_\s-]?S\b/gi, "Camión S")
        .replace(/\bTRUCK[_\s-]?M\b/gi, "Camión M")
        .replace(/\bTRUCK[_\s-]?L\b/gi, "Camión L")
        .replace(/\bTruck\s*_S\b/g, "Camión S")
        .replace(/\bTruck\s*_M\b/g, "Camión M")
        .replace(/\bTruck\s*_L\b/g, "Camión L")
        .replace(/\bmin_cost\b/g, "Costo mínimo")
        .replace(/\bmin_trips\b/g, "Viajes mínimos")
        .replace(/\bbaseline\b/gi, "Asignación actual")
        .replace(/\bsituación actual\b/gi, "Asignación actual")
        .replace(
          /(-?\d+)\.(\d+)\s*%/g,
          function (_, integer, decimals) {
            var sign = (
              integer.startsWith("-")
                ? "−"
                : ""
            );

            return (
              sign
              + integer.replace("-", "")
              + ","
              + decimals
              + " %"
            );
          }
        );

      return text;
    }

    return {
      SCENARIO_LABELS: SCENARIO_LABELS,
      OBJECTIVE_LABELS: OBJECTIVE_LABELS,
      finite: finite,
      formatNumber: formatNumber,
      formatCurrency: formatCurrency,
      formatCurrencyCompact: (
        formatCurrencyCompact
      ),
      formatPercent: formatPercent,
      formatKm: formatKm,
      formatDate: formatDate,
      formatDateRange: formatDateRange,
      vehicleLabel: vehicleLabel,
      scenarioLabel: scenarioLabel,
      objectiveLabel: objectiveLabel,
      weightLabel: weightLabel,
      normalizeBusinessText: (
        normalizeBusinessText
      )
    };
  }
);
