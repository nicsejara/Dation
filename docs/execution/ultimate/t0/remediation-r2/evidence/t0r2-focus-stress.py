import asyncio,copy,json
from pathlib import Path
from test_navigation import NavigationTests
OUT=Path('/workspace/work/dation-t0r2/focus/stress');OUT.mkdir(exist_ok=True)
AUDIT=Path('/workspace/Dation/backend/tests/browser/focus_audit.js').read_text()
async def main():
 b=NavigationTests();NavigationTests.setUpClass();records=[]
 try:
  await b.asyncSetUp();p=b.page;await p.emulate_media(reduced_motion='reduce')
  session=await b.context.new_cdp_session(p)
  await session.send('Emulation.setTouchEmulationEnabled',{'enabled':True,'maxTouchPoints':1})
  original=copy.deepcopy(b.case)
  for w,h,scale in [(320,256,1),(568,320,1),(720,450,2)]:
   await p.set_viewport_size({'width':w,'height':h})
   if scale==2:await session.send('Emulation.setDeviceMetricsOverride',{'width':w,'height':h,'deviceScaleFactor':2,'mobile':False})
   for kind,view,node in [('data','logistics-data',None),('map','logistics-map',None),('assignment','logistics-config','logistics_assignment'),('scheduling','logistics-config','logistics_scheduling')]:
    b.case.clear();b.case.update(copy.deepcopy(original))
    if kind=='map':b.case['nodes']=copy.deepcopy(b.f['initial_case']['nodes'])
    await b.open(view,node)
    if kind=='data':await p.locator('.d-workflow-action-bar[data-state=ready]').wait_for()
    touch=p.get_by_label('Nombre del Case',exact=True) if kind=='data' else p.locator('[data-config-context] summary')
    await touch.scroll_into_view_if_needed();r=await touch.bounding_box()
    await session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':r['x']+r['width']/2,'y':r['y']+r['height']/2}]})
    await session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    if kind=='data':assert await touch.evaluate('el=>el===document.activeElement')
    else:await p.wait_for_function("document.querySelector('[data-config-context]').open")
    await p.keyboard.press('Tab')
    target=p.locator('[data-scheduling-window-mode=custom]') if kind=='scheduling' else p.locator('[data-config-review]') if kind=='assignment' else p.locator('.dda-workspace-step[data-step="2"]')
    await target.focus();probe=await p.evaluate(AUDIT)
    assert probe['visibleFocus'] and not probe['outside'] and not probe['occluded'],(kind,w,h,probe)
    assert not await p.evaluate('document.documentElement.scrollWidth>innerWidth')
    await p.screenshot(path=str(OUT/f'{kind}-{w}-{h}-{scale}x-focus.png'))
    records.append({'surface':kind,'width':w,'height':h,'device_scale_factor':scale,'zoom_equivalent':'200% at 1440x900' if scale==2 else None,'touch':True,'focus':probe,'overflow':False})
    (OUT/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'surface':kind,'viewport':[w,h],'scale':scale,'status':'PASS'}),flush=True)
   if scale==2:await session.send('Emulation.clearDeviceMetricsOverride')
  assert b.execution_bodies==[]
 finally:
  if hasattr(b,'browser'):await b.asyncTearDown()
  NavigationTests.tearDownClass()
asyncio.run(main())
