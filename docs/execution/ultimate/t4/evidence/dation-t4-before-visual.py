from pathlib import Path
import json,sys,threading
from http.server import ThreadingHTTPServer
sys.path.insert(0,'/workspace/Dation/backend/tests/browser')
from test_platform_foundation import _FixtureHandler
from playwright.sync_api import sync_playwright
out=Path('/workspace/work/dation-t4/visual-before');out.mkdir(exist_ok=True)
server=ThreadingHTTPServer(('127.0.0.1',0),_FixtureHandler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  for width in (1440,390):
   page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce')
   page.goto(f'http://127.0.0.1:{server.server_port}/foundation');page.wait_for_selector('html[data-foundation-ready="true"]')
   page.screenshot(path=str(out/f'foundation-{width}.png'),full_page=True,animations='disabled')
   values=page.evaluate('''()=>Object.fromEntries(['.d-input','.d-button--primary','.d-field__label','.d-page-header__title'].map(s=>{const n=document.querySelector(s),c=getComputedStyle(n);return [s,Object.fromEntries(['fontFamily','fontSize','lineHeight','padding','borderRadius','backgroundColor','color'].map(k=>[k,c[k]]))]}))''')
   (out/f'tokens-{width}.json').write_text(json.dumps(values,indent=2)+'\n');page.close()
  browser.close()
finally:server.shutdown();server.server_close();thread.join(5)
print('Current Dation form/card reference captured at 1440 and 390.')
