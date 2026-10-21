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


async def assign_workflow_person(page,stage,field='owner'):
    """Use the actual inline UI; no direct writes to browser state or SQL."""
    uid='10000000-0000-4000-8000-000000000001'
    await page.locator('[data-workflow-responsibility="'+stage+'"]').wait_for()
    assigned=await page.evaluate("""({stage,field,uid})=>{
      const value=window.DationDispatch.getWorkspace().workflow?.stages?.[stage];
      return value?.[field]?.id===uid&&value?.[field+'_eligible'];
    }""",{'stage':stage,'field':field,'uid':uid})
    if assigned:return
    if field=='approver':
        for button in await page.locator('[data-approve-toolbar],[data-approve-final]').all():
            assert await button.is_disabled(),'Approval must wait for an eligible assigned approver.'
    root=page.locator('[data-workflow-responsibility="'+stage+'"]')
    import re
    await root.get_by_role('button',name=re.compile('^(Seleccionar responsable|Cambiar)$')).click()
    label='Responsable de datos' if stage=='data_preparation' else 'Aprobador asignado' if field=='approver' else 'Responsable de la decisión'
    await root.get_by_label(label,exact=True).select_option(uid)
    await root.get_by_role('button',name='Guardar',exact=True).click()
    await root.get_by_role('button',name='Cambiar',exact=True).wait_for()
