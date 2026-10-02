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

TEMPLATE_ROWS = {
    "orders": [
        {
            "order_id": "SHP-0001",
            "product": "A",
            "quantity_units": "10",
            "unit_weight_kg": "500",
            "origin": "Cordoba",
            "destination": "Villa Maria",
            "distance_km": "150",
            "priority": "Normal",
            "max_delivery_days": "3",
            "dispatch_date": "2026-10-01",
            "current_vehicle_type": "Truck_M",
        },
        {
            "order_id": "SHP-0002",
            "product": "B",
            "quantity_units": "8",
            "unit_weight_kg": "900",
            "origin": "Cordoba",
            "destination": "San Luis",
            "distance_km": "420",
            "priority": "High",
            "max_delivery_days": "2",
            "dispatch_date": "2026-10-02",
            "current_vehicle_type": "Truck_L",
        },
        {
            "order_id": "SHP-0003",
            "product": "C",
            "quantity_units": "12",
            "unit_weight_kg": "1400",
            "origin": "Rosario",
            "destination": "La Plata",
            "distance_km": "330",
            "priority": "Low",
            "max_delivery_days": "4",
            "dispatch_date": "2026-10-03",
            "current_vehicle_type": "Truck_S",
        },
        {
            "order_id": "SHP-0004",
            "product": "A",
            "quantity_units": "6",
            "unit_weight_kg": "500",
            "origin": "Buenos Aires",
            "destination": "Rio Cuarto",
            "distance_km": "610",
            "priority": "Normal",
            "max_delivery_days": "3",
            "dispatch_date": "2026-10-04",
            "current_vehicle_type": "Truck_XL",
        },
        {
            "order_id": "SHP-0005",
            "product": "B",
            "quantity_units": "15",
            "unit_weight_kg": "900",
            "origin": "Cordoba",
            "destination": "Santa Fe",
            "distance_km": "350",
            "priority": "Normal",
            "max_delivery_days": "2",
            "dispatch_date": "2026-10-05",
            "current_vehicle_type": "Third_Party_L",
        },
    ],
    "fleet": [
        {
            "vehicle_type": "Truck_S",
            "ownership": "own",
            "capacity_kg": "8000",
            "cost_per_km": "850",
            "fixed_trip_cost": "30000",
            "units_available": "4",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "fuel_l_per_100km": "25",
            "co2_kg_per_km": "0.75",
        },
        {
            "vehicle_type": "Truck_M",
            "ownership": "own",
            "capacity_kg": "15000",
            "cost_per_km": "980",
            "fixed_trip_cost": "38000",
            "units_available": "4",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "fuel_l_per_100km": "30",
            "co2_kg_per_km": "0.85",
        },
        {
            "vehicle_type": "Truck_L",
            "ownership": "own",
            "capacity_kg": "25000",
            "cost_per_km": "1180",
            "fixed_trip_cost": "48000",
            "units_available": "3",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "fuel_l_per_100km": "38",
            "co2_kg_per_km": "1.02",
        },
        {
            "vehicle_type": "Truck_XL",
            "ownership": "own",
            "capacity_kg": "30000",
            "cost_per_km": "1300",
            "fixed_trip_cost": "52000",
            "units_available": "1",
            "avg_speed_kmh": "65",
            "driving_hours_per_day": "10",
            "fuel_l_per_100km": "42",
            "co2_kg_per_km": "1.15",
        },
        {
            "vehicle_type": "Third_Party_L",
            "ownership": "third_party",
            "capacity_kg": "25000",
            "cost_per_km": "1534",
            "fixed_trip_cost": "62400",
            "units_available": "",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "fuel_l_per_100km": "38",
            "co2_kg_per_km": "1.02",
        },
    ],
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
    examples = TEMPLATE_ROWS[kind]
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=columns,
        delimiter=";",
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerows(examples)
    return buffer.getvalue()
