"""Single source of truth for Dispatch CSV contracts."""
import csv
import io
from copy import deepcopy

ORDERS_COLUMNS = [
    {
        "name": "order_id",
        "required": True,
        "type": "texto único",
        "rule": "Texto no vacío. También acepta shipment_id.",
        "example": "SHP-0001",
        "description": "Identifica la orden.",
        "aliases": ["shipment_id"],
    },
    {
        "name": "product",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío.",
        "example": "C",
        "description": "Producto que se envía.",
    },
    {
        "name": "quantity_units",
        "required": True,
        "type": "entero",
        "rule": "Entero mayor que 0.",
        "example": "11",
        "description": "Unidades; cada unidad es indivisible.",
    },
    {
        "name": "unit_weight_kg",
        "required": True,
        "type": "número",
        "rule": "Número mayor que 0, hasta 3 decimales.",
        "example": "1400",
        "description": "Peso de una unidad, en kg.",
    },
    {
        "name": "origin",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío.",
        "example": "Buenos Aires",
        "description": "Ciudad de origen.",
    },
    {
        "name": "destination",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío y distinto del origen.",
        "example": "Mendoza",
        "description": "Ciudad de destino.",
    },
    {
        "name": "distance_km",
        "required": True,
        "type": "número",
        "rule": "Mayor que 0 e igual para la misma ruta.",
        "example": "1050",
        "description": "Distancia de ida, en km.",
    },
    {
        "name": "priority",
        "required": True,
        "type": "opción",
        "rule": "High, Normal o Low.",
        "example": "Normal",
        "description": "Prioridad de la orden.",
    },
    {
        "name": "max_delivery_days",
        "required": True,
        "type": "entero",
        "rule": "Entero entre 1 y 90.",
        "example": "2",
        "description": "Días máximos desde disponibilidad hasta entrega.",
    },
    {
        "name": "dispatch_date",
        "required": True,
        "type": "fecha",
        "rule": "AAAA-MM-DD o d/m/AAAA, con día primero.",
        "example": "2026-10-09",
        "description": "Primer día en que la orden puede salir.",
    },
    {
        "name": "current_vehicle_type",
        "required": False,
        "type": "texto",
        "rule": "Opcional. También acepta vehicle_type.",
        "example": "Truck_S",
        "description": "Referencia informada para comparar; no decide el plan.",
        "aliases": ["vehicle_type"],
    },
]

FLEET_COLUMNS = [
    {
        "name": "vehicle_type",
        "required": True,
        "type": "texto único",
        "rule": "Texto no vacío y único.",
        "example": "Truck_L",
        "description": "Tipo de camión.",
    },
    {
        "name": "ownership",
        "required": True,
        "type": "opción",
        "rule": "own (propio) o third_party (tercerizado).",
        "example": "own",
        "description": "Quién opera el vehículo.",
    },
    {
        "name": "capacity_kg",
        "required": True,
        "type": "número",
        "rule": "Número mayor que 0.",
        "example": "25000",
        "description": "Carga máxima por viaje.",
    },
    {
        "name": "cost_per_km",
        "required": True,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "1180",
        "description": "Costo variable por km; combustible incluido.",
    },
    {
        "name": "fixed_trip_cost",
        "required": True,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "48000",
        "description": "Costo fijo por viaje.",
    },
    {
        "name": "units_available",
        "required": True,
        "type": "entero",
        "rule": "Propios: entero >= 0. Tercerizados: vacío = sin límite.",
        "example": "3",
        "description": "Camiones que pueden salir por día.",
    },
    {
        "name": "avg_speed_kmh",
        "required": True,
        "type": "número",
        "rule": "Número mayor que 0.",
        "example": "70",
        "description": "Velocidad media.",
    },
    {
        "name": "driving_hours_per_day",
        "required": True,
        "type": "número",
        "rule": "Entre 1 y 24.",
        "example": "10",
        "description": "Horas de conducción por día.",
    },
    {
        "name": "fuel_l_per_100km",
        "required": True,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "38",
        "description": "Consumo informativo.",
    },
    {
        "name": "co2_kg_per_km",
        "required": True,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "1.02",
        "description": "Emisiones informativas, no certificadas.",
    },
]

CONTRACTS = {
    "orders": {
        "schema": "orders_v1",
        "label": "Órdenes de envío",
        "role": "Qué hay que entregar. Cambian en cada corrida.",
        "columns": ORDERS_COLUMNS,
    },
    "fleet": {
        "schema": "fleet_v1",
        "label": "Flota disponible",
        "role": "Con qué camiones se puede despachar. Se versiona y reutiliza.",
        "columns": FLEET_COLUMNS,
    },
}

LEGACY_MIXED_COLUMNS = {
    "shipment_id",
    "product",
    "quantity_units",
    "unit_weight_kg",
    "origin",
    "destination",
    "distance_km",
    "vehicle_type",
    "vehicle_capacity_kg",
    "cost_per_km",
    "fixed_trip_cost",
    "priority",
    "max_delivery_days",
    "dispatch_date",
}


def get_contract(kind: str) -> dict:
    if kind not in CONTRACTS:
        raise KeyError(kind)
    return deepcopy(CONTRACTS[kind])


def public_contracts() -> dict:
    return {
        kind: get_contract(kind)
        for kind in CONTRACTS
    }


def aliases_for(kind: str) -> dict[str, str]:
    result = {}
    for column in CONTRACTS[kind]["columns"]:
        for alias in column.get("aliases", []):
            result[alias] = column["name"]
    return result


def required_columns(kind: str) -> list[str]:
    return [
        column["name"]
        for column in CONTRACTS[kind]["columns"]
        if column["required"]
    ]


def known_columns(kind: str) -> list[str]:
    return [
        column["name"]
        for column in CONTRACTS[kind]["columns"]
    ]


def template_csv(kind: str) -> str:
    contract = CONTRACTS[kind]
    columns = [column["name"] for column in contract["columns"]]
    example = {
        column["name"]: column["example"]
        for column in contract["columns"]
    }
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=columns,
        delimiter=";",
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerow(example)
    return buffer.getvalue()
