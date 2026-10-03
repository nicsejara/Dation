"""Shared CSV parsing and accumulated validation for Dispatch inputs."""
import csv
import io
from decimal import Decimal, InvalidOperation

from app.validators.contracts import (
    LEGACY_MIXED_COLUMNS,
    aliases_for,
    get_contract,
    known_columns,
    required_columns,
)


MAX_PROBLEMS = 100


class DispatchValidationError(ValueError):
    pass


class ValidationProblems:
    def __init__(self, limit: int = MAX_PROBLEMS):
        self.limit = limit
        self.errors = []
        self.warnings = []
        self.error_count = 0
        self.warning_count = 0

    def _append(self, target, kind, problem):
        if kind == "error":
            self.error_count += 1
        else:
            self.warning_count += 1
        if len(self.errors) + len(self.warnings) < self.limit:
            target.append(problem)

    def error(self, code, message, *, row=None, column=None, hint=None, value=None):
        self._append(
            self.errors,
            "error",
            problem(code, message, row=row, column=column, hint=hint, value=value),
        )

    def warning(self, code, message, *, row=None, column=None, hint=None, value=None):
        self._append(
            self.warnings,
            "warning",
            problem(code, message, row=row, column=column, hint=hint, value=value),
        )

    @property
    def truncated(self):
        return (
            self.error_count + self.warning_count
            > len(self.errors) + len(self.warnings)
        )


def problem(code, message, *, row=None, column=None, hint=None, value=None):
    payload = {
        "code": code,
        "row": row,
        "column": column,
        "message": message,
        "hint": hint,
    }
    if value is not None:
        payload["value"] = str(value)
    return payload


def issue_text(issue: dict) -> str:
    prefix = []
    if issue.get("row") is not None:
        prefix.append(f"Fila {issue['row']}")
    if issue.get("column"):
        prefix.append(f"columna {issue['column']}")
    start = ", ".join(prefix)
    return f"{start}: {issue['message']}" if start else issue["message"]


def _detected_format(kind: str, raw_columns: list[str], normalized: list[str]) -> str:
    raw_set = set(raw_columns)
    if len(LEGACY_MIXED_COLUMNS.intersection(raw_set)) >= 12:
        return "legacy_mixed"

    normalized_set = set(normalized)
    required = set(required_columns(kind))
    if required and required.issubset(normalized_set):
        return get_contract(kind)["schema"]

    known = set(known_columns(kind))
    if normalized and len(known.intersection(normalized)) >= max(2, len(known) // 2):
        return get_contract(kind)["schema"]
    return "unknown"


def parse_csv_report(contents: bytes, kind: str, problems: ValidationProblems):
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        problems.error(
            "INVALID_ENCODING",
            "El archivo no está codificado en UTF-8.",
            hint="Guardalo como CSV UTF-8 y volvé a cargarlo.",
        )
        return [], [], ",", "unknown"

    if not text.strip():
        problems.error(
            "EMPTY_FILE",
            "El archivo CSV está vacío.",
            hint="Usá la plantilla y agregá al menos una fila de datos.",
        )
        return [], [], ",", "unknown"

    first = text.splitlines()[0]
    comma_count = first.count(",")
    semicolon_count = first.count(";")
    if comma_count == 0 and semicolon_count == 0:
        problems.error(
            "INVALID_DELIMITER",
            "No se pudo detectar el separador del CSV.",
            row=1,
            hint="Usá coma o punto y coma como separador.",
        )
        return [], [], ",", "unknown"

    delimiter = ";" if semicolon_count > comma_count else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = list(reader)
    if not all_rows:
        problems.error("EMPTY_FILE", "El archivo CSV está vacío.")
        return [], [], delimiter, "unknown"

    raw_columns = [column.strip() for column in all_rows[0]]
    if not raw_columns or not any(raw_columns):
        problems.error(
            "MISSING_HEADER",
            "El CSV no contiene encabezados válidos.",
            row=1,
            hint="La primera fila debe contener los nombres de columnas.",
        )
        return [], [], delimiter, "unknown"

    seen = set()
    for column in raw_columns:
        if column in seen:
            problems.error(
                "DUPLICATE_COLUMN",
                f"La columna '{column}' está repetida.",
                row=1,
                column=column,
                hint="Dejá una sola columna con ese encabezado.",
            )
        seen.add(column)

    aliases = aliases_for(kind)
    for alias, canonical in aliases.items():
        if alias in raw_columns and canonical in raw_columns:
            problems.error(
                "ALIAS_CONFLICT",
                f"Están presentes '{alias}' y '{canonical}'.",
                row=1,
                column=canonical,
                hint=f"Usá solamente '{canonical}' o su alias '{alias}'.",
            )

    normalized = [aliases.get(column, column) for column in raw_columns]
    detected = _detected_format(kind, raw_columns, normalized)

    if detected == "legacy_mixed":
        problems.error(
            "LEGACY_MIXED",
            "Este archivo es del formato anterior, que mezcla órdenes y flota.",
            row=1,
            hint="Separalo en dos archivos usando las plantillas nuevas.",
        )
        return [], normalized, delimiter, detected

    required = set(required_columns(kind))
    for column in sorted(required - set(normalized)):
        problems.error(
            "MISSING_COLUMN",
            f"Falta la columna obligatoria '{column}'.",
            row=1,
            column=column,
            hint="No cambies los encabezados de la plantilla.",
        )

    known = set(known_columns(kind))
    for column in normalized:
        if column not in known:
            problems.warning(
                "EXTRA_COLUMN",
                f"La columna '{column}' no forma parte del contrato.",
                row=1,
                column=column,
                hint="Podés dejarla; Dation no la usa para decidir.",
            )

    data = []
    for row_number, values in enumerate(all_rows[1:], 2):
        if not values or not any(str(value).strip() for value in values):
            continue
        if len(values) != len(raw_columns):
            problems.error(
                "ROW_LENGTH",
                "La cantidad de valores no coincide con los encabezados.",
                row=row_number,
                hint=f"Esperábamos {len(raw_columns)} valores y recibimos {len(values)}.",
            )
            continue
        item = {
            normalized[index]: str(value).strip()
            for index, value in enumerate(values)
        }
        item["_row"] = row_number
        for column in required:
            if column == "units_available" and kind == "fleet":
                continue
            if not item.get(column, ""):
                problems.error(
                    "REQUIRED_EMPTY",
                    "El valor es obligatorio.",
                    row=row_number,
                    column=column,
                    hint="Completá la celda y volvé a validar.",
                )
        data.append(item)

    if not data:
        problems.error(
            "NO_DATA_ROWS",
            "El CSV no contiene registros de datos.",
            hint="Agregá al menos una fila debajo del encabezado.",
        )

    return data, normalized, delimiter, detected


def parse_number(
    item,
    key,
    problems,
    *,
    minimum=0,
    positive=False,
    integer=False,
    allow_empty=False,
    delimiter=";",
):
    raw = item.get(key, "")
    if raw == "":
        if allow_empty:
            return None
        return None

    normalized = raw.replace(",", ".") if delimiter == ";" else raw
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        problems.error(
            "INVALID_NUMBER",
            f"'{raw}' no es un número válido.",
            row=item["_row"],
            column=key,
            hint="Usá sólo dígitos y un separador decimal válido.",
            value=raw,
        )
        return None

    if not value.is_finite():
        problems.error(
            "INVALID_NUMBER",
            f"'{raw}' no es un número finito.",
            row=item["_row"],
            column=key,
            hint="Reemplazalo por un valor numérico.",
            value=raw,
        )
        return None

    if value.as_tuple().exponent < -3:
        problems.error(
            "TOO_MANY_DECIMALS",
            "El valor tiene más de 3 decimales.",
            row=item["_row"],
            column=key,
            hint="Redondeá el valor a un máximo de 3 decimales.",
            value=raw,
        )
        return None

    if value > 10**9 or value < minimum or (positive and value == 0):
        relation = "mayor que 0" if positive else f"mayor o igual que {minimum}"
        problems.error(
            "OUT_OF_RANGE",
            f"El valor debe ser {relation} y menor o igual que 1.000.000.000.",
            row=item["_row"],
            column=key,
            hint="Revisá la unidad y el rango del dato.",
            value=raw,
        )
        return None

    if integer and value != value.to_integral_value():
        problems.error(
            "NON_INTEGER",
            "El valor debe ser un entero.",
            row=item["_row"],
            column=key,
            hint="No uses decimales en esta columna.",
            value=raw,
        )
        return None

    return int(value) if integer else float(value)


def duplicate_values(items, key, problems):
    seen = {}
    for item in items:
        value = item.get(key)
        if not value:
            continue
        if value in seen:
            problems.error(
                "DUPLICATE_ID",
                f"El identificador '{value}' está repetido.",
                row=item["_row"],
                column=key,
                hint=f"Debe ser único; también aparece en la fila {seen[value]}.",
                value=value,
            )
        else:
            seen[value] = item["_row"]


# Legacy helpers kept for external consumers while validation migrates to reports.
def rows_from_csv(contents: bytes, required: list[str], aliases=None):
    aliases = aliases or {}
    text = contents.decode("utf-8-sig")
    delimiter = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = [c.strip() for c in (reader.fieldnames or [])]
    reader.fieldnames = columns
    normalized = [aliases.get(c, c) for c in columns]
    missing = set(required) - set(normalized)
    if missing:
        raise DispatchValidationError("Faltan columnas: " + ", ".join(sorted(missing)))
    rows = []
    for row_number, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise DispatchValidationError(f"Fila {row_number}: cantidad de columnas incorrecta.")
        item = {aliases.get(k, k): v.strip() for k, v in row.items()}
        item["_row"] = row_number
        rows.append(item)
    return rows, normalized


def fail(row, column, message):
    raise DispatchValidationError(f"Fila {row}, columna {column}: {message}.")


def number(item, key, *, minimum=0, positive=False, integer=False):
    try:
        value = Decimal(str(item[key]).replace(",", "."))
        if not value.is_finite() or value < minimum or (positive and value == 0):
            raise ValueError
        if integer and value != value.to_integral_value():
            raise ValueError
        if value > 10**9 or value.as_tuple().exponent < -3:
            raise ValueError
        return int(value) if integer else float(value)
    except (InvalidOperation, ValueError):
        fail(item["_row"], key, "número fuera de rango; hasta 3 decimales y unidades enteras")


def unique(items, key):
    seen = set()
    for item in items:
        if item[key] in seen:
            fail(item["_row"], key, "identificador duplicado")
        seen.add(item[key])
