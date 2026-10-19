"""Verify the first real foundation consumer without changing DDA behaviour."""
import json
import unittest

import test_navigation as navigation


class PlatformSettingsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        navigation.NavigationTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        navigation.NavigationTests.tearDownClass()

    async def test_settings_uses_foundation_and_keeps_status_refresh_and_dda_context(self):
        browser = navigation.NavigationTests()
        await browser.asyncSetUp()
        configured = False

        async def llm_status(route):
            await route.fulfill(content_type="application/json", body=json.dumps({
                "configured": configured, "provider": "qa",
                "model": "qa-" + "very-long-model-identifier-" * 5,
                "knowledge_version": "qa-v1",
            }))

        await browser.context.route("**/api/system/llm-status", llm_status)
        try:
            for width in (1440, 1280, 1024, 768, 390):
                with self.subTest(width=width):
                    configured = False
                    await browser.page.set_viewport_size({"width": width, "height": 1000})
                    await browser.open("logistics-map")
                    identity = await browser.page.evaluate("""() => {
                      const state = window.DationDispatch.getWorkspace();
                      return [state.decisionCase.id, state.orders.id, state.fleet.id];
                    }""")
                    await browser.nav("settings")
                    panel = browser.page.locator('[data-view-panel="settings"]')
                    await panel.locator("h1").wait_for(state="visible")
                    await browser.page.wait_for_function(
                        "document.querySelector('#settings-ai-status').textContent === 'No configurado'"
                    )
                    self.assertEqual(await panel.locator(".d-page-header h1").inner_text(), "Configuración")
                    await panel.get_by_label('Nombre del workspace').wait_for()
                    self.assertEqual(await panel.locator('[data-workspace-settings] [role=tab]').count(), 4)
                    self.assertEqual(await panel.locator("[data-workspace-settings] .d-card").count(), 1)
                    await panel.locator("[data-platform-diagnostics] summary").click()
                    self.assertEqual(await browser.page.locator(".view.is-active").count(), 1)
                    geometry = await panel.evaluate("""panel => {
                      const header = panel.querySelector('.d-page-header').getBoundingClientRect();
                      const grid = panel.querySelector('[data-workspace-settings]').getBoundingClientRect();
                      return {
                        overflow: document.documentElement.scrollWidth > innerWidth + 1,
                        gap: grid.top - header.bottom,
                        bodySize: parseFloat(getComputedStyle(panel.querySelector('.settings-row')).fontSize),
                        within: [...panel.querySelectorAll('[data-workspace-settings] .d-card')].every(card => {
                          const rect = card.getBoundingClientRect();
                          return rect.left >= 0 && rect.right <= innerWidth + 1;
                        })
                      };
                    }""")
                    self.assertFalse(geometry["overflow"])
                    self.assertTrue(geometry["within"])
                    self.assertGreaterEqual(geometry["gap"], 19.99)
                    self.assertGreaterEqual(geometry["bodySize"], 12)
                    help_trigger = panel.get_by_role("button", name="Acerca de estos estados")
                    help_panel = panel.locator("#settings-status-help")
                    self.assertIsNone(await help_trigger.get_attribute("aria-haspopup"))
                    await help_trigger.click()
                    self.assertTrue(await help_panel.is_visible())
                    self.assertEqual(await help_trigger.get_attribute("aria-expanded"), "true")
                    await browser.page.keyboard.press("Escape")
                    self.assertFalse(await help_panel.is_visible())
                    self.assertTrue(await help_trigger.evaluate("n=>document.activeElement===n"))
                    await help_trigger.click()

                    configured = True
                    await browser.nav("logistics-map")
                    await browser.page.locator('[data-map-node="logistics_assignment"]').first.wait_for(state="visible")
                    self.assertFalse(await panel.is_visible())
                    self.assertTrue(await help_panel.evaluate("n=>n.hidden"))
                    await browser.nav("settings")
                    await browser.page.wait_for_function(
                        "document.querySelector('#settings-ai-status').textContent === 'Disponible'"
                    )
                    self.assertEqual(await panel.locator("#settings-ai-provider").inner_text(), "qa")
                    self.assertFalse(await browser.page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"))
                    restored = await browser.page.evaluate("""() => {
                      const state = window.DationDispatch.getWorkspace();
                      return [state.decisionCase.id, state.orders.id, state.fleet.id];
                    }""")
                    self.assertEqual(restored, identity)

                    await browser.open("decision-dashboard", "logistics_assignment", browser.f["ids"]["assignment"])
                    self.assertEqual(await browser.page.locator(".view.is-active").count(), 1)
                    self.assertFalse(await browser.page.locator('[data-view-panel="settings"]').is_visible())
                    self.assertEqual(await browser.page.locator(".assignment-dashboard-v2.d-platform").count(), 0)
            self.assertFalse([
                (method, path) for method, path in browser.requests
                if method != "GET" and path != "/api/runs/preflight"
            ])
        finally:
            await browser.asyncTearDown()
