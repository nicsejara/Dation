"""Use the actual BFF/cookie/Bearer flow against the owned Auth contract fixture."""
async def authenticate(context,base):
    result=await context.request.post(base+'/auth/login',headers={'Origin':base},
        data={'email':'user-1@example.test','password':'dispatch-e2e-private'})
    assert result.status==200,await result.text()


async def api_get(context,url):
    from urllib.parse import urlsplit
    parsed=urlsplit(url);base=parsed.scheme+'://'+parsed.netloc
    response=await context.request.post(base+'/auth/session',headers={'Origin':base})
    assert response.status==200,await response.text()
    identity=await response.json()
    return await context.request.get(url,headers={'Authorization':'Bearer '+identity['access_token']})


async def assign_workflow_person(page,stage):
    """Use the actual inline UI; no direct writes to browser state or SQL."""
    uid='10000000-0000-4000-8000-000000000001'
    stage='data_owner' if stage=='data_preparation' else stage
    assigned=await page.evaluate("""({stage,uid})=>{
      const value=window.DationDispatch.getWorkspace().workflow?.stages?.[stage];
      return value?.owner?.id===uid&&value?.owner_eligible;
    }""",{'stage':stage,'uid':uid})
    if assigned:return
    if stage=='data_owner':
        form=page.locator('[data-case-identity]')
        await form.get_by_label('Nombre del Case',exact=True).fill('Real browser Case')
        await form.get_by_label('Categoría',exact=True).select_option('simulation')
        select=form.get_by_label('Data Owner',exact=True)
        await select.locator('option[value="'+uid+'"]').wait_for(state='attached')
        await select.select_option(uid);await form.get_by_role('button',name='Aplicar',exact=True).click()
        await form.get_by_text('Atributos y Data Owner aplicados.',exact=True).wait_for()
        return
    root=page.locator('[data-workflow-responsibility="'+stage+'"]')
    import re
    await root.get_by_role('button',name=re.compile('^(Seleccionar responsable|Cambiar)$')).click()
    select=root.get_by_label('Decision Owner',exact=True)
    await select.locator('option[value="'+uid+'"]').wait_for(state='attached')
    await select.select_option(uid)
    previous=await root.element_handle()
    map_view=await page.evaluate("window.dationGetCurrentView()==='logistics-map'")
    await root.get_by_role('button',name='Guardar',exact=True).click()
    await page.wait_for_function("({stage,uid})=>{const s=window.DationDispatch.getWorkspace().workflow?.stages?.[stage];return s?.owner?.id===uid&&s.owner_eligible;}",arg={'stage':stage,'uid':uid})
    if map_view:
        await page.wait_for_function('el=>!el.isConnected',arg=previous)
    await root.get_by_role('button',name='Cambiar',exact=True).wait_for()
