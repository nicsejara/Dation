"""Real local-stack catalog gate. Database changes are confined to the sandbox."""
import asyncio,json,os
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,ProxyHandler
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];REST=os.environ['DATION_E2E_REST'];WORKSPACE=os.environ['DATION_E2E_WORKSPACE']
assert all(urlsplit(url).hostname=='127.0.0.1' for url in (BASE,REST))

async def main():
 errors=[]
 async def grant(status):
  request=Request(REST+'/workspace_ddas?workspace_id=eq.'+WORKSPACE+'&dda_id=eq.logistics',
   data=json.dumps({'status':status}).encode(),method='PATCH',
   headers={'Authorization':'Bearer '+os.environ['SUPABASE_SECRET_KEY'],'Content-Type':'application/json'})
  with build_opener(ProxyHandler({})).open(request,timeout=10) as response:assert response.status==204
 try:
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   page=await browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce');page.set_default_timeout(15000);page.on('pageerror',lambda error:errors.append(str(error)))
   await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill('user-1@example.test');await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click()
   await page.locator('[data-platform-home] h1').wait_for()
   await page.locator('.nav [data-platform-view=inicio]').click();await page.locator('[data-dda-id=logistics] button').click();await page.locator('.dda-landing__hero').wait_for()
   await grant('disabled')
   # The server denies the still-valid JWT; fetch refreshes identity without replay.
   status=await page.evaluate("async()=> (await fetch('/api/decision-cases')).status");assert status==403
   root=page.locator('[data-home-dda-catalog]');await root.locator('[data-dda-entitlement=disabled]').wait_for()
   assert urlsplit(page.url).path=='/app/ddas'
   assert await root.locator('button[data-view-target],a').count()==0
   assert await page.locator('.asset-item').is_disabled()
   for path in ['/app/ddas/logistics','/app/ddas/logistics/data','/app/ddas/logistics/dashboard','/app/history']:
    await page.goto(BASE+path);await root.locator('[data-dda-entitlement=disabled]').wait_for();assert urlsplit(page.url).path=='/app/ddas'
   for width in (1440,1024,768,390):
    await page.set_viewport_size({'width':width,'height':1000})
    await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    probe=await page.evaluate("""() => ({width:innerWidth,scroll:document.documentElement.scrollWidth,nodes:[...document.body.querySelectorAll('*')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(n=>({tag:n.tagName,class:n.className,right:n.getBoundingClientRect().right,text:n.textContent.slice(0,80)}))})""");assert probe['scroll']<=width+1,probe
   await page.locator('.nav [data-platform-view=platform-home]').click();await page.locator('[data-platform-home] .platform-home__quick-link').first.wait_for();assert await page.get_by_role('link',name='Abrir DDA Logística',exact=True).count()==0
   await grant('enabled');await page.evaluate('window.dationSession.refresh()')
   await page.locator('.nav [data-platform-view=inicio]').click();await root.locator('#home-open-logistics').click();await page.locator('.dda-landing__hero').wait_for()
   assert errors==[],errors
   await browser.close()
 finally:await grant('enabled')
 print(json.dumps({'passed':True,'server_revocation':True,'deep_links':True,'reenable':True,'viewports':[1440,1024,768,390]}))
asyncio.run(main())
