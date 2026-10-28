import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 base=os.environ['DATION_T3_PARITY_URL'];out=Path('/workspace/work/dation-t3/dda-parity');out.mkdir(exist_ok=True)
 state=os.environ['DATION_T3_PARITY_STATE']
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  for width in [1440,390]:
   context=await browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
   r=await context.request.post(base+'/auth/login',headers={'Origin':base},data={'email':'user-1@example.test','password':'dispatch-e2e-private'});assert r.ok
   page=await context.new_page();await page.goto(base+'/app/ddas/logistics',wait_until='domcontentloaded')
   await page.wait_for_function('window.DationDispatch && !document.documentElement.classList.contains("d-session-loading")')
   hero=page.locator('.dda-landing__hero');await hero.wait_for()
   await page.evaluate('document.fonts.ready');await page.wait_for_function('[...document.querySelectorAll(".dda-landing__hero img")].every(n=>n.complete&&n.naturalWidth>0)')
   if state=='after':await page.get_by_role('button',name='Crear Case sin archivos',exact=True).wait_for()
   else:assert not await page.get_by_role('button',name='Crear Case sin archivos',exact=True).is_visible()
   await page.evaluate('scrollTo(0,0)');await hero.screenshot(path=str(out/f'{state}-{width}.png'),animations='disabled')
   values=await hero.evaluate('''n=>({rect:n.getBoundingClientRect().toJSON(),styles:[n,...n.querySelectorAll('*')].map(x=>{const c=getComputedStyle(x);return {tag:x.tagName,cls:x.className,styles:Object.fromEntries(['fontFamily','fontSize','fontWeight','lineHeight','padding','margin','gap','borderRadius','borderColor','borderWidth','boxShadow','backgroundColor','backgroundImage','color','width','height'].map(k=>[k,c[k]]))}})})''')
   (out/f'{state}-{width}.json').write_text(json.dumps(values,indent=2)+'\n')
   await context.close()
  await browser.close()
asyncio.run(main())
