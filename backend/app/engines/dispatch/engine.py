import copy
import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter

from app.models.dispatch_config import (
    DispatchConfig,
    DispatchOptions,
    OBJECTIVE_KEYS,
    PRESETS,
)
from app.validators.orders_schema import validate_orders_csv
from app.validators.fleet_schema import validate_fleet_csv

from .normalization import preflight
from .plans import greedy, summarize, validate_plan
from .model import solve


ENGINE_NAME = "logistics-dispatch-engine"
ENGINE_VERSION = "2.2.0"
SCHEMA_VERSION = "dispatch_v2"

NAMES = {
    "baseline_direct": "Referencia sintética: despacho individual",
    "min_cost": "Costo mínimo",
    "min_time": "Tiempo mínimo",
    "max_utilization": "Máxima utilización propia",
    "min_co2": "CO₂ mínimo",
    "balanced": "Balanceado",
    "selected": "Decisión recomendada",
}

METRICS = {
    "cost": "total_cost",
    "time": "avg_lead_time_days",
    "utilization": "outsourced_weight_share",
    "co2": "co2_kg",
}

SCENARIO_FOR_OBJECTIVE = {
    "cost": "min_cost",
    "time": "min_time",
    "utilization": "max_utilization",
    "co2": "min_co2",
}

DIRECTIONS = {
    "total_cost": "lower_better",
    "total_trips": "lower_better",
    "avg_lead_time_days": "lower_better",
    "on_time_rate": "higher_better",
    "late_orders": "lower_better",
    "total_late_days": "lower_better",
    "priority_weighted_late_days": "lower_better",
    "load_utilization": "higher_better",
    "own_load_utilization": "higher_better",
    "own_weight_share": "higher_better",
    "outsourced_weight_share": "lower_better",
    "outsourced_trips_share": "lower_better",
    "co2_kg": "lower_better",
    "fuel_l": "lower_better",
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
            current["dispatch_date"],
            current["fleet_pool_id"],
            current["origin"],
            current["destination"],
            [
                (
                    load["order_id"],
                    load["units"],
                )
                for load in current["loads"]
            ],
        )
        for current in scenario["trips"]
    ]


def _sla_key(scenario):
    metrics = scenario["metrics"]
    return (
        metrics["late_orders"],
        metrics["priority_weighted_late_days"],
        metrics["total_late_days"],
    )


def _metric(scenario, key):
    return scenario["metrics"][METRICS[key]]


def _decision_drivers(selected):
    outcomes = selected["order_outcomes"]
    metrics = selected["metrics"]
    return {
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
        "orders_postponed": sum(
            outcome["postponed_days"] > 0
            for outcome in outcomes
        ),
        "late_orders": metrics["late_orders"],
        "physical_sla_violations": (
            metrics["late_orders_unavoidable"]
        ),
        "capacity_or_policy_sla_violations": max(
            0,
            metrics["late_orders"]
            - metrics["late_orders_unavoidable"],
        ),
        "own_weight_share": metrics["own_weight_share"],
        "outsourced_weight_kg": (
            metrics["outsourced_weight_kg"]
        ),
        "own_trips": metrics["own_trips"],
        "outsourced_trips": metrics["outsourced_trips"],
    }


def _exceptions(selected):
    return [
        {
            "order_id": outcome["order_id"],
            "priority": outcome["priority"],
            "late_days": outcome["late_days"],
            "deadline": outcome["deadline"],
            "arrival_date": outcome["arrival_date"],
            "trip_ids": outcome["trip_ids"],
        }
        for outcome in selected["order_outcomes"]
        if outcome["late_days"] > 0
    ]


def run_dispatch_engine(
    orders_bytes,
    fleet_bytes,
    configuration=None,
    options=None,
    inputs=None,
    progress=None,
):
    started = perf_counter()
    config = DispatchConfig.model_validate(
        configuration or {}
    ).model_dump()
    opts = DispatchOptions.model_validate(
        options or {}
    ).model_dump()
    active_dimensions = tuple(config["dimensions"])
    analysis_depth = opts["analysis_depth"]
    run_sensitivity = (
        opts["sensitivity"]
        if opts["sensitivity"] is not None
        else analysis_depth == "deep"
    )
    opts["sensitivity"] = run_sensitivity

    def notify(stage):
        if (
            perf_counter() - started
            > opts["total_time_limit_s"]
        ):
            raise TimeoutError(
                "Se agotó el presupuesto global; "
                "no se publica una decisión parcial."
            )
        if progress:
            progress(stage)

    notify("validating")
    orders = sorted(
        validate_orders_csv(
            orders_bytes
        )["records"],
        key=lambda order: order["order_id"],
    )
    full_fleet = sorted(
        validate_fleet_csv(
            fleet_bytes
        )["records"],
        key=lambda vehicle: (
            vehicle["base_location"],
            vehicle["vehicle_type"],
            vehicle["fleet_pool_id"],
        ),
    )
    fleet = [
        vehicle
        for vehicle in full_fleet
        if (
            opts["allow_third_party"]
            or vehicle["ownership"] == "own"
        )
    ]
    if not fleet:
        raise ValueError("No hay flota habilitada.")

    check = preflight(
        orders,
        fleet,
        full_fleet,
    )
    if check["errors"]:
        raise ValueError(
            "; ".join(
                error["detail"]
                + " "
                + error.get("order_id", "")
                for error in check["errors"]
            )
        )

    anomalies = check["anomalies"]
    for anomaly in anomalies:
        decision = opts[
            "anomaly_decisions"
        ].get(anomaly["order_id"])
        if decision is None:
            raise ValueError(
                "Debés decidir incluir o excluir la anomalía "
                + anomaly["order_id"]
            )
        anomaly["decision"] = decision

    excluded = {
        anomaly["order_id"]
        for anomaly in anomalies
        if anomaly["decision"] == "exclude"
    }
    orders = [
        order
        for order in orders
        if order["order_id"] not in excluded
    ]
    if not orders:
        raise ValueError(
            "No quedan órdenes incluidas."
        )

    notify("baseline")
    scenarios = {}
    candidates = []

    direct = greedy(
        orders,
        fleet,
        direct=True,
    )
    if direct:
        try:
            validate_plan(
                direct,
                orders,
                fleet,
                direct=True,
            )
            baseline = {
                **summarize(
                    direct,
                    orders,
                    fleet,
                ),
                "name": NAMES["baseline_direct"],
                "feasible": True,
                "solver": {
                    "status": "feasible",
                    "method": "declared_policy",
                    "gap": None,
                    "sla_certified": False,
                },
            }
        except ValueError:
            baseline = {
                "name": NAMES["baseline_direct"],
                "feasible": False,
                "metrics": None,
                "trips": [],
                "order_outcomes": [],
                "solver": {
                    "status": "unknown",
                    "method": "declared_policy",
                    "gap": None,
                    "sla_certified": False,
                },
                "warning": (
                    "La política directa no respeta todas "
                    "las restricciones temporales."
                ),
            }
    else:
        baseline = {
            "name": NAMES["baseline_direct"],
            "feasible": False,
            "metrics": None,
            "trips": [],
            "order_outcomes": [],
            "solver": {
                "status": "unknown",
                "method": "declared_policy",
                "gap": None,
                "sla_certified": False,
            },
            "warning": (
                "La política directa no encuentra cobertura "
                "con la flota disponible."
            ),
        }
    scenarios["baseline_direct"] = baseline

    if (
        analysis_depth == "essential"
        and config["objective"]
        not in ("balanced", "custom")
    ):
        candidate_objectives = (
            config["objective"],
        )
    else:
        candidate_objectives = tuple(
            SCENARIO_FOR_OBJECTIVE[key]
            for key in active_dimensions
        )

    for objective in candidate_objectives:
        candidate_plan = greedy(
            orders,
            fleet,
            objective=objective,
            max_late_days=opts["max_late_days"],
        )
        if candidate_plan:
            validate_plan(
                candidate_plan,
                orders,
                fleet,
                max_late_days=opts[
                    "max_late_days"
                ],
            )
            candidates.append(
                summarize(
                    candidate_plan,
                    orders,
                    fleet,
                )
            )

    if baseline["feasible"]:
        try:
            validate_plan(
                baseline["trips"],
                orders,
                fleet,
                max_late_days=opts[
                    "max_late_days"
                ],
            )
            candidates.append(
                copy.deepcopy(baseline)
            )
        except ValueError:
            pass

    if not candidates:
        raise ValueError(
            "No se encontró una distribución completa "
            "dentro del horizonte de recuperación."
        )

    scales = {
        key: 1.0
        for key in OBJECTIVE_KEYS
    }

    def choose(weights, active_scales):
        def key(scenario):
            business = sum(
                weights[name]
                * _metric(scenario, name)
                / max(
                    active_scales[name],
                    1e-9,
                )
                for name in OBJECTIVE_KEYS
            )
            return (
                *_sla_key(scenario),
                business,
                scenario["metrics"]["total_trips"],
                scenario["metrics"]["total_cost"],
                plan_signature(scenario),
            )

        return min(
            candidates,
            key=key,
        )

    def optimize(weights, label, active_scales):
        notify("optimizing:" + label)
        if len(orders) <= 300:
            hint = (
                choose(
                    weights,
                    active_scales,
                )["trips"]
                if candidates
                else None
            )
            plan, meta = solve(
                orders,
                fleet,
                weights,
                active_scales,
                opts,
                hint,
            )
        else:
            plan = None
            meta = {
                "status": "feasible",
                "method": "heuristic",
                "gap": None,
                "sla_status": "not_run",
                "sla_certified": False,
                "reason": (
                    "Política determinística para "
                    "más de 300 órdenes."
                ),
            }

        solver_candidate = None
        if plan:
            validate_plan(
                plan,
                orders,
                fleet,
                max_late_days=opts[
                    "max_late_days"
                ],
            )
            solver_candidate = summarize(
                plan,
                orders,
                fleet,
            )
            candidates.append(
                solver_candidate
            )

        if not candidates:
            raise ValueError(
                "No se encontró una distribución factible "
                "dentro del presupuesto."
            )

        result = copy.deepcopy(
            choose(
                weights,
                active_scales,
            )
        )
        if (
            not solver_candidate
            or plan_signature(result)
            != plan_signature(
                solver_candidate
            )
        ):
            meta = {
                **meta,
                "status": "feasible",
                "method": (
                    "heuristic"
                    if not solver_candidate
                    else "best_candidate"
                ),
                "gap": None,
            }
        result.update(
            solver=meta,
            feasible=True,
            name=NAMES.get(label, label),
        )
        return result

    # The analysis depth controls how many alternative objectives are solved.
    # Essential only computes what is needed for the requested decision.
    # Comparative adds active extreme scenarios and a balanced reference.
    # Deep adds the same comparisons plus sensitivity evidence.
    extreme_map = {
        "min_cost": "cost",
        "min_time": "time",
        "max_utilization": "utilization",
        "min_co2": "co2",
    }
    active_extremes = {
        scenario: dimension
        for scenario, dimension in extreme_map.items()
        if dimension in active_dimensions
    }

    if (
        analysis_depth == "essential"
        and config["objective"]
        not in ("balanced", "custom")
    ):
        scenarios_to_solve = {
            config["objective"]: active_extremes[
                config["objective"]
            ]
        }
    else:
        scenarios_to_solve = active_extremes

    for scenario_name, objective_key in scenarios_to_solve.items():
        weights = {
            key: float(key == objective_key)
            for key in OBJECTIVE_KEYS
        }
        scenarios[scenario_name] = optimize(
            weights,
            scenario_name,
            scales,
        )

    normalization = {}
    dimensions_to_normalize = (
        active_dimensions
        if (
            analysis_depth != "essential"
            or config["objective"] in ("balanced", "custom")
        )
        else (
            extreme_map[config["objective"]],
        )
    )
    for objective_key in dimensions_to_normalize:
        values = [
            _metric(scenario, objective_key)
            for scenario in scenarios.values()
            if (
                scenario.get("feasible")
                and scenario.get("metrics")
            )
        ]
        if baseline["feasible"]:
            reference = _metric(
                baseline,
                objective_key,
            )
            values.append(reference)
        else:
            reference = max(values)

        best = min(values)
        scale = max(
            max(values) - best,
            abs(reference - best),
            abs(best) * .01,
            1e-6,
        )
        scales[objective_key] = scale
        extreme_name = SCENARIO_FOR_OBJECTIVE[
            objective_key
        ]
        extreme = scenarios.get(extreme_name)
        normalization[objective_key] = {
            "best_known": best,
            "reference": reference,
            "scale": scale,
            "certified_optimal": bool(
                extreme
                and extreme["solver"].get("status")
                == "optimal"
                and extreme["solver"].get(
                    "sla_certified",
                    False,
                )
            ),
        }

    balanced_weights = {
        key: (
            1 / len(active_dimensions)
            if key in active_dimensions
            else 0
        )
        for key in OBJECTIVE_KEYS
    }
    if (
        analysis_depth != "essential"
        or config["objective"] == "balanced"
    ):
        scenarios["balanced"] = optimize(
            balanced_weights,
            "balanced",
            scales,
        )

    weights = config["weights"]
    if config["objective"] in scenarios:
        selected = copy.deepcopy(
            scenarios[config["objective"]]
        )
    else:
        selected = optimize(
            weights,
            "selected",
            scales,
        )
    selected["name"] = NAMES["selected"]
    scenarios["selected"] = selected

    notify("sensitivity")
    sweep = []
    sensitivity_names = [
        scenario
        for scenario in (
            "min_cost",
            "min_time",
            "max_utilization",
            "min_co2",
            "balanced",
        )
        if scenario in scenarios
    ]
    if run_sensitivity:
        previous_map = None

        def order_map(scenario):
            mapping = {
                order["order_id"]: []
                for order in orders
            }
            for current in scenario["trips"]:
                signature = (
                    current["dispatch_date"],
                    current["fleet_pool_id"],
                    tuple(
                        (
                            load["order_id"],
                            load["units"],
                        )
                        for load in current[
                            "loads"
                        ]
                    ),
                )
                for load in current["loads"]:
                    mapping[
                        load["order_id"]
                    ].append(signature)
            return {
                key: tuple(sorted(value))
                for key, value in mapping.items()
            }

        selected_map = order_map(selected)
        for scenario_name in sensitivity_names:
            scenario = scenarios[scenario_name]
            current_map = order_map(scenario)
            if scenario_name == "balanced":
                point_weights = balanced_weights
            else:
                objective_key = extreme_map[
                    scenario_name
                ]
                point_weights = {
                    key: float(key == objective_key)
                    for key in OBJECTIVE_KEYS
                }
            point = {
                "scenario": scenario_name,
                "label": NAMES[scenario_name],
                "weights": point_weights,
                "metrics": scenario["metrics"],
                "solver": scenario["solver"],
                "plan_fingerprint": digest(
                    plan_signature(scenario)
                ),
                "orders_changed_vs_selected": sum(
                    current_map[key]
                    != selected_map[key]
                    for key in current_map
                ),
                "orders_changed_vs_previous": (
                    None
                    if previous_map is None
                    else sum(
                        current_map[key]
                        != previous_map[key]
                        for key in current_map
                    )
                ),
            }
            sweep.append(point)
            previous_map = current_map

    notify("summarizing")
    decision_drivers = _decision_drivers(
        selected
    )
    exceptions = _exceptions(selected)
    feasibility = {
        "orders": selected["metrics"]["orders"],
        "on_time_orders": (
            selected["metrics"]["orders"]
            - selected["metrics"]["late_orders"]
        ),
        "late_orders": selected["metrics"][
            "late_orders"
        ],
        "physical_sla_violations": selected[
            "metrics"
        ]["late_orders_unavoidable"],
        "capacity_or_policy_sla_violations": (
            decision_drivers[
                "capacity_or_policy_sla_violations"
            ]
        ),
        "best_known_late_orders": selected[
            "metrics"
        ]["late_orders"],
        "sla_optimal_certified": selected[
            "solver"
        ].get("sla_certified", False),
        "recovery_horizon_days": opts[
            "max_late_days"
        ],
    }
    decision_status = (
        "recommended"
        if not exceptions
        else "recommended_with_exceptions"
    )

    for name, scenario in scenarios.items():
        if scenario.get("metrics"):
            scenario["plan_fingerprint"] = digest(
                plan_signature(scenario)
            )
            scenario["delta_vs_baseline"] = (
                {
                    key: (
                        scenario["metrics"][key]
                        - baseline["metrics"][key]
                    )
                    for key in DIRECTIONS
                    if key
                    in scenario["metrics"]
                    and key
                    in baseline["metrics"]
                }
                if baseline["feasible"]
                else None
            )
        if name not in (
            "selected",
            "baseline_direct",
        ):
            scenario.pop("trips", None)
            scenario.pop(
                "order_outcomes",
                None,
            )

    result = {
        "schema_version": SCHEMA_VERSION,
        "decision": {
            "status": decision_status,
            "objective": config["objective"],
            "label": "Decisión recomendada",
        },
        "analysis": {
            "depth": analysis_depth,
            "active_dimensions": list(active_dimensions),
            "scenario_count": len(
                [
                    key
                    for key in scenarios
                    if key not in ("selected", "baseline_direct")
                ]
            ),
            "sensitivity_enabled": run_sensitivity,
        },
        "feasibility": feasibility,
        "decision_drivers": decision_drivers,
        "exceptions": exceptions,
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "executed_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "solver": selected["solver"],
        },
        "inputs": {
            "orders": {
                "sha256": hashlib.sha256(
                    orders_bytes
                ).hexdigest(),
                "rows": len(orders)
                + len(excluded),
                **(inputs or {}).get(
                    "orders",
                    {},
                ),
            },
            "fleet": {
                "sha256": hashlib.sha256(
                    fleet_bytes
                ).hexdigest(),
                "rows": len(full_fleet),
                **(inputs or {}).get(
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
        "fleet": full_fleet,
        "kpi_directions": DIRECTIONS,
        "normalization": normalization,
        "assumptions": [
            (
                "El SLA se optimiza antes que costo, tiempo, "
                "utilización propia o CO₂."
            ),
            (
                "Las entregas tardías sólo se exploran dentro de "
                f"{opts['max_late_days']} días de recuperación."
            ),
            (
                "Un viaje conecta un origen y un destino; "
                "no hay multiparada."
            ),
            (
                "La flota se asigna sólo desde pools cuya base "
                "coincide con el origen; tercerizados con base * "
                "pueden operar desde cualquier origen."
            ),
            (
                "Los pools finitos permanecen ocupados desde la "
                "salida hasta completar ida, entrega y retorno."
            ),
            (
                "Maximizar utilización propia minimiza primero "
                "la participación de kg tercerizados; la "
                "utilización de carga propia se informa como KPI."
            ),
            (
                "Costo, combustible y CO₂ contemplan ida y vuelta."
            ),
            (
                "Los factores de emisiones son informados por "
                "el usuario y no están certificados."
            ),
            (
                "No se modelan volumen, dimensiones, ventanas "
                "horarias, carga/descarga, multiparada ni "
                "reposicionamiento entre bases."
            ),
            (
                "Un resultado factible no demuestra optimalidad; "
                "el dashboard distingue la certificación del solver."
            ),
        ],
        "scenarios": scenarios,
        "sensitivity": {
            "weight_sweep": sweep,
            "frontier": sweep,
            "complete": (
                not run_sensitivity
                or len(sweep) == len(sensitivity_names)
            ),
        },
    }

    stable = {
        "schema_version": SCHEMA_VERSION,
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
        "decision": result["decision"],
        "feasibility": feasibility,
        "decision_drivers": decision_drivers,
        "scenarios": {
            key: {
                name: value
                for name, value in scenario.items()
                if name != "solver"
            }
            for key, scenario in scenarios.items()
        },
        "sensitivity": [
            {
                key: value
                for key, value in point.items()
                if key != "solver"
            }
            for point in sweep
        ],
    }

    if (
        perf_counter() - started
        > opts["total_time_limit_s"]
    ):
        raise TimeoutError(
            "Se agotó el presupuesto global; "
            "no se publica una decisión parcial."
        )

    result["result_fingerprint"] = digest(
        stable
    )
    result["engine"]["wall_ms"] = int(
        (perf_counter() - started) * 1000
    )
    return result
