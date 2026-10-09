from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "app" / "static" / "js" / "dispatch"
FOCUS = (DISPATCH / "scheduling-focus-rules.mjs").read_text(encoding="utf-8")
CONFIG = (DISPATCH / "scheduling-config-v2.mjs").read_text(encoding="utf-8")
SHARED = (DISPATCH / "decision-config-ui.mjs").read_text(encoding="utf-8")
CSS = (
    ROOT
    / "app"
    / "static"
    / "css"
    / "scheduling-rule-editor-phase3.css"
).read_text(encoding="utf-8")
BOOTSTRAP = (
    ROOT
    / "app"
    / "static"
    / "js"
    / "dda-variable-config.js"
).read_text(encoding="utf-8")


class SchedulingConfigPhase3RuleEditorTests(unittest.TestCase):
    def test_phase3_is_bootstrapped_and_cache_busted(self):
        self.assertIn(
            'scheduling-config-v2.mjs?v=scheduling-rule-editor-phase3-v1',
            BOOTSTRAP,
        )
        self.assertIn(
            'scheduling-focus-rules.mjs?v=scheduling-rule-editor-phase3-v1',
            CONFIG,
        )
        self.assertIn(
            'scheduling-rule-editor-phase3.css?v=scheduling-rule-editor-phase3-v1',
            CONFIG,
        )

    def test_rule_list_reuses_shared_rule_card_primitive(self):
        self.assertIn(
            'decisionRuleCard} from "./decision-config-ui.mjs?v=scheduling-rule-editor-phase3-v1"',
            FOCUS,
        )
        self.assertIn("decisionRuleCard({", FOCUS)
        self.assertIn("export function decisionRuleCard", SHARED)
        self.assertIn('className:"scheduling-rule-card-v3"', FOCUS)

    def test_editor_supports_create_edit_cancel_and_remove(self):
        for marker in (
            "editingRuleId",
            "data-scheduling-rule-add",
            "Agregar regla",
            "Guardar cambios",
            "data-scheduling-rule-edit",
            "data-scheduling-rule-cancel",
            "data-scheduling-rule-remove",
            "Escape",
        ):
            self.assertIn(marker, FOCUS)
        self.assertIn("item.id===editingId?rule:item", FOCUS)
        self.assertIn("editingRuleId:null", FOCUS)

    def test_pending_draft_blocks_review_and_execution(self):
        self.assertIn("function hasPendingRuleDraft", FOCUS)
        self.assertIn("function pendingRuleProblem", FOCUS)
        self.assertIn("Agregá o cancelá la regla preparada antes de ejecutar", FOCUS)
        self.assertIn("Guardá o cancelá los cambios", FOCUS)
        self.assertIn("const pending=pendingRuleProblem(config,trips)", CONFIG)
        self.assertIn("if(pending)return pending", CONFIG)
        self.assertIn('config.editingRuleId?"Editando regla":"Regla sin aplicar"', CONFIG)

    def test_editor_has_live_impact_and_overlap_feedback(self):
        for marker in (
            "IMPACTO PREVIO",
            "data-scheduling-rule-select-all",
            "data-scheduling-rule-clear-values",
            "scheduling-rule-preview__trips",
            "Solapamiento detectado",
            "overlappingRules",
            "draftMatchedTrips",
        ):
            self.assertIn(marker, FOCUS)
        self.assertIn('aria-live="polite"', FOCUS)

    def test_duplicate_and_impossible_overlapping_windows_are_guarded(self):
        self.assertIn("function ruleFingerprint", FOCUS)
        self.assertIn("Ya existe una regla idéntica", FOCUS)
        self.assertIn("function conflictingWindowRule", FOCUS)
        self.assertIn("entra en conflicto", FOCUS)
        self.assertIn("reglas temporales duplicadas", FOCUS)

    def test_editor_preserves_backend_temporal_rules_contract(self):
        for marker in (
            "id:rule.id",
            "field:rule.field",
            "values:[...(rule.values||[])]",
            "action:rule.action",
            "planning_window_start",
            "planning_window_end",
            "temporal_rules:executionRules(config)",
            'node_id:"logistics_scheduling"',
        ):
            self.assertIn(marker, FOCUS + CONFIG)

    def test_restoring_run_does_not_restore_transient_editor_state(self):
        self.assertIn("editingRuleId:null", CONFIG)
        self.assertIn(
            'ruleDraft:{field:"destination",values:[],action:"prioritize",windowStart:"",windowEnd:""}',
            CONFIG,
        )

    def test_phase3_rule_editor_is_responsive_and_motion_safe(self):
        self.assertIn("@media(max-width:820px)", CSS)
        self.assertIn("@media(max-width:620px)", CSS)
        self.assertIn("@media(prefers-reduced-motion:reduce)", CSS)
        self.assertIn("focus-visible", CSS)
        self.assertIn("scheduling-rule-preview__actions", CSS)


if __name__ == "__main__":
    unittest.main()
