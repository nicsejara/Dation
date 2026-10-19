"""The actual runtime hides approval from an unassigned Operator and attributes it."""
import asyncio,json,os
from urllib.parse import urlsplit,urlencode
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
async def main():
 errors=[]
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  target=BASE+'/app?'+urlencode({'view':'decision-dashboard','case_id':os.environ['DATION_TEAM_CASE'],'node_id':'logistics_assignment','run_id':os.environ['DATION_TEAM_RUN']})
  denied=await browser.new_context();await denied.add_cookies([{'name':'dation_access','value':os.environ['DATION_TEAM_OTHER_TOKEN'],'url':BASE}]);page=await denied.new_page();page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(target);await page.locator('.assignment-dashboard-v2').wait_for();assert await page.locator('[data-approve-toolbar],[data-approve-final]').count()==0;assert 'requiere al aprobador asignado' in await page.locator('[data-approval-policy]').inner_text()
  context=await browser.new_context();page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-2@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click();await page.locator('[data-platform-home] h1').wait_for();await page.goto(target);await page.locator('.assignment-dashboard-v2').wait_for();await page.locator('[data-approval-policy]').wait_for();assert 'Podés aprobar' in await page.locator('[data-approval-policy]').inner_text();await page.locator('[data-approve-toolbar]').click();await page.locator('[data-status-badge]').filter(has_text='Aprobada').wait_for(state='attached');assert await page.locator('[data-approve-toolbar]').is_disabled()
  assert errors==[],errors;await browser.close()
 print(json.dumps({'passed':True,'unassigned_operator_blocked_in_runtime':True,'assigned_operator_approved':True}))
asyncio.run(main())
