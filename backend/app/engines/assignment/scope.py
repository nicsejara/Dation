from collections import Counter
from datetime import date


ORDER_FILTER_FIELDS = {
    "estimated_dispatch_date": {
        "label": "Período",
        "type": "date",
        "quick": True,
    },
    "delivery_due_date": {
        "label": "Fecha objetivo",
        "type": "date",
        "quick": False,
    },
    "destination": {
        "label": "Destino",
        "type": "category",
        "quick": True,
    },
    "origin": {
        "label": "Origen",
        "type": "category",
        "quick": True,
    },
    "product": {
        "label": "Producto",
        "type": "category",
        "quick": True,
    },
    "priority": {
        "label": "Prioridad",
        "type": "category",
        "quick": False,
    },
    "quantity_units": {
        "label": "Cantidad",
        "type": "number",
        "quick": False,
    },
    "unit_weight_kg": {
        "label": "Peso por unidad",
        "type": "number",
        "quick": False,
    },
    "distance_km": {
        "label": "Distancia",
        "type": "number",
        "quick": False,
    },
}


def _values(filter_item):
    value = filter_item.get("resolved")
    if value is None:
        value = filter_item.get("value")
    return value or []


def _coerce_date(value):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def apply_order_scope(records, filters):
    result = list(records)
    for filter_item in filters or []:
        column = filter_item.get("column")
        metadata = ORDER_FILTER_FIELDS.get(column)
        if not metadata:
            raise ValueError(f"La columna {column!r} no admite filtros de alcance.")
        if filter_item.get("type") != metadata["type"]:
            raise ValueError(
                f"El tipo de filtro para {column} no coincide con el contrato."
            )

        values = _values(filter_item)
        field_type = metadata["type"]
        if field_type == "category":
            selected = {str(value) for value in values if str(value) != ""}
            if selected:
                result = [
                    row
                    for row in result
                    if str(row.get(column, "")) in selected
                ]
        elif field_type == "number":
            if len(values) != 2:
                raise ValueError(
                    f"El filtro numérico {column} requiere mínimo y máximo."
                )
            lower = float(values[0])
            upper = float(values[1])
            if lower > upper:
                lower, upper = upper, lower
            result = [
                row
                for row in result
                if row.get(column) not in (None, "")
                and lower <= float(row[column]) <= upper
            ]
        elif field_type == "date":
            if len(values) != 2:
                raise ValueError(
                    f"El filtro de fecha {column} requiere desde y hasta."
                )
            start = _coerce_date(values[0])
            end = _coerce_date(values[1])
            if not start or not end:
                raise ValueError(
                    f"El rango de fecha de {column} no es válido."
                )
            if start > end:
                start, end = end, start
            result = [
                row
                for row in result
                if (
                    _coerce_date(row.get(column)) is not None
                    and start <= _coerce_date(row.get(column)) <= end
                )
            ]
    return result


def _field_catalog(records, completeness):
    fields = []
    for column, metadata in ORDER_FILTER_FIELDS.items():
        source = (completeness or {}).get(column, {})
        if not source.get("present"):
            continue
        values = [row.get(column) for row in records if row.get(column) not in (None, "")]
        if not values:
            continue
        item = {
            "column": column,
            "label": metadata["label"],
            "type": metadata["type"],
            "quick": metadata["quick"],
        }
        if metadata["type"] == "category":
            counts = Counter(str(value) for value in values)
            item["values"] = [
                {"value": value, "count": count}
                for value, count in sorted(
                    counts.items(),
                    key=lambda current: (-current[1], current[0].lower()),
                )[:100]
            ]
        elif metadata["type"] == "number":
            numeric = [float(value) for value in values]
            item["min"] = min(numeric)
            item["max"] = max(numeric)
        else:
            dates = [current for current in (_coerce_date(value) for value in values) if current]
            if not dates:
                continue
            item["min"] = min(dates).isoformat()
            item["max"] = max(dates).isoformat()
        fields.append(item)
    return fields


def scope_preview(orders_report, fleet_report, filters=None):
    records = orders_report["records"]
    filtered = apply_order_scope(records, filters or [])
    fleet_records = fleet_report["records"]
    ownership = Counter(
        row.get("ownership")
        for row in fleet_records
        if row.get("ownership")
    )
    return {
        "orders": {
            "included": len(filtered),
            "total": len(records),
        },
        "fleet": {
            "included": len(fleet_records),
            "total": len(fleet_records),
            "own": ownership.get("own", 0),
            "third_party": ownership.get("third_party", 0),
        },
        "fields": _field_catalog(records, orders_report.get("completeness")),
        "filters": filters or [],
        "valid": bool(filtered),
    }
