import hashlib
from pathlib import Path


KNOWLEDGE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
    / "logistics"
)


def _all_knowledge_files() -> list[Path]:
    files = sorted(KNOWLEDGE_ROOT.glob("*.md"))

    if not files:
        raise RuntimeError("Logistics knowledge base is missing.")

    return files


def _knowledge_version(files: list[Path]) -> str:
    hasher = hashlib.sha256()

    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")

    return f"v0.4-{hasher.hexdigest()[:12]}"


def _load_selected(files: list[Path]) -> dict:
    all_files = _all_knowledge_files()
    parts: list[str] = []

    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        parts.append(
            f"\n\n---\nSOURCE: {path.name}\n---\n{content}"
        )

    return {
        "name": "logistics_interpreter",
        "version": _knowledge_version(all_files),
        "files": [path.name for path in files],
        "content": "".join(parts).strip(),
    }


def load_logistics_knowledge() -> dict:
    return _load_selected(_all_knowledge_files())


def load_logistics_knowledge_for_question(question: str) -> dict:
    files_by_name = {
        path.name: path
        for path in _all_knowledge_files()
    }

    selected = {
        "00_interpreter_contract.md",
    }

    q = question.lower()

    metric_terms = (
        "costo",
        "cost",
        "viaje",
        "distancia",
        "kilómetro",
        "kilometro",
        "fórmula",
        "formula",
        "calcula",
        "peso",
        "capacidad",
    )
    decision_terms = (
        "por qué",
        "porque",
        "mejor",
        "recomend",
        "alternativa",
        "trade",
        "camión",
        "camion",
        "vehículo",
        "vehiculo",
        "envío",
        "envio",
        "ahorro",
        "driver",
        "cambio",
        "ponderación",
        "ponderacion",
        "peso",
        "sensibilidad",
        "70/30",
        "100/0",
        "0/100",
    )
    limit_terms = (
        "supuesto",
        "limit",
        "riesgo",
        "falta",
        "faltan",
        "real",
        "operación",
        "operacion",
        "tiempo",
        "prioridad",
        "fecha",
        "disponibilidad",
        "sla",
        "clima",
    )

    if any(term in q for term in metric_terms):
        selected.add("02_metrics_and_formulas.md")

    if any(term in q for term in decision_terms):
        selected.add("03_decision_logic_and_tradeoffs.md")

    if any(term in q for term in limit_terms):
        selected.add("04_assumptions_limits_and_questions.md")

    # General questions get the business context if no specific domain
    # document was selected.
    if len(selected) == 1:
        selected.add("01_business_context.md")

    files = [
        files_by_name[name]
        for name in sorted(selected)
        if name in files_by_name
    ]

    return _load_selected(files)
