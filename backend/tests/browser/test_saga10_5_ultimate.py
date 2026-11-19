"""R2 regression scenarios migrated to R4 public controls (see TEST_MIGRATION.md)."""
import asyncio,json,re,unittest,subprocess,os
from pathlib import Path
from playwright.async_api import expect
import r4_model_helpers as r4
import guided_model_helpers as legacy
OUT=Path('/tmp/dation-saga10-5-r2-browser');OUT.mkdir(exist_ok=True)
class UltimateProTests(r4.R4Browser):
    async def test_02_roles_sources_cost_dependencies_and_currency(self):
        await self.start();await self.fill()
        node=await legacy.block(self.page,2)
        for value in ['LOGISTICS_PROVIDER','HYBRID','SHIPPER']:
            control=node.locator('[name=operating_role][value='+value+']');await control.focus();await self.page.keyboard.press('Space');await expect(control).to_be_checked()
        await node.locator('[name=consolidation_permitted][value=no]').focus();await self.page.keyboard.press('Space')
        await expect(node.locator('[name=transport_pattern]')).to_have_count(0)
        resources=await legacy.block(self.page,4);await resources.locator('label').filter(has=self.page.locator('[name=sources][value=OWN]')).click()
        costs=await legacy.block(self.page,5);await expect(costs.get_by_text('Costo operativo por kilómetro',exact=True)).to_be_hidden()
        await costs.locator('label').filter(has=self.page.locator('[name=currency][value=EUR]')).click()
        money=costs.locator('details').filter(has=self.page.get_by_text('Configuración monetaria avanzada',exact=True));await money.locator('>summary').click();await costs.get_by_label('Decimales monetarios',exact=True).select_option('4')
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_KM]')).click()
        await expect(costs.locator('[name=billing]').first).to_be_hidden()
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_TRIP]')).click()
        await costs.locator('[data-confirm-block="5"]').click();await expect(costs.locator('[data-model-error-for=costs]')).to_contain_text('tarifa externa')
        await costs.locator('label').filter(has=self.page.locator('[name=external_costs][value=PER_KM]')).click()
        cfg=await self.publish()
        self.assertFalse(cfg['consolidation_permitted']);self.assertEqual(cfg['allowed_sources'],['EXTERNAL'])
        self.assertEqual(cfg['currency_policy']['currency'],'EUR');self.assertEqual(cfg['currency_policy']['minor_units'],4)
        self.assertEqual(cfg['per_km_billing_bases'],['ONE_WAY','ROUND_TRIP']);self.assertEqual(cfg['external_cost_models'],['PER_KM'])

    async def test_01_homogeneous_physics_contract_and_explicit_confirmation(self):
        await r4.scenario(self,'test_01_progressive_one_two_edit_and_shared_physics')
    async def test_03_five_types_cancel_and_big_bag_without_fake_geometry(self):
        await r4.scenario(self,'test_04_five_units_metre_volume_and_cancel_safe')
    async def test_04_shared_support_two_homogeneous_presentations_and_reload(self):
        await r4.scenario(self,'test_01_progressive_one_two_edit_and_shared_physics')
    async def test_05_real_geometry_a11y_and_screenshots(self):
        await r4.scenario(self,'test_09_dom_inventory_responsive_geometry_accessibility_and_screenshots')
    async def test_06_stale_preview_retry_and_local_cta_never_publish(self):
        await r4.scenario(self,'test_06_stale_preview_error_retry_no_local_publication')
    async def test_07_dimensions_split_and_confirmation_invalidation(self):
        await r4.scenario(self,'test_10_dimensions_primary_split_and_independent_publication')
    async def test_08_legacy_mixed_currency_and_commercial_counts_are_not_converted(self):
        await r4.scenario(self,'test_08_legacy_contracts_preserved_without_catalog_manager')
