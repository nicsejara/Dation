from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "app" / "static" / "js" / "dispatch"


class DecisionConfigUiFoundationTests(unittest.TestCase):
    def setUp(self):
        self.shared = (DISPATCH / "decision-config-ui.mjs").read_text(encoding="utf-8")
        self.assignment = (DISPATCH / "assignment-config.mjs").read_text(encoding="utf-8")
        self.scheduling = (DISPATCH / "scheduling-config-v2.mjs").read_text(encoding="utf-8")

    def test_shared_module_exposes_canonical_primitives(self):
        for name in (
            "decisionHero",
            "decisionCaseCard",
            "decisionDataFileCard",
            "decisionSectionHeader",
            "decisionChoiceCard",
            "decisionDepthCard",
            "configSummaryBar",
            "decisionInfoNote",
            "decisionEmptyState",
            "decisionRuleCard",
        ):
            self.assertIn(f"export function {name}", self.shared)

    def test_shared_primitives_preserve_assignment_visual_contract(self):
        for marker in (
            "dispatch-pro-hero assignment-config-hero",
            "dispatch-pro-how-panel assignment-decision-panel",
            "dispatch-case-card assignment-case-strip",
            "assignment-section__head",
            "assignment-choice-card",
            "assignment-depth-card",
            "assignment-summary-bar",
            "assignment-review-cta",
        ):
            self.assertIn(marker, self.shared)

    def test_shared_option_components_keep_disabled_accessibility_contract(self):
        self.assertIn('buttonAttrs.disabled=true', self.shared)
        self.assertIn('buttonAttrs["aria-disabled"]="true"', self.shared)
        self.assertIn('attributes.disabled=true', self.shared)
        self.assertIn('attributes["aria-disabled"]="true"', self.shared)

    def test_assignment_consumes_shared_primitives(self):
        self.assertIn('from "./decision-config-ui.mjs?v=decision-config-foundation"', self.assignment)
        for name in (
            "decisionHero(",
            "decisionCaseCard(",
            "decisionDataFileCard(",
            "decisionSectionHeader(",
            "decisionChoiceCard(",
            "decisionDepthCard(",
            "configSummaryBar(",
        ):
            self.assertIn(name, self.assignment)

    def test_assignment_no_longer_owns_duplicate_component_renderers(self):
        self.assertNotIn("function sectionHeader(", self.assignment)

    def test_scheduling_now_consumes_shared_primitives(self):
        self.assertIn('from "./decision-config-ui.mjs?v=scheduling-shared-phase2-v1"', self.scheduling)
        for name in (
            "decisionHero(",
            "decisionCaseCard(",
            "decisionDataFileCard(",
            "decisionSectionHeader(",
            "decisionChoiceCard(",
            "decisionDepthCard(",
            "configSummaryBar(",
        ):
            self.assertIn(name, self.scheduling)
        self.assertNotIn("function sectionHead(", self.scheduling)
        self.assertNotIn("function choice(", self.scheduling)


if __name__ == "__main__":
    unittest.main()
