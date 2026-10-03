"""Single source of truth for the Logistics Data Pack CSV contracts."""
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
        "description": "Identifica de forma única la orden.",
        "aliases": ["shipment_id"],
        "used_by": ["assignment", "scheduling", "final_assignment"],
    },
    {
        "name": "product",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío.",
        "example": "Producto A",
        "description": "Producto que se transporta.",
        "used_by": ["assignment", "final_assignment"],
    },
    {
        "name": "quantity_units",
        "required": True,
        "type": "entero",
        "rule": "Entero mayor que 0.",
        "example": "15",
        "description": "Cantidad de unidades de la orden.",
        "used_by": ["assignment"],
    },
    {
        "name": "unit_weight_kg",
        "required": True,
        "type": "número",
        "rule": "Número mayor que 0, hasta 3 decimales.",
        "example": "800",
        "description": "Peso de cada unidad en kg.",
        "used_by": ["assignment"],
    },
    {
        "name": "origin",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío.",
        "example": "Cordoba",
        "description": "Site desde el que sale la carga.",
        "used_by": ["assignment", "scheduling"],
    },
    {
        "name": "destination",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío y distinto del origen.",
        "example": "Mendoza",
        "description": "Ciudad de destino.",
        "used_by": ["assignment", "scheduling"],
    },
    {
        "name": "distance_km",
        "required": True,
        "type": "número",
        "rule": "Mayor que 0 e igual para la misma ruta.",
        "example": "650",
        "description": "Distancia de ida entre origen y destino.",
        "used_by": ["assignment", "scheduling"],
    },
    {
        "name": "estimated_dispatch_date",
        "required": False,
        "type": "fecha",
        "rule": "AAAA-MM-DD o d/m/AAAA.",
        "example": "2026-10-05",
        "description": "Fecha estimada desde la que se espera despachar la orden.",
        "aliases": ["ready_date", "dispatch_date"],
        "used_by": ["scheduling"],
        "unlock_label": "Planificación",
    },
    {
        "name": "priority",
        "required": False,
        "type": "opción",
        "rule": "High, Normal o Low.",
        "example": "Normal",
        "description": "Prioridad operativa para análisis posteriores.",
        "used_by": ["scheduling"],
        "unlock_label": "Planificación avanzada",
    },
    {
        "name": "delivery_due_date",
        "required": False,
        "type": "fecha",
        "rule": "AAAA-MM-DD o d/m/AAAA.",
        "example": "2026-10-07",
        "description": "Fecha objetivo de entrega para evaluar nivel de servicio.",
        "used_by": ["scheduling"],
        "unlock_label": "SLA de planificación",
    },
]

FLEET_COLUMNS = [
    {
        "name": "vehicle_id",
        "required": True,
        "type": "texto único",
        "rule": "Texto no vacío y único por vehículo.",
        "example": "VEH-001",
        "description": "Identificador interno del camión real.",
        "used_by": ["assignment", "scheduling", "final_assignment"],
    },
    {
        "name": "license_plate",
        "required": False,
        "type": "texto",
        "rule": "Patente o dominio del vehículo.",
        "example": "AE123XX",
        "description": "Identifica la unidad física en la asignación final.",
        "used_by": ["final_assignment"],
        "unlock_label": "Asignación final",
    },
    {
        "name": "vehicle_type",
        "required": True,
        "type": "texto",
        "rule": "Texto no vacío.",
        "example": "Truck_L",
        "description": "Tamaño o categoría logística del camión.",
        "used_by": ["assignment", "scheduling", "final_assignment"],
    },
    {
        "name": "ownership",
        "required": True,
        "type": "opción",
        "rule": "own (propio) o third_party (tercerizado).",
        "example": "own",
        "description": "Indica si la unidad es propia o de un proveedor.",
        "used_by": ["assignment", "final_assignment"],
    },
    {
        "name": "provider_name",
        "required": False,
        "type": "texto",
        "rule": "Texto libre; puede quedar vacío para flota propia.",
        "example": "Transportes Norte",
        "description": "Proveedor responsable cuando la unidad es tercerizada.",
        "used_by": ["final_assignment"],
        "unlock_label": "Detalle de ejecución",
    },
    {
        "name": "base_site",
        "required": True,
        "type": "texto",
        "rule": "Site operativo del vehículo.",
        "example": "Cordoba",
        "description": "Base desde la que opera el camión.",
        "used_by": ["assignment", "scheduling"],
    },
    {
        "name": "capacity_kg",
        "required": True,
        "type": "número",
        "rule": "Número mayor que 0.",
        "example": "25000",
        "description": "Capacidad máxima de carga por viaje.",
        "used_by": ["assignment"],
    },
    {
        "name": "capacity_m3",
        "required": False,
        "type": "número",
        "rule": "Número mayor que 0 o vacío.",
        "example": "65",
        "description": "Capacidad volumétrica para modelos futuros.",
        "used_by": ["assignment"],
        "unlock_label": "Restricción volumétrica",
    },
    {
        "name": "cost_per_km",
        "required": False,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "1180",
        "description": "Costo variable por km.",
        "used_by": ["assignment"],
        "unlock_label": "Objetivo Costo",
    },
    {
        "name": "fixed_trip_cost",
        "required": False,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "48000",
        "description": "Costo fijo por viaje.",
        "used_by": ["assignment"],
        "unlock_label": "Objetivo Costo",
    },
    {
        "name": "fuel_l_per_100km",
        "required": False,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "38",
        "description": "Consumo estimado cada 100 km.",
        "used_by": ["assignment"],
        "unlock_label": "Análisis de combustible",
    },
    {
        "name": "co2_kg_per_km",
        "required": False,
        "type": "número",
        "rule": "Número mayor o igual que 0.",
        "example": "1.02",
        "description": "Factor estimado de emisiones por km.",
        "used_by": ["assignment"],
        "unlock_label": "Objetivo CO₂",
    },
    {
        "name": "avg_speed_kmh",
        "required": False,
        "type": "número",
        "rule": "Número mayor que 0.",
        "example": "70",
        "description": "Velocidad media usada para planificación.",
        "used_by": ["scheduling"],
        "unlock_label": "Planificación",
    },
    {
        "name": "driving_hours_per_day",
        "required": False,
        "type": "número",
        "rule": "Entre 1 y 24.",
        "example": "10",
        "description": "Horas de conducción disponibles por día.",
        "used_by": ["scheduling"],
        "unlock_label": "Planificación",
    },
    {
        "name": "status",
        "required": False,
        "type": "opción",
        "rule": "available, maintenance o unavailable.",
        "example": "available",
        "description": "Estado operativo actual del vehículo.",
        "used_by": ["scheduling", "final_assignment"],
        "unlock_label": "Planificación",
    },
    {
        "name": "available_from",
        "required": False,
        "type": "fecha",
        "rule": "AAAA-MM-DD o d/m/AAAA.",
        "example": "2026-10-01",
        "description": "Inicio de disponibilidad de la unidad.",
        "used_by": ["scheduling", "final_assignment"],
        "unlock_label": "Planificación",
    },
    {
        "name": "available_until",
        "required": False,
        "type": "fecha",
        "rule": "AAAA-MM-DD o d/m/AAAA.",
        "example": "2026-10-31",
        "description": "Fin de disponibilidad conocida de la unidad.",
        "used_by": ["scheduling", "final_assignment"],
        "unlock_label": "Asignación final",
    },
]

CONTRACTS = {
    "orders": {
        "schema": "orders_v3",
        "label": "Órdenes",
        "role": "Demanda a transportar. Las columnas temporales son opcionales hasta Planificación.",
        "columns": ORDERS_COLUMNS,
    },
    "fleet": {
        "schema": "fleet_v3",
        "label": "Flota",
        "role": "Una fila por camión real, propio o tercerizado. Sin pools.",
        "columns": FLEET_COLUMNS,
    },
}

TEMPLATE_ROWS = {
    "orders": [
        {
            "order_id": "SHP-0001",
            "product": "Producto A",
            "quantity_units": "15",
            "unit_weight_kg": "800",
            "origin": "Cordoba",
            "destination": "Mendoza",
            "distance_km": "650",
            "estimated_dispatch_date": "2026-10-05",
            "priority": "Normal",
            "delivery_due_date": "2026-10-07",
        },
        {
            "order_id": "SHP-0002",
            "product": "Producto B",
            "quantity_units": "10",
            "unit_weight_kg": "1200",
            "origin": "Cordoba",
            "destination": "Mendoza",
            "distance_km": "650",
            "estimated_dispatch_date": "2026-10-05",
            "priority": "High",
            "delivery_due_date": "2026-10-06",
        },
        {
            "order_id": "SHP-0003",
            "product": "Producto C",
            "quantity_units": "20",
            "unit_weight_kg": "500",
            "origin": "Cordoba",
            "destination": "Rosario",
            "distance_km": "400",
            "estimated_dispatch_date": "2026-10-06",
            "priority": "Normal",
            "delivery_due_date": "2026-10-08",
        },
        {
            "order_id": "SHP-0004",
            "product": "Producto A",
            "quantity_units": "8",
            "unit_weight_kg": "800",
            "origin": "Cordoba",
            "destination": "Villa Maria",
            "distance_km": "150",
            "estimated_dispatch_date": "2026-10-06",
            "priority": "Low",
            "delivery_due_date": "2026-10-09",
        },
        {
            "order_id": "SHP-0005",
            "product": "Producto B",
            "quantity_units": "18",
            "unit_weight_kg": "1200",
            "origin": "Cordoba",
            "destination": "Buenos Aires",
            "distance_km": "700",
            "estimated_dispatch_date": "2026-10-07",
            "priority": "Normal",
            "delivery_due_date": "2026-10-09",
        },
    ],
    "fleet": [
        {
            "vehicle_id": "VEH-001",
            "license_plate": "AE123XX",
            "vehicle_type": "Truck_L",
            "ownership": "own",
            "provider_name": "",
            "base_site": "Cordoba",
            "capacity_kg": "25000",
            "capacity_m3": "65",
            "cost_per_km": "1180",
            "fixed_trip_cost": "48000",
            "fuel_l_per_100km": "38",
            "co2_kg_per_km": "1.02",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "status": "available",
            "available_from": "2026-10-01",
            "available_until": "2026-10-31",
        },
        {
            "vehicle_id": "VEH-002",
            "license_plate": "AF456YY",
            "vehicle_type": "Truck_L",
            "ownership": "own",
            "provider_name": "",
            "base_site": "Cordoba",
            "capacity_kg": "25000",
            "capacity_m3": "65",
            "cost_per_km": "1180",
            "fixed_trip_cost": "48000",
            "fuel_l_per_100km": "38",
            "co2_kg_per_km": "1.02",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "status": "available",
            "available_from": "2026-10-01",
            "available_until": "2026-10-31",
        },
        {
            "vehicle_id": "VEH-003",
            "license_plate": "AG789ZZ",
            "vehicle_type": "Truck_M",
            "ownership": "own",
            "provider_name": "",
            "base_site": "Cordoba",
            "capacity_kg": "15000",
            "capacity_m3": "42",
            "cost_per_km": "920",
            "fixed_trip_cost": "35000",
            "fuel_l_per_100km": "30",
            "co2_kg_per_km": "0.80",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "status": "available",
            "available_from": "2026-10-01",
            "available_until": "2026-10-31",
        },
        {
            "vehicle_id": "VEH-101",
            "license_plate": "AH111AA",
            "vehicle_type": "Truck_L",
            "ownership": "third_party",
            "provider_name": "Transportes Norte",
            "base_site": "Cordoba",
            "capacity_kg": "25000",
            "capacity_m3": "65",
            "cost_per_km": "1534",
            "fixed_trip_cost": "62400",
            "fuel_l_per_100km": "38",
            "co2_kg_per_km": "1.02",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "status": "available",
            "available_from": "2026-10-01",
            "available_until": "2026-10-31",
        },
        {
            "vehicle_id": "VEH-102",
            "license_plate": "AI222BB",
            "vehicle_type": "Truck_M",
            "ownership": "third_party",
            "provider_name": "Logistica Centro",
            "base_site": "Cordoba",
            "capacity_kg": "15000",
            "capacity_m3": "42",
            "cost_per_km": "1270",
            "fixed_trip_cost": "52000",
            "fuel_l_per_100km": "30",
            "co2_kg_per_km": "0.80",
            "avg_speed_kmh": "70",
            "driving_hours_per_day": "10",
            "status": "available",
            "available_from": "2026-10-01",
            "available_until": "2026-10-31",
        },
    ],
}


# Retained only to detect the pre-Data-Pack mixed format and give a clear error.
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
