"""A confirmed person without membership can accept without creating a workspace."""
import asyncio,json,os
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context();await context.add_cookies([{'name':'dation_access','value':os.environ['DATION_TEAM_NEW_TOKEN'],'url':BASE}]);page=await context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(BASE+'/workspace-setup');await page.get_by_role('button',name='Aceptar invitación',exact=True).wait_for();assert not await page.locator('#auth-root>form').is_visible();await page.get_by_role('button',name='Aceptar invitación',exact=True).click();await page.locator('[data-platform-home] h1').wait_for();assert await page.locator('[data-workspace-name]').inner_text()=='Dation';assert errors==[],errors;await browser.close()
 print(json.dumps({'passed':True,'no_membership_invitation_acceptance':True}))
asyncio.run(main())
