"""Two real BFF sessions: invite, accept, assign and inspect responsive collaboration."""
import asyncio,json,os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
BASE=os.environ['DATION_E2E_URL'];assert urlsplit(BASE).hostname=='127.0.0.1'
CASE=os.environ['DATION_TEAM_CASE'];USER_B=os.environ['DATION_TEAM_USER_B']
async def main():
 errors=[];artifacts=Path(os.environ['DATION_E2E_ARTIFACTS'])/'collaboration' if os.getenv('DATION_E2E_ARTIFACTS') else None
 if artifacts:artifacts.mkdir(parents=True,exist_ok=True)
 theme=(Path(__file__).parents[1]/'browser/theme_audit.js').read_text()
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or '/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=await context.new_page();page.set_default_timeout(15000);page.on('pageerror',lambda e:errors.append(str(e)))
  async def login(page,email):
   await page.goto(BASE+'/login');await page.get_by_label('Email',exact=True).fill(email);await page.get_by_label('Contraseña',exact=True).fill('dispatch-e2e-private');await page.get_by_role('button',name='Ingresar',exact=True).click();await page.locator('[data-platform-home] h1').wait_for()
  await login(page,'user-1@example.test');await page.locator('.nav [data-platform-view=platform-team]').click();root=page.locator('[data-platform-team]');await root.get_by_role('table').wait_for()
  await root.get_by_role('button',name='Invitar',exact=True).click();dialog=page.get_by_role('dialog');await dialog.get_by_label('Email',exact=True).fill('user-2@example.test');await dialog.get_by_label('Rol de acceso').select_option('operator');await dialog.get_by_label('Responsabilidad de negocio').select_option('decision_owner');assert 'no envía un correo' in await dialog.inner_text();await dialog.get_by_role('button',name='Invitar',exact=True).click();await root.get_by_text('Invitación pendiente',exact=False).wait_for()
  second=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');other=await second.new_page();other.on('pageerror',lambda e:errors.append(str(e)));await login(other,'user-2@example.test');await other.locator('.nav [data-platform-view=platform-team]').click();incoming=other.locator('[data-platform-team] .team-incoming');await incoming.get_by_role('button',name='Aceptar invitación',exact=True).click();await other.locator('[data-platform-home] h1').wait_for();assert await other.locator('[data-workspace-name]').inner_text()=='Dation'
  await page.reload();await root.get_by_text('user-2@example.test',exact=True).wait_for();member_name=await root.get_by_role('row').filter(has_text='user-2@example.test').locator('strong').inner_text()
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');probe=await page.evaluate(theme);probe['width']=width
   if probe['overflow']:probe['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'team-{width}.png'),full_page=True)
  await page.evaluate('''async uid=>{const team=await (await fetch('/api/platform/team')).json(),member=team.members.find(m=>m.user_id===uid);const response=await fetch('/api/platform/team/members/'+uid+'/responsibilities',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({expected_updated_at:member.updated_at,business_roles:['decision_owner']})});if(!response.ok)throw Error('Responsibility setup failed');}''',USER_B)
  await page.set_viewport_size({'width':1440,'height':1000});await page.locator('.nav [data-platform-view=platform-decisions]').click();center=page.locator('[data-platform-decisions]');await center.get_by_role('link',name='Abrir',exact=True).click();node=center.locator('[data-center-node=logistics_assignment]');await center.locator('.center-drawer:visible .center-responsibilities').first.get_by_role('button',name='Asignar decision owner · Asignación de carga',exact=True).click();dialog=page.get_by_role('dialog');await dialog.get_by_label('Decision Owner',exact=True).select_option(USER_B);assert await dialog.get_by_label('Aprobador asignado',exact=True).count()==0;await dialog.get_by_role('button',name='Guardar',exact=True).click();await center.get_by_text('Responsable actualizado.',exact=True).wait_for();await page.reload();await center.get_by_role('heading',name='Cadena de decisiones',exact=True).wait_for();assert await center.locator('.center-drawer:visible .center-drawer__content>.center-responsibilities .center-person').filter(has_text=member_name).count()==1
  for width in (1440,1024,768,390):
   await page.set_viewport_size({'width':width,'height':1000});await page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');probe=await page.evaluate(theme);probe['width']=width
   if probe['overflow']:probe['outside']=await page.evaluate("[...document.querySelectorAll('body *')].filter(n=>n.getClientRects().length&&n.getBoundingClientRect().right>innerWidth+1).slice(0,20).map(n=>({tag:n.tagName,cls:n.className,right:n.getBoundingClientRect().right,width:n.getBoundingClientRect().width}))")
   assert not probe['overflow'] and not probe['failures'],probe
   if artifacts:await page.screenshot(path=str(artifacts/f'assigned-{width}.png'),full_page=True)
  await other.locator('.nav [data-platform-view=platform-team]').click();await other.locator('[data-platform-team]').get_by_role('table').wait_for();assert await other.locator('[data-platform-team]').get_by_role('button',name='Invitar',exact=True).count()==0
  assert errors==[],errors;await browser.close()
 print(json.dumps({'passed':True,'real_invite_acceptance':True,'assignment_reload':True,'read_only_team':True,'viewports':[1440,1024,768,390]}))
asyncio.run(main())
