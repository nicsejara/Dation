"""Strict, shared CSV parsing. Row numbers include the header."""
import csv
import io
from decimal import Decimal, InvalidOperation


class DispatchValidationError(ValueError):
    pass


def rows_from_csv(contents: bytes, required: list[str], aliases=None):
    try:
        text = contents.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise DispatchValidationError('El CSV debe estar codificado en UTF-8.') from exc
    if not text.strip():
        raise DispatchValidationError('El CSV está vacío.')
    delimiter = ';' if text.splitlines()[0].count(';') > text.splitlines()[0].count(',') else ','
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = [c.strip() for c in (reader.fieldnames or [])]
    if len(columns) != len(set(columns)):
        raise DispatchValidationError('Hay columnas duplicadas.')
    reader.fieldnames = columns
    aliases = aliases or {}
    for old, new in aliases.items():
        if old in columns and new in columns:
            raise DispatchValidationError(f'Usá solamente {new} o su alias {old}, no ambos.')
    normalized = [aliases.get(c, c) for c in columns]
    missing = set(required) - set(normalized)
    if missing:
        raise DispatchValidationError('Faltan columnas: ' + ', '.join(sorted(missing)))
    result = []
    for row_number, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise DispatchValidationError(f'Fila {row_number}: cantidad de columnas incorrecta.')
        item = {aliases.get(k, k): v.strip() for k, v in row.items()}
        if not any(item.values()):
            continue
        for key in required:
            if not item.get(key):
                fail(row_number, key, 'el valor es obligatorio')
        item['_row'] = row_number
        result.append(item)
    if not result:
        raise DispatchValidationError('El CSV no contiene registros.')
    return result, normalized


def fail(row, column, message):
    raise DispatchValidationError(f'Fila {row}, columna {column}: {message}.')


def number(item, key, *, minimum=0, positive=False, integer=False):
    try:
        n = Decimal(str(item[key]).replace(',', '.'))
        if not n.is_finite() or n < minimum or (positive and n == 0):
            raise ValueError
        if integer and n != n.to_integral_value():
            raise ValueError
        if n > 10**9 or n.as_tuple().exponent < -3:
            raise ValueError
        return int(n) if integer else float(n)
    except (InvalidOperation, ValueError):
        fail(item['_row'], key, 'número fuera de rango; hasta 3 decimales y unidades enteras')


def unique(items, key):
    seen = set()
    for item in items:
        if item[key] in seen:
            fail(item['_row'], key, 'identificador duplicado')
        seen.add(item[key])
