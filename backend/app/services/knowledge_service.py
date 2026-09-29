import hashlib
from pathlib import Path


KNOWLEDGE_ROOT = (
    Path(__file__).resolve().parent.parent
    / "knowledge"
    / "logistics"
)


def load_logistics_knowledge() -> dict:
    files = sorted(KNOWLEDGE_ROOT.glob("*.md"))

    if not files:
        raise RuntimeError("Logistics knowledge base is missing.")

    parts: list[str] = []
    hasher = hashlib.sha256()

    for path in files:
        content = path.read_text(encoding="utf-8").strip()
        parts.append(f"\n\n---\nSOURCE: {path.name}\n---\n{content}")
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")

    digest = hasher.hexdigest()[:12]

    return {
        "name": "logistics_interpreter",
        "version": f"v0.1-{digest}",
        "files": [path.name for path in files],
        "content": "".join(parts).strip(),
    }
