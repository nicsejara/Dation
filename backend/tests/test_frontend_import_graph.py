"""Deleted frontend modules must not leave dangling static or lazy imports."""
from pathlib import Path
import re
import unittest


class FrontendImportGraphTests(unittest.TestCase):
    def test_template_entrypoints_and_relative_imports_resolve(self):
        app = Path(__file__).resolve().parents[1] / "app"
        static = (app / "static").resolve()
        references = []
        entrypoints = []
        graph = {}
        for template in (app / "templates").glob("*.html"):
            for src in re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)', template.read_text()):
                if src.startswith("/static/"):
                    target = (app / src.split("?")[0].lstrip("/")).resolve()
                    references.append((template, target))
                    entrypoints.append(target)
        for module in (static / "js").rglob("*"):
            if module.suffix not in (".js", ".mjs"):
                continue
            graph[module.resolve()] = []
            for src in re.findall(r'(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)["\']([^"\']+)', module.read_text()):
                if src.startswith("."):
                    target = (module.parent / src.split("?")[0]).resolve()
                    references.append((module, target))
                    graph[module.resolve()].append(target)
        self.assertTrue(references, "No frontend entrypoints or imports checked")
        for owner, target in references:
            with self.subTest(owner=str(owner.relative_to(app)), target=target.name):
                self.assertTrue(target.is_relative_to(static), "Import escapes static assets")
                self.assertTrue(target.is_file(), "Missing frontend dependency: " + str(target))
        visited = set()
        while entrypoints:
            module = entrypoints.pop()
            if module not in visited:
                visited.add(module)
                entrypoints.extend(graph.get(module, []))
        self.assertEqual(sorted(str(p.relative_to(static)) for p in graph.keys() - visited), [],
                         "Frontend modules have no template/import consumer")
