"""Fixed-trip temporal certificate, independent of D1 allocation and D2 policy.

The witness is a proof of existence, not a published dispatch recommendation.
OWN occupancy ends exclusively; EXTERNAL services share one horizon quota.
"""
from collections import defaultdict
from datetime import date
from typing import Literal

from ortools.sat.python import cp_model
from pydantic import Field

from app.domain.logistics.base import ContractModel, DecisionDate, Identifier, Positive
from app.domain.logistics.contracts import Horizon, TransportResource
from app.domain.logistics.transit import TransitEstimator


class FixedTrip(ContractModel):
    trip_id: Identifier
    resource_id: Identifier
    distance_km: Positive
    ready_date: DecisionDate
    delivery_due_date: DecisionDate


class TemporalWitness(ContractModel):
    trip_id: Identifier
    resource_id: Identifier
    dispatch: DecisionDate
    arrival: DecisionDate
    available_again: DecisionDate | None
    unit_index: int | None = Field(default=None, strict=True, ge=0)


class FeasibilityCertificate(ContractModel):
    status: Literal['FEASIBLE', 'INFEASIBLE', 'UNKNOWN']
    witness: tuple[TemporalWitness, ...] = ()
    native_status: str
    scope: Literal['FIXED_TRIPS_EXISTENCE_V1'] = 'FIXED_TRIPS_EXISTENCE_V1'
    cause: str | None = None


def dispatch_window(trip, resource, horizon):
    """Use the T1 authority; horizon bounds departures, not arrival/return."""
    estimate = TransitEstimator.estimate(trip.distance_km, resource.source)
    earliest = max(horizon.planning_start, trip.ready_date)
    # Ordinals avoid DATE underflow on a clearly impossible long transit.
    latest = min(horizon.planning_end.toordinal(),
                 trip.delivery_due_date.toordinal() - estimate.outbound_days + 1)
    return earliest.toordinal(), latest, estimate


def day_resource_feasibility(trips, resources, horizon, *, deterministic_budget=2.0):
    horizon = Horizon.model_validate(horizon)
    trips = tuple(FixedTrip.model_validate(t) for t in trips)
    resources = tuple(TransportResource.model_validate(r) for r in resources)
    if len({t.trip_id for t in trips}) != len(trips) or len({r.resource_id for r in resources}) != len(resources):
        raise ValueError('Duplicate fixed Trip/resource IDs')
    if len(trips) > 256 or len(resources) > 40 or (horizon.planning_end-horizon.planning_start).days > 365:
        return FeasibilityCertificate(status='UNKNOWN', native_status='NOT_RUN', cause='KERNEL_BUDGET')
    if not 0 <= deterministic_budget <= 30:
        raise ValueError('Invalid deterministic kernel budget')
    by_id = {r.resource_id: r for r in resources}
    if any(t.resource_id not in by_id for t in trips):
        raise ValueError('Unknown fixed Trip resource')
    if not trips:
        return FeasibilityCertificate(status='FEASIBLE', native_status='TRIVIAL')
    model = cp_model.CpModel()
    starts, intervals, counts, estimates = {}, defaultdict(list), defaultdict(int), {}
    for trip in sorted(trips, key=lambda t: t.trip_id):
        resource = by_id[trip.resource_id]
        available = resource.units_available if resource.source == 'OWN' else resource.services_available
        if available is None or resource.source == 'EXTERNAL' and resource.availability_source == 'UNKNOWN':
            return FeasibilityCertificate(status='UNKNOWN', native_status='NOT_RUN', cause='UNKNOWN_AVAILABILITY')
        earliest, latest, estimate = dispatch_window(trip, resource, horizon)
        if earliest > latest or available == 0:
            return FeasibilityCertificate(status='INFEASIBLE', native_status='EXACT_BOUND', cause='WINDOW_OR_ZERO_AVAILABILITY')
        start = model.new_int_var(earliest, latest, 'start_' + trip.trip_id)
        starts[trip.trip_id] = start
        estimates[trip.trip_id] = estimate
        counts[resource.resource_id] += 1
        if resource.source == 'OWN':
            intervals[resource.resource_id].append(model.new_fixed_size_interval_var(start, estimate.cycle_days, 'cycle_'+trip.trip_id))
    for rid, count in counts.items():
        resource = by_id[rid]
        if resource.source == 'EXTERNAL' and count > resource.services_available:
            return FeasibilityCertificate(status='INFEASIBLE', native_status='EXACT_BOUND', cause='HORIZON_SERVICE_LIMIT')
        if resource.source == 'OWN':
            model.add_cumulative(intervals[rid], [1]*count, min(resource.units_available, count))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_deterministic_time = deterministic_budget
    solver.parameters.max_time_in_seconds = 10
    status = solver.solve(model)
    native = solver.status_name(status)
    if status == cp_model.MODEL_INVALID:
        raise RuntimeError('Invalid fixed-trip feasibility model: '+model.validate())
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return FeasibilityCertificate(status='INFEASIBLE' if status == cp_model.INFEASIBLE else 'UNKNOWN', native_status=native)
    witness, free = [], defaultdict(dict)
    # Colour the certified interval graph: logical units, never vehicle plates.
    for trip in sorted(trips, key=lambda t: (solver.value(starts[t.trip_id]), t.trip_id)):
        r = by_id[trip.resource_id]
        dispatch = date.fromordinal(solver.value(starts[trip.trip_id]))
        dates = TransitEstimator.dates(dispatch, trip.distance_km, r.source)
        unit = None
        if r.source == 'OWN':
            busy = free[r.resource_id]
            unit = next((u for u in range(min(r.units_available, len(trips))) if busy.get(u, date.min) <= dispatch), None)
            if unit is None:
                raise RuntimeError('Kernel interval witness cannot be coloured')
            busy[unit] = dates.available_again
        witness.append(TemporalWitness(trip_id=trip.trip_id, resource_id=r.resource_id,
            dispatch=dispatch, arrival=dates.arrival, available_again=dates.available_again, unit_index=unit))
    return FeasibilityCertificate(status='FEASIBLE', native_status=native, witness=tuple(sorted(witness, key=lambda w:w.trip_id)))
