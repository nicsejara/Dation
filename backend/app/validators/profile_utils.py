"""Presentation metadata derived from validated Dispatch CSV inputs."""
from datetime import date


MONTHS_SHORT = (
    "",
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)

MONTHS_LONG = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def detected_metadata(contents: bytes, kind: str, columns: list[str]) -> dict:
    try:
        text = contents.decode("utf-8-sig")
        encoding = "UTF-8"
    except UnicodeDecodeError:
        text = contents.decode("utf-8-sig", errors="replace")
        encoding = "No reconocido"
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    raw_columns = [value.strip() for value in first_line.split(delimiter)]

    alias_map = {
        "orders": {
            "shipment_id": "order_id",
            "vehicle_type": "current_vehicle_type",
        },
        "fleet": {},
    }[kind]
    aliases = [
        {"from": alias, "to": canonical}
        for alias, canonical in alias_map.items()
        if alias in raw_columns
    ]

    date_format = None
    if kind == "orders" and "dispatch_date" in columns:
        date_format = (
            "d/m/AAAA"
            if any("/" in line for line in text.splitlines()[1:6])
            else "AAAA-MM-DD"
        )

    return {
        "delimiter": delimiter,
        "encoding": encoding,
        "date_format": date_format,
        "aliases": aliases,
        "columns": len(columns),
    }


def preview_payload(columns: list[str], rows: list[dict]) -> dict:
    visible = [
        column
        for column in columns
        if column not in {"_row", "deadline"}
    ]
    preview = []
    for row in rows[:5]:
        preview.append(
            {
                column: row.get(column)
                for column in visible
            }
        )
    return {
        "columns": visible,
        "rows": preview,
        "shown": len(preview),
    }


def format_orders_label(date_from: str, date_to: str) -> str:
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if start.year == end.year and start.month == end.month:
        return (
            f"Órdenes {start.day}–{end.day} "
            f"{MONTHS_SHORT[start.month]} {start.year}"
        )
    return (
        f"Órdenes {start.day} {MONTHS_SHORT[start.month]} "
        f"– {end.day} {MONTHS_SHORT[end.month]} {end.year}"
    )


def format_fleet_label(today: date | None = None) -> str:
    current = today or date.today()
    return f"Flota {MONTHS_LONG[current.month]} {current.year}"
