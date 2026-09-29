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
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        header = sample.splitlines()[0] if sample.splitlines() else ""

        candidates = {
            ",": header.count(","),
            ";": header.count(";"),
            "\t": header.count("\t"),
            "|": header.count("|"),
        }

        delimiter = max(candidates, key=candidates.get)

        if candidates[delimiter] == 0:
            raise LogisticsValidationError(
                "Could not detect the CSV delimiter. "
                "Supported delimiters are comma, semicolon, tab and pipe."
            )

        return delimiter


def validate_logistics_csv(contents: bytes) -> dict:
    if not contents:
        raise LogisticsValidationError("The CSV file is empty.")

    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise LogisticsValidationError(
            "The file must use UTF-8 encoding."
        ) from exc

    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    if not reader.fieldnames:
        raise LogisticsValidationError("The CSV has no header row.")

    columns = [column.strip() for column in reader.fieldnames]

    missing_columns = [
        column for column in EXPECTED_COLUMNS if column not in columns
    ]
    unexpected_columns = [
        column for column in columns if column not in EXPECTED_COLUMNS
    ]

    if missing_columns:
        raise LogisticsValidationError(
            "Missing required columns: "
            + ", ".join(missing_columns)
            + ". Detected columns: "
            + ", ".join(columns)
        )

    rows = list(reader)

    if not rows:
        raise LogisticsValidationError("The CSV contains no data rows.")

    invalid_numeric = []
    empty_required_cells = 0
    shipment_ids = []
    total_cells = 0

    for row_number, row in enumerate(rows, start=2):
        shipment_id = (row.get("shipment_id") or "").strip()
        shipment_ids.append(shipment_id)

        for column in EXPECTED_COLUMNS:
            total_cells += 1
            value = (row.get(column) or "").strip()

            if not value:
                empty_required_cells += 1

        for column in NUMERIC_COLUMNS:
            value = (row.get(column) or "").strip()

            try:
                number = float(value.replace(",", "."))
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
            f"The CSV contains {empty_required_cells} empty required cells."
        )

    if invalid_numeric:
        first = invalid_numeric[0]

        raise LogisticsValidationError(
            "Invalid numeric value at "
            f"row {first['row']}, column {first['column']}: "
            f"{first['value']!r}."
        )

    duplicate_shipments = len(shipment_ids) - len(set(shipment_ids))

    if duplicate_shipments:
        raise LogisticsValidationError(
            f"The CSV contains {duplicate_shipments} duplicate shipment_id values."
        )

    return {
        "schema": "logistics_v0.1",
        "rows": len(rows),
        "columns": len(columns),
        "column_names": columns,
        "delimiter": {
            ",": "comma",
            ";": "semicolon",
            "\t": "tab",
            "|": "pipe",
        }.get(delimiter, delimiter),
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
        "empty_required_cells": empty_required_cells,
        "duplicate_shipments": duplicate_shipments,
        "total_cells": total_cells,
    }
