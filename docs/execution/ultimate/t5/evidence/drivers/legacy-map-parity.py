"""Reproduce the pre-STOP legacy Map reference with the final T5 frontend."""
import asyncio,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'/workspace/Dation/backend/tests/browser')
import test_saga3_ui as fixture
W=Path('/workspace/work/dation-t5');OUT=W/'legacy-map-parity';OUT.mkdir(exist_ok=True)
async def run():
    fixture.Saga3UITests.setUpClass();f=fixture.Saga3UITests();result=[]
    try:
        await f.asyncSetUp();await f.page.emulate_media(reduced_motion='reduce');await f.b.open('logistics-map');await f.page.wait_for_load_state('networkidle')
        for width in [1440,390]:
            await f.page.set_viewport_size({'width':width,'height':1000});path=OUT/f'after-{width}.png';await f.page.screenshot(path=str(path),full_page=True,animations='disabled')
            before=W/'visual-before'/f'map-{width}.png';a=hashlib.sha256(before.read_bytes()).hexdigest();b=hashlib.sha256(path.read_bytes()).hexdigest()
            result.append({'width':width,'before_sha256':a,'after_sha256':b,'pixels_equal':a==b})
    finally:
        await f.asyncTearDown();fixture.Saga3UITests.tearDownClass()
    (OUT/'parity.json').write_text(json.dumps({'same_fixture_theme_data':True,'viewports':result},indent=2)+'\n')
    assert all(r['pixels_equal'] for r in result),result
asyncio.run(run())
print('PASS: unchanged legacy Map pixels at 1440 and 390 against the preserved pre-STOP reference.')
