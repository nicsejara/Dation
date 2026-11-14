"""Exercise the public wizard actions; never mutate its internal state."""
from playwright.async_api import expect


async def publish_model(page, name=None):
    if name is not None:
        await page.get_by_label('Nombre del modelo *', exact=True).fill(name)
    action=page.get_by_role('button',name='Crear y seleccionar modelo',exact=True)
    await expect(action).to_be_enabled()
    await action.click()
    await expect(page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')
    await expect(page.locator('[data-dation-test=core-model]')).to_have_attribute('data-model-state','MODEL_SELECTED')


async def select_model(page, model_id, version_id):
    await page.get_by_role('button',name='Seleccionar modelo existente',exact=True).click()
    dialog=page.get_by_role('dialog')
    await dialog.get_by_label('Logistics Model',exact=True).select_option(model_id)
    await expect(dialog.get_by_role('button',name='Seleccionar esta versión',exact=True)).to_be_enabled()
    await dialog.get_by_label('Model Version',exact=True).select_option(version_id)
    await dialog.get_by_role('button',name='Seleccionar esta versión',exact=True).click()
    await expect(page.locator('[data-dation-test=core-step-2]')).to_have_attribute('aria-current','step')


async def show_case(page):
    await page.locator('[data-dation-test=core-step-3]').click()
    await expect(page.locator('[data-dation-test=core-case]')).to_be_visible()
