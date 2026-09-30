const assert = require("node:assert/strict");
const path = require("node:path");

const formatters = require(
  path.resolve(
    __dirname,
    "../app/static/js/dashboard-formatters.js"
  )
);

const selectors = require(
  path.resolve(
    __dirname,
    "../app/static/js/dashboard-selectors.js"
  )
);

assert.equal(
  formatters.formatCurrency(169511400),
  "$ 169.511.400"
);

assert.equal(
  formatters.formatCurrencyCompact(169511400),
  "$ 169,5 M"
);

assert.equal(
  formatters.formatPercent(-26.29),
  "−26,3 %"
);

assert.equal(
  formatters.formatKm(150610),
  "150.610 km"
);

assert.equal(
  formatters.vehicleLabel("TRUCK_L"),
  "Camión L"
);

assert.equal(
  formatters.scenarioLabel("min_cost"),
  "Costo mínimo"
);

assert.equal(
  formatters.formatDateRange(
    "2026-10-01",
    "2026-10-09"
  ),
  "1 oct – 9 oct 2026"
);

const current = {
  metrics: {
    shipments: 3,
    total_cost: 300,
    total_trips: 9,
    total_distance_km: 900
  },
  assignments: [
    {
      shipment_id: "A",
      origin: "Cordoba",
      destination: "Rosario",
      vehicle_type: "TRUCK_S",
      required_trips: 4,
      total_cost: 120,
      total_distance_km: 400,
      quantity_units: 10
    },
    {
      shipment_id: "B",
      origin: "Cordoba",
      destination: "Rosario",
      vehicle_type: "TRUCK_M",
      required_trips: 3,
      total_cost: 100,
      total_distance_km: 300,
      quantity_units: 8
    },
    {
      shipment_id: "C",
      origin: "Rosario",
      destination: "Santa Fe",
      vehicle_type: "TRUCK_L",
      required_trips: 2,
      total_cost: 80,
      total_distance_km: 200,
      quantity_units: 6
    }
  ]
};

const decision = {
  metrics: {
    shipments: 3,
    total_cost: 210,
    total_trips: 6,
    total_distance_km: 600
  },
  assignments: [
    {
      shipment_id: "A",
      origin: "Cordoba",
      destination: "Rosario",
      vehicle_type: "TRUCK_L",
      required_trips: 2,
      total_cost: 70,
      total_distance_km: 200,
      quantity_units: 10
    },
    {
      shipment_id: "B",
      origin: "Cordoba",
      destination: "Rosario",
      vehicle_type: "TRUCK_L",
      required_trips: 2,
      total_cost: 70,
      total_distance_km: 200,
      quantity_units: 8
    },
    {
      shipment_id: "C",
      origin: "Rosario",
      destination: "Santa Fe",
      vehicle_type: "TRUCK_L",
      required_trips: 2,
      total_cost: 70,
      total_distance_km: 200,
      quantity_units: 6
    }
  ]
};

const result = {
  recommended_scenario: "min_cost",
  vehicle_catalog: [
    {
      vehicle_type: "TRUCK_S",
      capacity_kg: 8000
    },
    {
      vehicle_type: "TRUCK_M",
      capacity_kg: 15000
    },
    {
      vehicle_type: "TRUCK_L",
      capacity_kg: 25000
    }
  ],
  scenarios: {
    baseline: current,
    min_cost: decision,
    min_trips: JSON.parse(
      JSON.stringify(decision)
    )
  }
};

const run = {
  result_json: result
};

assert.equal(
  selectors.assignmentDifferenceCount(
    current,
    decision
  ),
  2
);

assert.equal(
  selectors.scenariosEquivalent(
    decision,
    result.scenarios.min_trips
  ),
  true
);

assert.deepEqual(
  selectors.savings(
    current,
    decision
  ).cost,
  {
    absolute: 90,
    pct: 30
  }
);

assert.deepEqual(
  selectors.assignmentDistribution(
    decision
  ).find(
    (item) => (
      item.vehicle_type === "TRUCK_L"
    )
  ),
  {
    vehicle_type: "TRUCK_L",
    shipments: 3,
    trips: 6,
    units: 24,
    weight_kg: 0
  }
);

const matrix = (
  selectors.reassignmentMatrix(
    current,
    decision,
    result
  )
);

assert.equal(
  matrix.length,
  2
);

assert.equal(
  matrix[0].shipments,
  1
);

const corridors = (
  selectors.corridorGroups(
    current,
    decision,
    result
  )
);

assert.equal(
  corridors[0].corridor,
  "Cordoba → Rosario"
);

assert.equal(
  corridors[0].shipments,
  2
);

assert.equal(
  selectors.chooseDefaultReference(
    result
  ),
  "baseline"
);

const sensitivity = (
  selectors.sensitivitySummary(
    result
  )
);

assert.equal(
  sensitivity.robust,
  true
);

const hero = selectors.heroDecision(
  current,
  decision,
  result
);

assert.equal(
  hero.changed,
  2
);

assert.equal(
  hero.direction,
  "a camiones de mayor capacidad"
);

console.log(
  "dashboard formatters/selectors tests: ok"
);
