"""Public guided wizard actions, without modifying internal state."""
import re
from playwright.async_api import expect

async def compatible(page):
    """Explicitly exercise historical contracts through their preserved editor."""
    if await page.locator('[data-continue-compatible]').is_visible():
        await page.locator('[data-continue-compatible]').click();return
    if not await page.locator('.model-wizard-pro').count():return
    await block(page,3)
    await page.locator('[data-editor-compatible]').click()
    await page.get_by_role('dialog').get_by_role('button',name='Abrir editor compatible',exact=True).click()
    await expect(page.locator('.model-wizard-pro')).to_have_count(0)
    node=await step(page,3)
    await node.locator('label').filter(has=page.locator('[name=cargo_input_mode][value=direct]')).click()
    node=await step(page,6)
    for value in ['weight_kg','volume_m3']:await node.locator('[name=dimensions][value="'+value+'"]').uncheck()
    await node.locator('[name=dimensions][value=pallets]').check()
    await node.locator('[name=primary_dimension]').select_option('pallets')

async def block(page,index):
    node=page.locator('[data-dation-test=model-v2-block-'+str(index)+']')
    if await node.get_attribute('open') is None:await node.locator('>summary').click()
    return node

async def step(page,index):
    await compatible(page)
    await block(page,3);node=page.locator('[data-cargo-step="'+str(index)+'"]')
    if await node.get_attribute('open') is None:await node.locator('>summary').click()
    return node

async def mode(page,value):
    node=await step(page,3)
    await node.locator('label.guided-radio-card').filter(has=page.locator('[name=cargo_input_mode][value="'+value+'"]')).click()

async def product(page,name,mass,*,code='',unit='caja',units='1',groups='SECO'):
    node=await step(page,4);await node.get_by_role('button',name='Agregar producto',exact=True).click()
    row=node.locator('.guided-product-row').filter(has=page.locator('.guided-product-editor:not([hidden])'))
    await row.get_by_label('Nombre del producto *',exact=True).fill(name)
    await row.get_by_label('Código (opcional)',exact=True).fill(code)
    await row.get_by_label('Unidad del producto *',exact=True).fill(unit)
    await row.get_by_label('Unidades por bulto *',exact=True).fill(units)
    if mass is not None:await row.locator('fieldset').filter(has=page.get_by_text('Peso bruto por bulto (opcional)',exact=True)).get_by_label('Valor',exact=True).fill(str(mass))
    tags=row.get_by_label('Categorías de compatibilidad (separadas por coma)',exact=True)
    if not await tags.is_visible():await row.locator('details').filter(has=page.get_by_text('Datos avanzados del producto',exact=True)).locator('>summary').click()
    await tags.fill(groups);return await row.get_attribute('data-product-id')

async def support(page,name='Pallet estándar',tare='25'):
    node=await step(page,2);await node.get_by_role('button',name='Agregar unidad logística',exact=True).click()
    await node.get_by_label('Nombre de la unidad *',exact=True).fill(name)
    await node.locator('fieldset').filter(has=page.get_by_text('Tara explícita',exact=True)).get_by_label('Valor',exact=True).fill(tare)
    return await node.get_by_label('Soporte activo',exact=True).input_value()

async def presentation(page,name,unit_id,parts,*,loaded=('120','100','150')):
    node=await step(page,5);await node.get_by_role('button',name='Agregar presentación',exact=True).click()
    await node.get_by_label('Nombre de la presentación *',exact=True).fill(name)
    if unit_id:await node.get_by_label('Unidad logística compartida',exact=True).select_option(unit_id)
    for i,(key,quantity) in enumerate(parts):
        if i:await node.get_by_role('button',name='Agregar producto a la composición',exact=True).click()
        row=node.locator('.guided-composition-row[role=row]').filter(has=page.locator('select')).nth(i)
        await row.get_by_label('Producto *',exact=True).select_option(key)
        await row.get_by_label('Bultos por presentación *',exact=True).fill(str(quantity))
    key=await node.get_by_label('Presentación activa',exact=True).input_value()
    if loaded:
        if unit_id:
            await node.get_by_role('button',name='Editar soporte y exterior cargado',exact=True).click()
            node=await step(page,2)
        group=node.locator('details').filter(has=page.get_by_text('Dimensiones exteriores cargadas',exact=True))
        if await group.get_attribute('open') is None:await group.locator('>summary').click()
        for label,value in zip(['Largo','Ancho','Alto'],loaded):await group.get_by_label(label,exact=True).fill(value)
    return key

async def confirm(page):
    await compatible(page)
    for index in [1,2,4,5]:
        node=await block(page,index);await node.locator('[data-confirm-block="'+str(index)+'"]').click()
    await step(page,7);checkbox=page.get_by_role('checkbox',name=re.compile('Revisé la configuración'))
    await expect(checkbox).to_be_enabled()
    if not await checkbox.is_checked():await checkbox.check()
    await expect(page.locator('[data-dation-test=model-create]')).to_be_enabled()
