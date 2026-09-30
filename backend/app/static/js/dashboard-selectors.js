(function (root, factory) {
  var api = factory();

  if (
    typeof module === "object"
    && module.exports
  ) {
    module.exports = api;
  }

  root.DationDashboardSelectors = api;
})(
  typeof window !== "undefined"
    ? window
    : globalThis,
  function () {
    "use strict";

    function assignments(
      scenario
    ) {
      return (
        scenario
        && Array.isArray(
          scenario.assignments
        )
          ? scenario.assignments
          : []
      );
    }

    function assignmentMap(
      scenario
    ) {
      var map = new Map();

      assignments(
        scenario
      ).forEach(function (item) {
        map.set(
          item.shipment_id,
          item
        );
      });

      return map;
    }

    function selectedScenario(
      run
    ) {
      var result = (
        run
        && run.result_json
      );

      if (
        !result
        || !result.scenarios
      ) {
        return null;
      }

      return (
        result.scenarios[
          result.recommended_scenario
        ]
        || null
      );
    }

    function currentScenario(
      run
    ) {
      return (
        run
        && run.result_json
        && run.result_json.scenarios
        && run.result_json.scenarios.baseline
      )
      || null;
    }

    function assignmentDifferenceCount(
      first,
      second
    ) {
      var left = assignmentMap(first);
      var right = assignmentMap(second);
      var ids = new Set(
        Array.from(left.keys())
          .concat(
            Array.from(
              right.keys()
            )
          )
      );

      var count = 0;

      ids.forEach(function (id) {
        var a = left.get(id);
        var b = right.get(id);

        if (
          (
            a
            && a.vehicle_type
          )
          !== (
            b
            && b.vehicle_type
          )
        ) {
          count += 1;
        }
      });

      return count;
    }

    function scenariosEquivalent(
      first,
      second
    ) {
      var a = assignments(first);
      var b = assignments(second);

      if (a.length !== b.length) {
        return false;
      }

      return (
        assignmentDifferenceCount(
          first,
          second
        ) === 0
      );
    }

    function vehicleCatalogMap(
      result
    ) {
      var map = new Map();

      (
        result
        && Array.isArray(
          result.vehicle_catalog
        )
          ? result.vehicle_catalog
          : []
      ).forEach(function (vehicle) {
        map.set(
          vehicle.vehicle_type,
          vehicle
        );
      });

      return map;
    }

    function assignmentDistribution(
      scenario
    ) {
      var map = new Map();

      assignments(
        scenario
      ).forEach(function (item) {
        var key = (
          item.vehicle_type
          || "Sin vehículo"
        );

        var current = (
          map.get(key)
          || {
            vehicle_type: key,
            shipments: 0,
            trips: 0,
            units: 0,
            weight_kg: 0
          }
        );

        current.shipments += 1;
        current.trips += Number(
          item.required_trips || 0
        );
        current.units += Number(
          item.quantity_units || 0
        );
        current.weight_kg += Number(
          item.total_weight_kg || 0
        );

        map.set(
          key,
          current
        );
      });

      return Array.from(
        map.values()
      ).sort(function (a, b) {
        return (
          String(a.vehicle_type)
            .localeCompare(
              String(b.vehicle_type)
            )
        );
      });
    }

    function savings(
      current,
      selected
    ) {
      var currentMetrics = (
        current
        && current.metrics
        || {}
      );

      var selectedMetrics = (
        selected
        && selected.metrics
        || {}
      );

      function delta(
        currentValue,
        selectedValue
      ) {
        var base = Number(
          currentValue
        );
        var next = Number(
          selectedValue
        );

        if (
          !Number.isFinite(base)
          || !Number.isFinite(next)
        ) {
          return {
            absolute: null,
            pct: null
          };
        }

        return {
          absolute: (
            base - next
          ),
          pct: (
            base === 0
              ? null
              : (
                (
                  base - next
                )
                / base
              ) * 100
          )
        };
      }

      return {
        cost: delta(
          currentMetrics.total_cost,
          selectedMetrics.total_cost
        ),
        trips: delta(
          currentMetrics.total_trips,
          selectedMetrics.total_trips
        ),
        distance: delta(
          currentMetrics
            .total_distance_km,
          selectedMetrics
            .total_distance_km
        )
      };
    }

    function kpis(
      current,
      selected
    ) {
      var gain = savings(
        current,
        selected
      );

      return [
        {
          key: "cost",
          label: "Costo total",
          current: (
            current
            && current.metrics
            && current.metrics.total_cost
          ),
          decision: (
            selected
            && selected.metrics
            && selected.metrics.total_cost
          ),
          absolute: (
            gain.cost.absolute
          ),
          pct: gain.cost.pct
        },
        {
          key: "trips",
          label: "Viajes",
          current: (
            current
            && current.metrics
            && current.metrics.total_trips
          ),
          decision: (
            selected
            && selected.metrics
            && selected.metrics.total_trips
          ),
          absolute: (
            gain.trips.absolute
          ),
          pct: gain.trips.pct
        },
        {
          key: "distance",
          label: "Distancia total",
          current: (
            current
            && current.metrics
            && current.metrics
              .total_distance_km
          ),
          decision: (
            selected
            && selected.metrics
            && selected.metrics
              .total_distance_km
          ),
          absolute: (
            gain.distance.absolute
          ),
          pct: gain.distance.pct
        },
        {
          key: "reassigned",
          label: "Despachos reasignados",
          current: 0,
          decision: (
            assignmentDifferenceCount(
              current,
              selected
            )
          ),
          absolute: (
            assignmentDifferenceCount(
              current,
              selected
            )
          ),
          pct: (
            selected
            && selected.metrics
            && Number(
              selected.metrics.shipments
            )
              ? (
                assignmentDifferenceCount(
                  current,
                  selected
                )
                / Number(
                  selected.metrics
                    .shipments
                )
              ) * 100
              : null
          )
        }
      ];
    }

    function reassignmentDetails(
      current,
      selected,
      result
    ) {
      var base = assignmentMap(
        current
      );
      var catalog = (
        vehicleCatalogMap(
          result
        )
      );

      return assignments(
        selected
      )
        .map(function (item) {
          var previous = (
            base.get(
              item.shipment_id
            )
          );

          if (
            !previous
            || previous.vehicle_type
              === item.vehicle_type
          ) {
            return null;
          }

          var previousVehicle = (
            catalog.get(
              previous.vehicle_type
            )
            || {}
          );

          var nextVehicle = (
            catalog.get(
              item.vehicle_type
            )
            || {}
          );

          return {
            shipment_id: (
              item.shipment_id
            ),
            product: item.product,
            origin: item.origin,
            destination: (
              item.destination
            ),
            from_vehicle: (
              previous.vehicle_type
            ),
            to_vehicle: (
              item.vehicle_type
            ),
            from_capacity_kg: Number(
              previousVehicle.capacity_kg
              || previousVehicle
                .vehicle_capacity_kg
              || 0
            ),
            to_capacity_kg: Number(
              nextVehicle.capacity_kg
              || nextVehicle
                .vehicle_capacity_kg
              || 0
            ),
            current_trips: Number(
              previous.required_trips
              || 0
            ),
            decision_trips: Number(
              item.required_trips || 0
            ),
            trips_avoided: (
              Number(
                previous.required_trips
                || 0
              )
              - Number(
                item.required_trips
                || 0
              )
            ),
            current_cost: Number(
              previous.total_cost || 0
            ),
            decision_cost: Number(
              item.total_cost || 0
            ),
            cost_saving: (
              Number(
                previous.total_cost
                || 0
              )
              - Number(
                item.total_cost
                || 0
              )
            ),
            units: Number(
              item.quantity_units || 0
            )
          };
        })
        .filter(Boolean);
    }

    function reassignmentMatrix(
      current,
      selected,
      result
    ) {
      var map = new Map();

      reassignmentDetails(
        current,
        selected,
        result
      ).forEach(function (item) {
        var key = (
          item.from_vehicle
          + "→"
          + item.to_vehicle
        );

        var row = (
          map.get(key)
          || {
            from_vehicle: (
              item.from_vehicle
            ),
            to_vehicle: (
              item.to_vehicle
            ),
            shipments: 0,
            trips_avoided: 0,
            cost_saving: 0
          }
        );

        row.shipments += 1;
        row.trips_avoided += (
          item.trips_avoided
        );
        row.cost_saving += (
          item.cost_saving
        );

        map.set(
          key,
          row
        );
      });

      return Array.from(
        map.values()
      ).sort(function (a, b) {
        return (
          b.shipments
          - a.shipments
        );
      });
    }

    function corridorGroups(
      current,
      selected,
      result
    ) {
      var map = new Map();

      reassignmentDetails(
        current,
        selected,
        result
      ).forEach(function (item) {
        var key = (
          item.origin
          + " → "
          + item.destination
        );

        var row = (
          map.get(key)
          || {
            corridor: key,
            origin: item.origin,
            destination: (
              item.destination
            ),
            shipments: 0,
            trips_avoided: 0,
            cost_saving: 0,
            transitions: {}
          }
        );

        var transition = (
          item.from_vehicle
          + "→"
          + item.to_vehicle
        );

        row.shipments += 1;
        row.trips_avoided += (
          item.trips_avoided
        );
        row.cost_saving += (
          item.cost_saving
        );
        row.transitions[
          transition
        ] = (
          row.transitions[
            transition
          ]
          || 0
        ) + 1;

        map.set(key, row);
      });

      return Array.from(
        map.values()
      )
        .map(function (row) {
          var entries = Object.entries(
            row.transitions
          ).sort(function (a, b) {
            return b[1] - a[1];
          });

          return Object.assign(
            {},
            row,
            {
              dominant_transition: (
                entries.length
                  ? entries[0][0]
                  : "—"
              )
            }
          );
        })
        .sort(function (a, b) {
          return (
            Math.abs(
              b.cost_saving
            )
            - Math.abs(
              a.cost_saving
            )
          );
        });
    }

    function chooseDefaultReference(
      result
    ) {
      if (
        !result
        || !result.scenarios
      ) {
        return "baseline";
      }

      var selected = (
        result.scenarios[
          result.recommended_scenario
        ]
      );

      var baseline = (
        result.scenarios.baseline
      );

      if (
        baseline
        && !scenariosEquivalent(
          selected,
          baseline
        )
      ) {
        return "baseline";
      }

      var candidates = [
        "min_cost",
        "min_trips"
      ];

      for (
        var index = 0;
        index < candidates.length;
        index += 1
      ) {
        var key = candidates[index];
        var scenario = (
          result.scenarios[key]
        );

        if (
          scenario
          && !scenariosEquivalent(
            selected,
            scenario
          )
        ) {
          return key;
        }
      }

      return "baseline";
    }

    function sensitivitySummary(
      result
    ) {
      if (
        !result
        || !result.scenarios
      ) {
        return {
          robust: false,
          available: []
        };
      }

      var selected = (
        result.scenarios[
          result.recommended_scenario
        ]
      );

      var minCost = (
        result.scenarios.min_cost
      );

      var minTrips = (
        result.scenarios.min_trips
      );

      var costSame = (
        Boolean(minCost)
        && scenariosEquivalent(
          selected,
          minCost
        )
      );

      var tripsSame = (
        Boolean(minTrips)
        && scenariosEquivalent(
          selected,
          minTrips
        )
      );

      return {
        robust: (
          costSame
          && tripsSame
        ),
        matches_cost: costSame,
        matches_trips: tripsSame,
        available: [
          minCost
            ? {
              key: "min_cost",
              scenario: minCost,
              same: costSame
            }
            : null,
          minTrips
            ? {
              key: "min_trips",
              scenario: minTrips,
              same: tripsSame
            }
            : null
        ].filter(Boolean)
      };
    }

    function heroDecision(
      current,
      selected,
      result
    ) {
      var changes = (
        reassignmentDetails(
          current,
          selected,
          result
        )
      );

      var total = (
        selected
        && selected.metrics
        && Number(
          selected.metrics.shipments
        )
      )
      || assignments(selected).length;

      var larger = 0;
      var smaller = 0;

      changes.forEach(
        function (item) {
          if (
            item.to_capacity_kg
            > item.from_capacity_kg
          ) {
            larger += 1;
          } else if (
            item.to_capacity_kg
            < item.from_capacity_kg
          ) {
            smaller += 1;
          }
        }
      );

      var direction = (
        larger > smaller
          ? "a camiones de mayor capacidad"
          : smaller > larger
            ? "a camiones de menor capacidad"
            : "entre alternativas de capacidad"
      );

      return {
        changed: changes.length,
        total: total,
        direction: direction,
        title: (
          changes.length === 0
            ? (
              "Mantener la asignación "
              + "actual de los "
              + total
              + " despachos"
            )
            : (
              "Reasignar "
              + changes.length
              + " de "
              + total
              + " despachos "
              + direction
            )
        )
      };
    }

    return {
      assignments: assignments,
      assignmentMap: assignmentMap,
      selectedScenario: selectedScenario,
      currentScenario: currentScenario,
      assignmentDifferenceCount: (
        assignmentDifferenceCount
      ),
      scenariosEquivalent: (
        scenariosEquivalent
      ),
      vehicleCatalogMap: (
        vehicleCatalogMap
      ),
      assignmentDistribution: (
        assignmentDistribution
      ),
      savings: savings,
      kpis: kpis,
      reassignmentDetails: (
        reassignmentDetails
      ),
      reassignmentMatrix: (
        reassignmentMatrix
      ),
      corridorGroups: (
        corridorGroups
      ),
      chooseDefaultReference: (
        chooseDefaultReference
      ),
      sensitivitySummary: (
        sensitivitySummary
      ),
      heroDecision: heroDecision
    };
  }
);
