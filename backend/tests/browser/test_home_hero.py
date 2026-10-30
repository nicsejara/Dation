"""Home hero acceptance using real static assets and isolated existing API fixtures."""
import datetime
import unittest
from pathlib import Path
from urllib.parse import urlsplit
import test_navigation as nav

WIDTHS=((1440,900),(1280,800),(1024,768),(768,1024),(375,812),(320,640))

class HomeHeroTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):nav.NavigationTests.setUpClass()
    @classmethod
    def tearDownClass(cls):nav.NavigationTests.tearDownClass()
    async def asyncSetUp(self):
        self.b=nav.NavigationTests();await self.b.asyncSetUp();self.page=self.b.page
        await self.page.emulate_media(reduced_motion='reduce')
    async def asyncTearDown(self):await self.b.asyncTearDown()
    async def open_home(self):
        await self.page.goto(f'http://127.0.0.1:{self.b.port}/app')
        await self.page.locator('.platform-home__greeting').wait_for()

    async def test_h1_h3_h4_h5_copy_network_band_and_reflow(self):
        await self.open_home()
        hero=self.page.locator('.platform-home__header')
        audit=(Path(__file__).parent/'theme_audit.js').read_text()
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            self.assertEqual(await hero.locator('.platform-home__eyebrow').inner_text(),'DATION · DECISION INTELLIGENCE')
            self.assertEqual(' '.join((await hero.locator('h1').inner_text()).split()),'De tus datos a decisiones que podés explicar y repetir.')
            self.assertEqual(await hero.locator('.d-page-description').inner_text(),'Dation combina datos, reglas y motores de decisión para que cada análisis tenga contexto, evidencia y trazabilidad.')
            self.assertEqual(await hero.locator('.platform-home__chain strong').all_inner_texts(),['Data Pack','Decision Case','Decision Run'])
            self.assertEqual(await hero.locator('.platform-home__chain li>span').all_inner_texts(),['Datos y contexto de la decisión','Objetivo, reglas y responsables','Alternativas, evidencia y aprobación'])
            self.assertEqual(await hero.locator('.platform-home__chain a,.platform-home__chain button').count(),0)
            image=hero.locator('img');self.assertEqual(await image.get_attribute('alt'),'')
            self.assertEqual(await image.get_attribute('width'),'724');self.assertEqual(await image.get_attribute('height'),'543')
            if width>700:
                await self.page.wait_for_function('document.querySelector(".platform-home__network img").naturalWidth===724')
                self.assertTrue(await image.is_visible())
            else:self.assertFalse(await image.is_visible())
            self.assertEqual(await self.page.locator('.view.is-active h1').count(),1)
            metrics=await self.page.evaluate(audit)
            self.assertFalse(metrics['overflow'],width);self.assertEqual(metrics['failures'],[],width)
        self.assertEqual(self.b.errors,[]);self.assertEqual(self.b.execution_bodies,[])

    async def test_h2_catalog_center_keyboard_and_history_use_existing_navigation(self):
        await self.open_home();hero=self.page.locator('.platform-home__header')
        primary=hero.get_by_role('link',name='Explorar DDA',exact=True)
        secondary=hero.get_by_role('link',name='Ir a Decision Center',exact=True)
        self.assertEqual(urlsplit(await secondary.get_attribute('href')).path,'/app/decisions')
        self.assertEqual(await secondary.get_attribute('href'),await self.page.locator('.platform-home__quick').get_by_role('link',name='Decision Center',exact=True).get_attribute('href'))
        for width,height in WIDTHS:
            await self.page.set_viewport_size({'width':width,'height':height})
            await primary.focus();await self.page.keyboard.press('Tab')
            self.assertTrue(await secondary.evaluate('e=>e===document.activeElement'))
            self.assertEqual(await secondary.evaluate('e=>getComputedStyle(e).outlineStyle'),'solid')
            await secondary.press('Enter')
            await self.page.wait_for_function("window.dationGetCurrentView()==='platform-decisions'")
            self.assertEqual(urlsplit(self.page.url).path,'/app/decisions')
            await self.page.go_back();await self.page.locator('.platform-home__greeting').wait_for()
            await primary.press('Enter')
            self.assertEqual(await self.page.evaluate('document.activeElement.id'),'dation-dda-title')
            self.assertEqual(await self.page.evaluate('location.pathname'),'/app')
        self.assertFalse(any(m=='POST' and p in ('/api/runs','/api/decision-cases') for m,p in self.b.requests))

    async def test_h6_greeting_keeps_workspace_timezone_identity_updates_and_fallback(self):
        for timestamp,timezone,expected in [('2026-10-24T02:00:00Z','America/Argentina/Buenos_Aires','Buenas noches'),('2026-10-24T14:00:00Z','UTC','Buenas tardes'),('2026-10-24T03:00:00Z','UTC','Buenos días')]:
            await self.page.clock.set_fixed_time(datetime.datetime.fromisoformat(timestamp.replace('Z','+00:00')))
            self.b.workspace_settings['workspace']['timezone']=timezone
            await self.open_home()
            self.assertEqual(await self.page.locator('.platform-home__greeting').inner_text(),expected+', Synthetic')
        await self.page.evaluate("window.dationSession.identity.profile.first_name=\"Seán O'Brien-Ó Súilleabháin\";dispatchEvent(new Event('dation:identity'))")
        self.assertIn("Seán O'Brien-Ó Súilleabháin",await self.page.locator('.platform-home__greeting').inner_text())
        await self.page.evaluate("window.dationSession.identity.profile.first_name='';dispatchEvent(new Event('dation:identity'))")
        self.assertEqual(await self.page.locator('.platform-home__greeting').inner_text(),'Buenos días')
        self.assertEqual(self.b.execution_bodies,[])

    async def test_h5_zoom_200_percent_keeps_hero_ctas_visible_with_keyboard(self):
        await self.open_home()
        session=await self.b.context.new_cdp_session(self.page)
        await session.send('Emulation.setDeviceMetricsOverride',{'width':720,'height':450,'deviceScaleFactor':2,'mobile':False})
        focus=(Path(__file__).parent/'focus_audit.js').read_text()
        for link in await self.page.locator('.platform-home__hero-actions a').all():
            await link.focus();state=await self.page.evaluate(focus)
            self.assertFalse(state['occluded'] or state['outside'],state)
        self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        await session.send('Emulation.clearDeviceMetricsOverride')

    async def test_art_is_small_and_reserves_geometry_and_content_survives_failure(self):
        import asyncio
        asset=nav.ROOT/'app/static/assets/home-isometric.webp'
        self.assertLess(asset.stat().st_size,110_000)
        async def slow_art(route):
            await asyncio.sleep(.5)
            await route.fulfill(path=asset,content_type='image/webp')
        await self.b.context.route('**/home-isometric.webp',slow_art)
        await self.open_home()
        hero=self.page.locator('.platform-home__header')
        before=await hero.bounding_box()
        await self.page.wait_for_function('document.querySelector(".platform-home__network img").naturalWidth>0')
        self.assertEqual(await hero.bounding_box(),before)
        await self.b.context.unroute('**/home-isometric.webp',slow_art)
        await self.b.context.route('**/home-isometric.webp',lambda route:route.abort())
        await self.open_home()
        self.assertEqual(await hero.get_by_role('link').count(),2)
        self.assertTrue(await hero.locator('h1').is_visible())
        self.assertEqual(await self.page.locator('.platform-home__quick-link').count(),4)
        self.assertEqual(self.b.errors,[])

    async def test_alignment_matches_logistics_frame_and_control_geometry(self):
        for width,height in WIDTHS+((1920,1080),):
            await self.page.set_viewport_size({'width':width,'height':height})
            measured=[]
            for path,hero_selector,actions in [('/app','.platform-home__header','.platform-home__hero-actions a'),('/app/ddas/logistics','.dda-landing__hero','.dda-landing__hero-actions button')]:
                await self.page.goto(f'http://127.0.0.1:{self.b.port}'+path)
                hero=self.page.locator(hero_selector);await hero.wait_for()
                await self.page.evaluate('document.fonts.ready')
                measured.append(await hero.evaluate('''(hero,selector)=>{
                    const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
                    const s=getComputedStyle(hero),copy=hero.querySelector('.d-product-hero__copy'),panel=hero.querySelector('.d-product-hero__panel'),p=getComputedStyle(panel);
                    return {hero:rect(hero),padding:s.padding,radius:s.borderRadius,copy:rect(copy),panel:{background:p.backgroundColor,border:p.border,radius:p.borderRadius,padding:p.padding},buttons:[...hero.querySelectorAll(selector)].map(e=>{
                        const s=getComputedStyle(e),r=e.getBoundingClientRect(),walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT),range=document.createRange();let n,inkFits=true;
                        while(n=walker.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('svg'))continue;range.selectNodeContents(n);for(const b of range.getClientRects())if(b.left<r.left+1||b.right>r.right-1||b.top<r.top||b.bottom>r.bottom)inkFits=false;}
                        return {...rect(e),inkFits,padding:s.padding,radius:s.borderRadius,font:s.fontSize,weight:s.fontWeight,line:s.lineHeight};
                    })};
                }''',actions))
            home,logistics=measured
            self.assertAlmostEqual(home['hero']['x'],logistics['hero']['x'],delta=.5)
            self.assertAlmostEqual(home['hero']['width'],logistics['hero']['width'],delta=.5)
            if width>700:self.assertAlmostEqual(home['hero']['height'],logistics['hero']['height'],delta=.5)
            for key in ('padding','radius','panel'):self.assertEqual(home[key],logistics[key],(width,key))
            self.assertAlmostEqual(home['copy']['y']-home['hero']['y'],21 if width<=700 else 25,delta=.1)
            self.assertAlmostEqual(home['copy']['x']-home['hero']['x'],21 if width<=700 else 25,delta=.1)
            primary,secondary=home['buttons'];reference=logistics['buttons'][0]
            self.assertTrue(all(button['inkFits'] for page in measured for button in page['buttons']),(width,measured))
            self.assertAlmostEqual(primary['width'],secondary['width'],delta=.1)
            self.assertAlmostEqual(primary['height'],secondary['height'],delta=.1)
            self.assertGreaterEqual(reference['width'],44)  # Comenzar has its own text width; preserve touch size and ink checks.
            self.assertAlmostEqual(primary['height'],reference['height'],delta=.1)
            for key in ('padding','radius','font','weight','line'):
                self.assertEqual(primary[key],secondary[key],(width,key))
                self.assertEqual(primary[key],reference[key],(width,key))
            self.assertFalse(await self.page.evaluate('document.documentElement.scrollWidth>innerWidth'))
        self.assertEqual(self.b.errors,[]);self.assertEqual(self.b.execution_bodies,[])
