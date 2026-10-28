import asyncio,copy,json,os,sys
from pathlib import Path
from test_navigation import NavigationTests
PHASE=sys.argv[1];OUT=Path('/workspace/work/dation-t0r2/focus')/PHASE;OUT.mkdir(parents=True,exist_ok=True)
AUDIT=(Path('/workspace/Dation/backend/tests/browser')/'focus_audit.js').read_text()
async def main():
 b=NavigationTests();NavigationTests.setUpClass()
 result=[]
 try:
  await b.asyncSetUp();p=b.page;await p.emulate_media(reduced_motion='reduce');initial=copy.deepcopy(b.case)
  for w,h in [(320,568),(320,256),(568,320),(1440,1000),(1280,1000),(1024,1000),(768,1000),(390,844)]:
   await p.set_viewport_size({'width':w,'height':h})
   for kind,view,node in [('data','logistics-data',None),('map','logistics-map',None),('assignment','logistics-config','logistics_assignment'),('scheduling','logistics-config','logistics_scheduling')]:
    b.case.clear();b.case.update(copy.deepcopy(initial))
    if kind=='map':b.case['nodes']=copy.deepcopy(b.f['initial_case']['nodes'])
    await b.open(view,node);await p.evaluate('document.fonts.ready');await p.wait_for_load_state('networkidle')
    baseline=await p.locator('.view.is-active').evaluate("e=>({overflow:document.documentElement.scrollWidth>innerWidth,style:[e.querySelector('.d-page-hero'),e.querySelector('h1'),e.querySelector('.d-workflow-action-bar')].filter(Boolean).map(n=>{const s=getComputedStyle(n),r=n.getBoundingClientRect();return {class:n.className,width:r.width,height:r.height,font:s.font,padding:s.padding,radius:s.borderRadius,background:s.backgroundColor,border:s.border,gap:s.gap}})})")
    await p.screenshot(path=str(OUT/f'{kind}-{w}-{h}-rest.png'),animations='disabled')
    seen=set();failures=[];pending=[]
    for i in range(120):
     await p.keyboard.press('Tab');immediate=await p.evaluate(AUDIT)
     if immediate.get('skip'):continue
     if immediate['identity'] in seen:break
     seen.add(immediate['identity'])
     if immediate['tag']=='ARTICLE' and immediate['rect']['height']>h-160:continue
     if immediate['outside'] or immediate['occluded'] or not immediate['visibleFocus']:
      await p.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');stable=await p.evaluate(AUDIT)
      details=await p.evaluate("""()=>{const e=document.activeElement,r=e.getBoundingClientRect();return {hits:[.2,.5,.8].map(t=>{const n=document.elementFromPoint(r.x+r.width*t,r.y+r.height*t);return n?{tag:n.tagName,cls:n.className,text:n.textContent.slice(0,70)}:null}),ancestors:[...function*(n){while(n){yield n;n=n.parentElement}}(e)].map(n=>{const s=getComputedStyle(n),r=n.getBoundingClientRect();return {tag:n.tagName,cls:n.className,rect:{x:r.x,y:r.y,w:r.width,h:r.height},overflowX:s.overflowX,overflowY:s.overflowY,scrollTop:n.scrollTop,scrollLeft:n.scrollLeft,padding:s.padding,position:s.position}}),bar:(()=>{const n=document.querySelector('.view.is-active .d-workflow-action-bar');if(!n)return null;const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()}}""")
      failures.append({'step':i,'immediate':immediate,'stable':stable,'details':details});await p.screenshot(path=str(OUT/f'{kind}-{w}-{h}-focus.png'),animations='disabled');break
    row={'kind':kind,'width':w,'height':h,'baseline':baseline,'visited':len(seen),'failures':failures};result.append(row)
    (OUT/'probes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'kind':kind,'viewport':[w,h],'visited':len(seen),'failures':len(failures)},ensure_ascii=False),flush=True)
 finally:
  if hasattr(b,'browser'):await b.asyncTearDown()
  NavigationTests.tearDownClass()
asyncio.run(main())
