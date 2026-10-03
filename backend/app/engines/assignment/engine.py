import copy
import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter

from app.models.assignment_config import (
    ASSIGNMENT_OBJECTIVE_KEYS,
    AssignmentConfig,
    AssignmentOptions,
)
from app.validators.fleet_schema import (
    validate_fleet_csv,
)
from app.validators.orders_schema import (
    validate_orders_csv,
)

from .model import solve
from .plans import (
    active_vehicle,
    greedy,
    summarize,
    validate_assignment,
)
from .preflight import assignment_preflight


ENGINE_NAME = "logistics-assignment-engine"
ENGINE_VERSION = "1.0.0"
SCHEMA_VERSION = "assignment_v1"

NAMES = {
    "min_trips": "Menor cantidad de viajes",
    "min_cost": "Costo mínimo",
    "max_own_fleet": "Mayor uso de flota propia",
    "min_co2": "CO₂ mínimo",
    "balanced": "Balanceado",
    "selected": "Decisión recomendada",
}

METRICS = {
    "trips": "total_trips",
    "cost": "total_cost",
    "own_fleet": "outsourced_weight_kg",
    "co2": "co2_kg",
}

SCENARIO_FOR_OBJECTIVE = {
    "trips": "min_trips",
    "cost": "min_cost",
    "own_fleet": "max_own_fleet",
    "co2": "min_co2",
}

DIRECTIONS = {
    "total_trips": "lower_better",
    "total_cost": "lower_better",
    "outsourced_weight_kg": "lower_better",
    "outsourced_weight_share": "lower_better",
    "own_weight_share": "higher_better",
    "load_utilization": "higher_better",
    "co2_kg": "lower_better",
}


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


def plan_signature(scenario):
    return [
        (
            current["vehicle_id"],
            current["origin"],
            current["destination"],
            [
                (
                    load["order_id"],
                    load["units"],
                )
                for load in current[
                    "loads"
                ]
            ],
        )
        for current in scenario[
            "trips"
        ]
    ]


def _metric(scenario, key):
    value = scenario["metrics"][
        METRICS[key]
    ]
    if value is None:
        raise ValueError(
            "La dimensión "
            + key
            + " no tiene datos suficientes."
        )
    return float(value)


def _capabilities(fleet_report):
    completeness = fleet_report.get(
        "completeness",
        {},
    )

    def complete(column):
        return bool(
            completeness.get(
                column,
                {},
            ).get("complete")
        )

    return {
        "trips": True,
        "own_fleet": True,
        "cost": (
            complete("cost_per_km")
            and complete(
                "fixed_trip_cost"
            )
        ),
        "co2": complete(
            "co2_kg_per_km"
        ),
    }


def _validate_dimensions(
    config,
    capabilities,
):
    unavailable = [
        key
        for key in config["dimensions"]
        if not capabilities.get(key)
    ]
    if unavailable:
        labels = {
            "cost": (
                "costo por km y costo fijo"
            ),
            "co2": "factor de CO₂",
        }
        detail = ", ".join(
            labels.get(
                key,
                key,
            )
            for key in unavailable
        )
        raise ValueError(
            "La configuración usa dimensiones "
            "sin datos completos: "
            + detail
            + "."
        )


def _decision_drivers(selected):
    metrics = selected["metrics"]
    outcomes = selected[
        "order_outcomes"
    ]
    return {
        "trips": metrics[
            "total_trips"
        ],
        "vehicles_used": metrics[
            "vehicles_used"
        ],
        "orders_consolidated": sum(
            outcome["consolidated"]
            for outcome in outcomes
        ),
        "orders_split": sum(
            outcome["split"]
            for outcome in outcomes
        ),
        "orders_outsourced": sum(
            outcome["outsourced"]
            for outcome in outcomes
        ),
        "own_weight_share": metrics[
            "own_weight_share"
        ],
        "outsourced_weight_kg": metrics[
            "outsourced_weight_kg"
        ],
    }


def run_assignment_engine(
    orders_bytes,
    fleet_bytes,
    configuration=None,
    options=None,
    inputs=None,
    progress=None,
):
    started = perf_counter()
    config = AssignmentConfig.model_validate(
        configuration or {}
    ).model_dump()
    opts = AssignmentOptions.model_validate(
        options or {}
    ).model_dump()
    active_dimensions = tuple(
        config["dimensions"]
    )
    analysis_depth = opts[
        "analysis_depth"
    ]

    def notify(stage):
        if (
            perf_counter()
            - started
            > opts[
                "total_time_limit_s"
            ]
        ):
            raise TimeoutError(
                "Se agotó el presupuesto global; "
                "no se publica una asignación parcial."
            )
        if progress:
            progress(stage)

    notify("validating")
    orders_report = validate_orders_csv(
        orders_bytes
    )
    fleet_report = validate_fleet_csv(
        fleet_bytes
    )
    orders = sorted(
        orders_report["records"],
        key=lambda order: order[
            "order_id"
        ],
    )
    full_fleet = sorted(
        fleet_report["records"],
        key=lambda vehicle: (
            vehicle["base_site"],
            vehicle["ownership"],
            vehicle["vehicle_type"],
            vehicle["vehicle_id"],
        ),
    )
    capabilities = _capabilities(
        fleet_report
    )
    _validate_dimensions(
        config,
        capabilities,
    )

    fleet = [
        vehicle
        for vehicle in full_fleet
        if (
            active_vehicle(vehicle)
            and (
                opts[
                    "allow_third_party"
                ]
                or vehicle[
                    "ownership"
                ]
                == "own"
            )
        )
    ]
    if not fleet:
        raise ValueError(
            "No hay flota habilitada "
            "para Assignment."
        )

    check = assignment_preflight(
        orders,
        fleet,
        full_fleet,
    )
    if check["errors"]:
        raise ValueError(
            "; ".join(
                item["detail"]
                + (
                    " "
                    + item.get(
                        "order_id",
                        "",
                    )
                    if item.get(
                        "order_id"
                    )
                    else ""
                )
                for item in check[
                    "errors"
                ]
            )
        )

    anomalies = check[
        "anomalies"
    ]
    for anomaly in anomalies:
        decision = opts[
            "anomaly_decisions"
        ].get(
            anomaly["order_id"]
        )
        if decision is None:
            raise ValueError(
                "Debés decidir incluir o excluir "
                "la anomalía "
                + anomaly[
                    "order_id"
                ]
            )
        anomaly["decision"] = (
            decision
        )

    excluded = {
        anomaly["order_id"]
        for anomaly in anomalies
        if anomaly["decision"]
        == "exclude"
    }
    orders = [
        order
        for order in orders
        if order["order_id"]
        not in excluded
    ]
    if not orders:
        raise ValueError(
            "No quedan órdenes incluidas."
        )

    notify("constructing")
    greedy_candidates = []
    candidate_dimensions = (
        active_dimensions
        if (
            analysis_depth
            != "essential"
            or config["objective"]
            in (
                "balanced",
                "custom",
            )
        )
        else (
            next(
                key
                for key, scenario
                in SCENARIO_FOR_OBJECTIVE.items()
                if scenario
                == config["objective"]
            ),
        )
    )

    for key in candidate_dimensions:
        plan = greedy(
            orders,
            fleet,
            SCENARIO_FOR_OBJECTIVE[
                key
            ],
        )
        if not plan:
            continue
        validate_assignment(
            plan,
            orders,
            fleet,
        )
        greedy_candidates.append(
            {
                **summarize(
                    plan,
                    orders,
                    fleet,
                    capabilities,
                ),
                "name": NAMES[
                    SCENARIO_FOR_OBJECTIVE[
                        key
                    ]
                ],
                "feasible": True,
                "solver": {
                    "status": "feasible",
                    "method": "heuristic",
                    "gap": None,
                },
            }
        )

    if not greedy_candidates:
        raise ValueError(
            "No se encontró una asignación "
            "completa para todas las órdenes."
        )

    scales = {
        key: 1.0
        for key in (
            ASSIGNMENT_OBJECTIVE_KEYS
        )
    }
    normalization = {}
    for key in active_dimensions:
        values = [
            _metric(
                scenario,
                key,
            )
            for scenario
            in greedy_candidates
        ]
        best = min(values)
        worst = max(values)
        scale = max(
            worst - best,
            abs(best) * .01,
            1e-6,
        )
        scales[key] = scale
        normalization[key] = {
            "best_candidate": best,
            "reference_candidate": worst,
            "scale": scale,
        }

    def score(
        scenario,
        weights,
    ):
        return sum(
            float(weights[key])
            * (
                _metric(
                    scenario,
                    key,
                )
                / max(
                    scales[key],
                    1e-9,
                )
            )
            for key in (
                ASSIGNMENT_OBJECTIVE_KEYS
            )
            if float(
                weights[key]
            ) > 0
        )

    def choose(weights):
        return min(
            greedy_candidates,
            key=lambda scenario: (
                score(
                    scenario,
                    weights,
                ),
                scenario[
                    "metrics"
                ]["total_trips"],
                scenario[
                    "metrics"
                ][
                    "outsourced_weight_kg"
                ],
                plan_signature(
                    scenario
                ),
            ),
        )

    scenarios = {}

    def optimize(
        weights,
        label,
    ):
        notify(
            "optimizing:"
            + label
        )
        hint = choose(
            weights
        )["trips"]
        plan, meta = solve(
            orders,
            fleet,
            weights,
            scales,
            opts,
            hint,
        )

        candidates = list(
            greedy_candidates
        )
        solver_candidate = None
        if plan:
            validate_assignment(
                plan,
                orders,
                fleet,
            )
            solver_candidate = {
                **summarize(
                    plan,
                    orders,
                    fleet,
                    capabilities,
                ),
                "name": NAMES.get(
                    label,
                    label,
                ),
                "feasible": True,
                "solver": meta,
            }
            candidates.append(
                solver_candidate
            )

        selected = copy.deepcopy(
            min(
                candidates,
                key=lambda scenario: (
                    score(
                        scenario,
                        weights,
                    ),
                    scenario[
                        "metrics"
                    ]["total_trips"],
                    scenario[
                        "metrics"
                    ][
                        "outsourced_weight_kg"
                    ],
                    plan_signature(
                        scenario
                    ),
                ),
            )
        )

        if (
            solver_candidate is None
            or plan_signature(
                selected
            )
            != plan_signature(
                solver_candidate
            )
        ):
            selected["solver"] = {
                **meta,
                "status": "feasible",
                "method": (
                    "heuristic"
                    if (
                        solver_candidate
                        is None
                    )
                    else "best_candidate"
                ),
                "gap": None,
            }
        selected["name"] = NAMES.get(
            label,
            label,
        )
        return selected

    extremes = {
        scenario: key
        for key, scenario
        in SCENARIO_FOR_OBJECTIVE.items()
        if key in active_dimensions
    }

    if (
        analysis_depth
        == "essential"
        and config["objective"]
        not in (
            "balanced",
            "custom",
        )
    ):
        scenario_names = {
            config["objective"]: next(
                key
                for key, value
                in SCENARIO_FOR_OBJECTIVE.items()
                if value
                == config[
                    "objective"
                ]
            )
        }
    else:
        scenario_names = extremes

    for name, key in (
        scenario_names.items()
    ):
        weights = {
            item: float(
                item == key
            )
            for item in (
                ASSIGNMENT_OBJECTIVE_KEYS
            )
        }
        scenarios[name] = optimize(
            weights,
            name,
        )

    balanced_weights = {
        key: (
            1
            / len(
                active_dimensions
            )
            if key
            in active_dimensions
            else 0
        )
        for key in (
            ASSIGNMENT_OBJECTIVE_KEYS
        )
    }
    if (
        analysis_depth
        != "essential"
        or config["objective"]
        == "balanced"
    ):
        scenarios[
            "balanced"
        ] = optimize(
            balanced_weights,
            "balanced",
        )

    configured_weights = (
        config["weights"]
    )
    if (
        config["objective"]
        in scenarios
    ):
        selected = copy.deepcopy(
            scenarios[
                config[
                    "objective"
                ]
            ]
        )
    else:
        selected = optimize(
            configured_weights,
            "selected",
        )
    selected["name"] = NAMES[
        "selected"
    ]
    scenarios["selected"] = (
        selected
    )

    notify("summarizing")
    selected_plan_fingerprint = (
        digest(
            plan_signature(
                selected
            )
        )
    )
    for name, scenario in (
        scenarios.items()
    ):
        scenario[
            "plan_fingerprint"
        ] = digest(
            plan_signature(
                scenario
            )
        )
        if name != "selected":
            scenario.pop(
                "trips",
                None,
            )
            scenario.pop(
                "order_outcomes",
                None,
            )

    frontier = [
        {
            "scenario": name,
            "label": NAMES.get(
                name,
                name,
            ),
            "metrics": scenario[
                "metrics"
            ],
            "solver": scenario[
                "solver"
            ],
            "plan_fingerprint": scenario[
                "plan_fingerprint"
            ],
        }
        for name, scenario
        in scenarios.items()
        if name != "selected"
    ]

    resources = [
        {
            "vehicle_id": vehicle[
                "vehicle_id"
            ],
            "vehicle_type": vehicle[
                "vehicle_type"
            ],
            "ownership": vehicle[
                "ownership"
            ],
            "provider_name": (
                vehicle.get(
                    "provider_name"
                )
                or None
            ),
            "base_site": vehicle[
                "base_site"
            ],
            "capacity_kg": vehicle[
                "capacity_kg"
            ],
            "status": (
                vehicle.get(
                    "status"
                )
                or "available"
            ),
        }
        for vehicle in full_fleet
    ]

    result = {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "decision": {
            "id": (
                "logistics_assignment"
            ),
            "status": "recommended",
            "objective": config[
                "objective"
            ],
            "label": (
                "Asignación recomendada"
            ),
        },
        "analysis": {
            "depth": analysis_depth,
            "active_dimensions": list(
                active_dimensions
            ),
            "scenario_count": len(
                [
                    key
                    for key in scenarios
                    if key
                    != "selected"
                ]
            ),
            "temporal": False,
        },
        "capabilities": (
            capabilities
        ),
        "decision_drivers": (
            _decision_drivers(
                selected
            )
        ),
        "exceptions": [],
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "solver": selected[
                "solver"
            ],
        },
        "inputs": {
            "orders": {
                "sha256": (
                    hashlib.sha256(
                        orders_bytes
                    ).hexdigest()
                ),
                "rows": (
                    len(orders)
                    + len(excluded)
                ),
                **(
                    inputs
                    or {}
                ).get(
                    "orders",
                    {},
                ),
            },
            "fleet": {
                "sha256": (
                    hashlib.sha256(
                        fleet_bytes
                    ).hexdigest()
                ),
                "rows": len(
                    full_fleet
                ),
                **(
                    inputs
                    or {}
                ).get(
                    "fleet",
                    {},
                ),
            },
            "anomalies": anomalies,
            "preflight": check,
        },
        "configuration": {
            **config,
            "options": opts,
        },
        "resources": resources,
        "kpi_directions": (
            DIRECTIONS
        ),
        "normalization": (
            normalization
        ),
        "assumptions": [
            (
                "Assignment decide cómo "
                "distribuir la carga, no cuándo "
                "ejecutar los viajes."
            ),
            (
                "Cada viaje conecta un origen "
                "y un destino; no hay multiparada."
            ),
            (
                "Cada unidad se asigna completa "
                "y ningún viaje supera la "
                "capacidad del vehículo."
            ),
            (
                "Un mismo vehículo puede recibir "
                "varios viajes abstractos porque "
                "su secuencia temporal se resuelve "
                "en Scheduling."
            ),
            (
                "Costo y CO₂, cuando están "
                "disponibles, contemplan ida "
                "y vuelta."
            ),
            (
                "Fechas estimadas, velocidad, "
                "horas de conducción, SLA y "
                "disponibilidad futura no "
                "intervienen en Assignment."
            ),
        ],
        "scenarios": scenarios,
        "sensitivity": {
            "frontier": (
                frontier
                if analysis_depth
                in (
                    "comparative",
                    "deep",
                )
                else []
            ),
            "complete": True,
        },
        "handoff": {
            "schema_version": (
                "scheduling_input_v1"
            ),
            "source_decision": (
                "logistics_assignment"
            ),
            "next_decision": (
                "logistics_scheduling"
            ),
            "source_path": (
                "scenarios.selected.trips"
            ),
            "assignment_fingerprint": (
                selected_plan_fingerprint
            ),
            "trip_count": selected[
                "metrics"
            ]["total_trips"],
            "trip_ids": [
                trip["trip_id"]
                for trip in selected[
                    "trips"
                ]
            ],
        },
    }

    stable = {
        "schema_version": (
            SCHEMA_VERSION
        ),
        "version": ENGINE_VERSION,
        "configuration": result[
            "configuration"
        ],
        "orders_hash": result[
            "inputs"
        ]["orders"]["sha256"],
        "fleet_hash": result[
            "inputs"
        ]["fleet"]["sha256"],
        "decision": result[
            "decision"
        ],
        "capabilities": capabilities,
        "selected": {
            "metrics": selected[
                "metrics"
            ],
            "plan": plan_signature(
                selected
            ),
        },
        "alternatives": {
            key: scenario[
                "metrics"
            ]
            for key, scenario
            in scenarios.items()
            if key != "selected"
        },
    }
    result[
        "result_fingerprint"
    ] = digest(stable)
    result["engine"]["wall_ms"] = (
        int(
            (
                perf_counter()
                - started
            )
            * 1000
        )
    )
    return result
