"""Observe only two unchanged browser tests on a selected source checkout."""
import asyncio,json,os,sys,traceback,unittest
from pathlib import Path
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests/browser')]
from playwright.async_api import Locator
import test_final_polish as c1
import test_run_lineage_polish as f3

OUT=Path(os.environ['BROWSER_DIAGNOSTICS']);OUT.mkdir(parents=True,exist_ok=True)
records=[];current={};original_texts=Locator.all_inner_texts
SNAPSHOT='''()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,html:document.documentElement.className,view:window.dationGetCurrentView?.(),fonts:document.fonts.status,labels:[...document.querySelectorAll('.dda-landing__flow-node small,.dispatch-pro-how-node small')].map(e=>({text:e.textContent,inner:e.innerText,visibility:getComputedStyle(e).visibility,display:getComputedStyle(e).display,rect:e.getBoundingClientRect().toJSON(),ancestors:[...function*(n){while(n){yield n;n=n.parentElement}}(e)].slice(0,8).map(n=>({tag:n.tagName,cls:n.className,hidden:n.hidden,display:getComputedStyle(n).display,visibility:getComputedStyle(n).visibility}))})),offenders:[...document.querySelectorAll('body *')].filter(e=>{let r=e.getBoundingClientRect();return r.width&&r.height&&(r.right>innerWidth+1||r.left< -1)}).slice(0,25).map(e=>({tag:e.tagName,id:e.id,cls:typeof e.className==='string'?e.className:'svg',rect:e.getBoundingClientRect().toJSON(),text:e.innerText?.slice(0,120)}))})'''

async def capture(page,reason,observed):
    before=await page.evaluate(SNAPSHOT)
    await page.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    after=await page.evaluate(SNAPSHOT)
    key=str(len(records));record={**current,'reason':reason,'observed':observed,'before':before,'after_two_frames':after}
    print('BROWSER_OBSERVATION='+json.dumps(record),flush=True)
    records.append(record);(OUT/'observations.json').write_text(json.dumps(records,indent=2))
    if reason!='overflow' or observed:
        await page.screenshot(path=str(OUT/(key+'.png')),full_page=True)

async def observed_texts(self):
    result=await original_texts(self)
    if result==['','','']:await capture(current['page'],'empty_inner_texts',result)
    return result
Locator.all_inner_texts=observed_texts

def instrument(cls):
    original=cls.asyncSetUp
    async def setup(self):
        await original(self);page=self.page;current.clear();current.update(test=self.id(),page=page,browser=self.b.browser.version,cpu_rate=getattr(self,'cpu_rate',1))
        session=await self.b.context.new_cdp_session(page)
        await session.send('Emulation.setCPUThrottlingRate',{'rate':getattr(self,'cpu_rate',1)})
        evaluate=page.evaluate
        async def observed_evaluate(expression,*args,**kwargs):
            value=await evaluate(expression,*args,**kwargs)
            if expression=='document.documentElement.scrollWidth>innerWidth' and value:
                await capture(page,'overflow',value)
            return value
        page.evaluate=observed_evaluate
    cls.asyncSetUp=setup

# Page objects are never serialized; the rest of the observer contains synthetic DOM only.
class SafeEncoder(json.JSONEncoder):
    def default(self,obj):return '<local browser page>'
# capture() drops the page handle before serializing.
_original_capture=capture
async def capture(page,reason,observed):
    saved=current.pop('page',None)
    try:return await _original_capture(page,reason,observed)
    finally:
        if saved:current['page']=saved

instrument(c1.FinalPolishTests);instrument(f3.RunLineagePolishTests)
suite=unittest.TestSuite()
for rate in (1,2):
    for _ in range(4):
        for cls,name in [(c1.FinalPolishTests,'test_c1_overview_hero_has_local_art_process_and_unchanged_actions'),(f3.RunLineagePolishTests,'test_f3_case_flow_keeps_steps_without_decorative_truck')]:
            case=cls(name);case.cpu_rate=rate;suite.addTest(case)
result=unittest.TextTestRunner(verbosity=2).run(suite)
(OUT/'result.json').write_text(json.dumps({'source':os.environ['SOURCE_REF'],'run':os.environ.get('GITHUB_RUN_ID'),'tests':result.testsRun,
 'failures':[{'test':str(t),'trace':v} for t,v in result.failures+result.errors],'observations':records},indent=2))
print('BROWSER_DIAGNOSTIC_RESULT='+json.dumps({'source':os.environ['SOURCE_REF'],'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}),flush=True)
sys.exit(not result.wasSuccessful())
