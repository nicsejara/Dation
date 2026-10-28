import asyncio
import json
from pathlib import Path
import unittest
import test_navigation
import test_home_hero
import test_saga4_ui

ids = [
 'test_home_hero.HomeHeroTests.test_art_is_small_and_reserves_geometry_and_content_survives_failure',
 'test_navigation.NavigationTests.test_dashboard_toolbars_share_controls_and_symmetric_bleed',
 'test_navigation.NavigationTests.test_case_ux_real_data_change_retains_lineage_but_reopening_history_has_no_new_notice',
 'test_saga4_ui.Saga4UITests.test_shared_case_context_and_compact_map_milestones',
]
folder=Path('/workspace/work/dation-t0r2/browser-diagnostic');folder.mkdir(exist_ok=True)
for cls,name in [(test_home_hero.HomeHeroTests,ids[0].split('.')[-1]),(test_navigation.NavigationTests,ids[1].split('.')[-1]),(test_navigation.NavigationTests,ids[2].split('.')[-1]),(test_saga4_ui.Saga4UITests,ids[3].split('.')[-1])]:
 original=getattr(cls,name)
 def wrap(fn):
  async def test(self):
   try:return await fn(self)
   except Exception:
    b=getattr(self,'b',self)
    state={'name':fn.__name__,'url':self.page.url,'text':await self.page.locator('body').inner_text(),'requests':b.requests,'fixture_errors':b.fixture_errors,'errors':b.errors,'workspace':await self.page.evaluate('window.DationDispatch?.getWorkspace()')}
    (folder/(fn.__name__+'.json')).write_text(json.dumps(state,indent=2))
    await self.page.screenshot(path=str(folder/(fn.__name__+'.png')))
    raise
  return test
 setattr(cls,name,wrap(original))
suite=unittest.TestLoader().loadTestsFromNames(ids)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
