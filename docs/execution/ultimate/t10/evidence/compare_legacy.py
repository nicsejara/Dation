import asyncio,json,os,sys,datetime,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/Dation/backend/tests/browser')
import test_navigation as nav
OUT=Path('/workspace/work/dation-t10/legacy-preservation');OUT.mkdir(exist_ok=True)
os.environ['DATION_RUNTIME_PYTHON']='/workspace/Dation/.venv/bin/python'
CLOCK="""(()=>{const Original=Date;const fixed=Original.parse('2026-10-27T18:48:00Z');class QAClock extends Original{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}}window.Date=QAClock;})();"""
async def capture(label,root):
 nav.ROOT=Path(root);nav.NavigationTests.setUpClass()
 try:
  b=nav.NavigationTests();await b.asyncSetUp();await b.page.add_init_script(CLOCK);records=[]
  try:
   for name,size in [('desktop',(1440,900)),('laptop',(1024,768)),('tablet',(768,1024)),('phone',(375,812)),('small',(320,640))]:
    await b.page.set_viewport_size(dict(zip(['width','height'],size)))
    for node,key in [('logistics_assignment','assignment'),('logistics_scheduling','scheduling')]:
     await b.open('decision-dashboard',node,b.f['ids'][key]);await b.page.evaluate('document.fonts.ready');await b.page.evaluate('scrollTo(0,0)');await b.page.mouse.move(0,0)
     await b.page.locator('.d-dashboard-hero img').first.evaluate('img=>img.decode().catch(()=>{})');await b.page.wait_for_timeout(150)
     path=OUT/f'{label}-{key}-{name}.png';await b.page.screenshot(path=str(path),full_page=True,animations='disabled')
     records.append({'kind':key,'viewport':size,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'styles':await b.page.evaluate("()=>{const s=getComputedStyle(document.querySelector('.d-dashboard-hero'));return {font:s.fontFamily,radius:s.borderRadius,padding:s.padding,border:s.borderColor,background:s.backgroundColor,shadow:s.boxShadow,width:document.body.scrollWidth}}")})
   (OUT/f'{label}.json').write_text(json.dumps(records,indent=2));assert not b.errors,b.errors;print(label,': 10 screenshots, no browser errors',flush=True)
  finally:await b.asyncTearDown()
 finally:nav.NavigationTests.tearDownClass()
async def main():
 await capture('post-t9','/workspace/work/dation-t10/baseline-src/backend')
 await capture('candidate','/workspace/Dation/backend')
asyncio.run(main())
