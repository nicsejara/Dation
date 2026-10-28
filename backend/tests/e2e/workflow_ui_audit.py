"""Rendered workflow contracts exercised against the disposable real API."""
from pathlib import Path


THEME = (Path(__file__).parents[1] / 'browser/theme_audit.js').read_text()


class WorkflowUIAudit:
    def __init__(self, page, artifacts, viewport):
        self.page, self.artifacts, self.viewport = page, artifacts, viewport
        self.checkpoints, self.heroes, self.bars, self.actions, self.reviews = [], [], [], [], []
        self.toolbars = []
        self.action_reference = None
        self.review_reference = None

    async def checkpoint(self, name, selector='.view.is-active'):
        result = await self.page.evaluate(THEME, selector)
        assert not result['overflow'] and not result['failures'], (name, result)
        assert result['scheme'] == 'dark' and not result['legacyBoundary'], (name, result)
        self.checkpoints.append({'name': name, 'view': await self.page.evaluate('window.dationGetCurrentView()'),
                                 'viewport': self.page.viewport_size, **result})
        if self.artifacts:
            self.artifacts.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=str(self.artifacts / (name + '.png')))

    async def action(self, name, button):
        await button.wait_for(state='visible')
        assert not await button.is_disabled(), name
        await self.page.mouse.move(0, 0)
        actual = await button.evaluate('''el=>{
            const s=getComputedStyle(el),icon=el.querySelector('svg');
            return {style:Object.fromEntries(['minHeight','padding','borderRadius','fontFamily','fontSize','fontWeight','gap','backgroundColor','color'].map(k=>[k,s[k]])),
                lineHeight:s.lineHeight,continuation:el.matches('[data-after-approve]'),
                primary:el.classList.contains('d-button--primary'),shared:el.classList.contains('d-button--workflow'),icons:el.querySelectorAll('svg').length,
                decorative:icon?.getAttribute('aria-hidden'),clipped:el.scrollWidth>el.clientWidth||el.scrollHeight>el.clientHeight};
        }''')
        assert actual['shared'] and actual['icons'] == 1 and actual['decorative'] == 'true', (name, actual)
        assert not actual['clipped'] and actual['style']['minHeight'] == '46px', (name, actual)
        assert actual['primary'], (name, actual)
        # Contextual continuation wraps at 1.4 (dashboard-toolbar.css); other
        # workflow controls use 1.35. Shared style remains identical.
        assert actual['lineHeight']==('18.2px' if actual['continuation'] else '17.55px'),(name,actual)
        if self.action_reference is None:
            self.action_reference = actual['style']
        assert actual['style'] == self.action_reference, (name, actual, self.action_reference)
        await button.hover()
        hover = await button.evaluate('el=>getComputedStyle(el).backgroundColor')
        assert hover != actual['style']['backgroundColor'], (name, hover)
        await self.page.mouse.move(0, 0)
        self.actions.append({'name': name, **actual, 'hover': hover})

    async def hero(self, name, decision=None):
        hero = self.page.locator('.view.is-active .d-page-hero--workflow')
        await hero.wait_for()
        actual = await hero.evaluate('''el=>{
            const r=el.getBoundingClientRect(),step=el.querySelector('.d-hero-meta__step'),decision=el.querySelector('.d-hero-meta__decision');
            const s=step.getBoundingClientRect(),d=decision?.getBoundingClientRect();
            return {height:r.height,overflow:el.scrollWidth>el.clientWidth,panel:el.querySelector('.dispatch-pro-hero-visual')?.getBoundingClientRect().height??null,optional:el.querySelector('.dispatch-pro-hero-visual')?.tagName==='DETAILS',minimum:getComputedStyle(el).minHeight,
                stepSize:parseFloat(getComputedStyle(step).fontSize),stepWeight:parseFloat(getComputedStyle(step).fontWeight),
                decision:decision?{text:decision.textContent,below:d.top>=s.bottom+3.5,aligned:Math.abs(d.left-s.left)<.5,
                    size:parseFloat(getComputedStyle(decision).fontSize),weight:parseFloat(getComputedStyle(decision).fontWeight),
                    padding:getComputedStyle(decision).padding,border:getComputedStyle(decision).borderWidth}:null};
        }''')
        assert not actual['overflow'] and actual['height']>0 and actual['minimum']=='0px', (name, actual)
        if name.startswith('data'):assert actual['panel'] is None,(name,actual)
        else:assert actual['optional'] and actual['panel']>0,(name,actual)
        if decision:
            d = actual['decision']
            assert d and d['text'] == decision,(name,actual)
            assert d['size']==actual['stepSize']==12 and d['weight']==actual['stepWeight']==500,(name,actual)
            assert d['padding']=='0px' and d['border']=='0px',(name,actual)
        else:
            assert actual['decision'] is None, (name, actual)
        self.heroes.append({'name': name, **actual})

    async def bar(self, name, count):
        bar = self.page.locator('.d-workflow-action-bar')
        actual = await bar.evaluate('''el=>{
            const items=[...el.querySelectorAll('.d-workflow-action-bar__item')];
            return {items:items.map(item=>{const r=item.getBoundingClientRect();return {width:r.width,height:r.height,
                clipped:item.scrollWidth>item.clientWidth||item.scrollHeight>item.clientHeight};}),
                actionWidth:el.querySelector('.d-button').getBoundingClientRect().width,overflow:el.scrollWidth>el.clientWidth};
        }''')
        items = actual['items']
        assert len(items) == count and not actual['overflow'], (name, actual)
        assert all(not item['clipped'] for item in items), (name, actual)
        assert max(i['width'] for i in items) - min(i['width'] for i in items) < .5, (name, actual)
        assert max(i['height'] for i in items) - min(i['height'] for i in items) < .5, (name, actual)
        assert actual['actionWidth'] > items[0]['width'], (name, actual)
        self.bars.append({'name': name, **actual})

    async def review(self, kind):
        dialog = self.page.locator('dialog.d-execution-review[open]')
        await dialog.wait_for()
        assert await dialog.evaluate("el=>el.matches(':modal')")
        labels = await dialog.locator('.d-execution-review__row strong').all_text_contents()
        assert labels == (['Decision Case', 'Decision Owner', 'Alcance', 'Objetivo', 'Prioridades', 'Recursos'] if kind == 'assignment'
                          else ['Decision Case', 'Decision Owner', 'Entrada', 'Ventana', 'Reglas por foco', 'Objetivo', 'Recursos']), labels
        actual = await dialog.evaluate('''el=>{
            const style=node=>{const s=getComputedStyle(node);return Object.fromEntries(
                ['padding','borderRadius','font','color','background','gap','maxWidth','maxHeight'].map(k=>[k,s[k]]));};
            const r=el.getBoundingClientRect();
            return {width:r.width,center:Math.abs(r.x+r.width/2-innerWidth/2),height:r.height,
                style:{shell:style(el),heading:style(el.querySelector('h2')),row:style(el.querySelector('.d-execution-review__row')),
                    value:style(el.querySelector('.d-execution-review__row span')),footer:style(el.querySelector('footer'))}};
        }''')
        assert actual['width'] == min(650, self.viewport['width'] - 32) and actual['center'] < .5, actual
        assert actual['height'] <= self.viewport['height'] - 32, actual
        if self.review_reference is None:
            self.review_reference = actual['style']
        assert actual['style'] == self.review_reference, (kind, actual, self.review_reference)
        secondary = dialog.get_by_role('button', name='Volver', exact=True)
        assert 'd-button--secondary' in await secondary.get_attribute('class')
        await self.action(kind + '-execute', dialog.locator('[data-config-execute],[data-scheduling-execute]'))
        await self.checkpoint(kind + '-review', 'dialog[open]')
        buttons = dialog.get_by_role('button')
        await buttons.last.focus()
        await self.page.keyboard.press('Tab')
        assert await buttons.first.evaluate('el=>el===document.activeElement')
        await self.page.keyboard.press('Shift+Tab')
        assert await buttons.last.evaluate('el=>el===document.activeElement')
        self.reviews.append({'name': kind, **actual, 'tab_trap': True, 'secondary_role': True})

    async def toolbar(self, name):
        toolbar = self.page.locator('.view.is-active [data-dashboard-toolbar]')
        actual = await toolbar.evaluate('''el=>{
            const r=el.getBoundingClientRect(),m=el.closest('.d-decision-dashboard').querySelector('main').getBoundingClientRect(),h=el.closest('#dispatch-hero')?.getBoundingClientRect();
            const tools=[...el.querySelectorAll(el.dataset.toolbarPlacement==='hero'?'.dashboard-toolbar__menu>summary':'[data-dashboard-map],.dashboard-toolbar__menu>summary')].filter(button=>button.getClientRects().length).map(button=>{
                const r=button.getBoundingClientRect(),s=getComputedStyle(button);
                return {width:r.width,height:r.height,padding:s.padding,radius:s.borderRadius,font:s.font,gap:s.gap};});
            const primary=[...el.querySelectorAll('.d-button')].find(button=>button.getClientRects().length)?.getBoundingClientRect();
            return {hero:el.dataset.toolbarPlacement==='hero',insideHero:h?r.left>=h.left&&r.right<=h.right:false,left:m.left-r.left,right:r.right-m.right,tools,
                primary:primary?{width:primary.width,height:primary.height}:null};
        }''')
        bleed = 24 if self.viewport['width'] > 1100 else 12 if self.viewport['width'] > 760 else 0
        if actual['hero']:assert actual['insideHero'],actual
        else:assert abs(actual['left'] - bleed) < .25 and abs(actual['right'] - bleed) < .25, actual
        assert len(actual['tools']) == (2 if actual['hero'] else 3)
        reference = actual['tools'][0]
        for tool in actual['tools'][1:]:
            assert abs(tool['width'] - reference['width']) < .25 and abs(tool['height'] - reference['height']) < .25, actual
            assert all(tool[key] == reference[key] for key in ('padding', 'radius', 'font', 'gap')), actual
        assert actual['primary'], actual
        if self.viewport['width'] <= 760:
            assert abs(actual['primary']['height'] - reference['height']) < .25, actual
        else:
            assert actual['primary']['height'] > reference['height'], actual
        if self.viewport['width'] > 760:
            assert actual['primary']['width'] > reference['width'], actual
        self.toolbars.append({'name': name, **actual})

    def report(self):
        return {'viewport': self.viewport, 'checkpoints': self.checkpoints, 'heroes': self.heroes,
                'bars': self.bars, 'actions': self.actions, 'reviews': self.reviews, 'toolbars': self.toolbars}
