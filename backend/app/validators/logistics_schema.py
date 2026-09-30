import csv
import io


EXPECTED_COLUMNS = [
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
]

NUMERIC_COLUMNS = [
    "quantity_units",
    "unit_weight_kg",
    "distance_km",
    "vehicle_capacity_kg",
    "cost_per_km",
    "fixed_trip_cost",
    "max_delivery_days",
]


class LogisticsValidationError(ValueError):
    pass


def _detect_delimiter(text: str) -> str:
    sample = text[:8192]

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|",
        )
        return dialect.delimiter
    except csv.Error:
        header = (
            sample.splitlines()[0]
            if sample.splitlines()
            else ""
        )

        candidates = {
            ",": header.count(","),
            ";": header.count(";"),
            "\t": header.count("\t"),
            "|": header.count("|"),
        }

        delimiter = max(
            candidates,
            key=candidates.get,
        )

        if candidates[delimiter] == 0:
            raise LogisticsValidationError(
                "No se pudo detectar el separador del CSV. "
                "Se admiten coma, punto y coma, tabulación y pipe."
            )

        return delimiter


def parse_logistics_csv(contents: bytes) -> dict:
    if not contents:
        raise LogisticsValidationError(
            "El archivo CSV está vacío."
        )

    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LogisticsValidationError(
            "El archivo debe utilizar codificación UTF-8."
        ) from exc

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(
        io.StringIO(text),
        delimiter=delimiter,
    )

    if not reader.fieldnames:
        raise LogisticsValidationError(
            "El CSV no contiene una fila de encabezados."
        )

    columns = [
        column.strip()
        for column in reader.fieldnames
    ]

    rows = list(reader)

    return {
        "rows": rows,
        "columns": columns,
        "delimiter": delimiter,
    }


def validate_logistics_csv(contents: bytes) -> dict:
    parsed = parse_logistics_csv(contents)
    rows = parsed["rows"]
    columns = parsed["columns"]
    delimiter = parsed["delimiter"]

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in columns
    ]
    unexpected_columns = [
        column
        for column in columns
        if column not in EXPECTED_COLUMNS
    ]

    if missing_columns:
        raise LogisticsValidationError(
            "Faltan columnas requeridas: "
            + ", ".join(missing_columns)
            + ". Columnas detectadas: "
            + ", ".join(columns)
        )

    if not rows:
        raise LogisticsValidationError(
            "El CSV no contiene registros de datos."
        )

    invalid_numeric = []
    empty_required_cells = 0
    shipment_ids = []
    total_cells = 0

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        shipment_id = (
            row.get("shipment_id") or ""
        ).strip()
        shipment_ids.append(shipment_id)

        for column in EXPECTED_COLUMNS:
            total_cells += 1
            value = (
                row.get(column) or ""
            ).strip()

            if not value:
                empty_required_cells += 1

        for column in NUMERIC_COLUMNS:
            value = (
                row.get(column) or ""
            ).strip()

            try:
                number = float(
                    value.replace(",", ".")
                )

                if number < 0:
                    raise ValueError

            except ValueError:
                invalid_numeric.append(
                    {
                        "row": row_number,
                        "column": column,
                        "value": value,
                    }
                )

    if empty_required_cells:
        raise LogisticsValidationError(
            "El CSV contiene "
            f"{empty_required_cells} celdas obligatorias vacías."
        )

    if invalid_numeric:
        first = invalid_numeric[0]

        raise LogisticsValidationError(
            "Valor numérico inválido en la fila "
            f"{first['row']}, columna "
            f"{first['column']}: "
            f"{first['value']!r}."
        )

    duplicate_shipments = (
        len(shipment_ids)
        - len(set(shipment_ids))
    )

    if duplicate_shipments:
        raise LogisticsValidationError(
            "El CSV contiene "
            f"{duplicate_shipments} valores shipment_id duplicados."
        )

    return {
        "schema": "logistics_v0.1",
        "rows": len(rows),
        "columns": len(columns),
        "column_names": columns,
        "delimiter": {
            ",": "coma",
            ";": "punto_y_coma",
            "\t": "tabulacion",
            "|": "pipe",
        }.get(delimiter, delimiter),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "empty_required_cells": empty_required_cells,
        "duplicate_shipments": duplicate_shipments,
        "total_cells": total_cells,
    }
