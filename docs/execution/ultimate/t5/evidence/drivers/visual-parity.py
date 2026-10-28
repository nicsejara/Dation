"""Compare native primitives before/after loading T5's scoped CSS, no APIs."""
from pathlib import Path
from http.server import ThreadingHTTPServer
import hashlib,json,re,sys,threading
from urllib.parse import urlsplit
sys.path.insert(0,'/workspace/Dation/backend/tests/browser')
from test_platform_foundation import _FixtureHandler,ROOT,FIXTURE
from playwright.sync_api import sync_playwright

OUT=Path('/workspace/work/dation-t5/visual-parity');OUT.mkdir(exist_ok=True)
class Handler(_FixtureHandler):
 def do_GET(self):
  if urlsplit(self.path).path!='/foundation':return super().do_GET()
  links=re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*>',(ROOT/'app/templates/app.html').read_text())
  if 'after' in self.path:links.append('<link rel="stylesheet" href="/static/css/ultimate-graph.css">')
  body=FIXTURE.read_text().replace('<!-- runtime-styles -->','\n'.join(links)).encode()
  self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
  for width in [1440,1280,1024,768,390]:
   measurements={};pixels={}
   for state in ['before','after']:
    page=browser.new_page(viewport={'width':width,'height':1000},reduced_motion='reduce')
    page.goto(f'http://127.0.0.1:{server.server_port}/foundation?{state}');page.wait_for_selector('html[data-foundation-ready="true"]');page.evaluate('document.fonts.ready');page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    path=OUT/f'{state}-{width}.png';page.screenshot(path=str(path),full_page=True,animations='disabled');pixels[state]=hashlib.sha256(path.read_bytes()).hexdigest()
    measurements[state]=page.evaluate('''()=>Object.fromEntries(['.d-input','.d-button--primary','.d-field__label','.d-page-header__title','.d-card'].map(s=>{const n=document.querySelector(s);if(!n)return [s,null];const c=getComputedStyle(n);return [s,Object.fromEntries(['fontFamily','fontSize','fontWeight','lineHeight','padding','gap','borderRadius','borderColor','borderWidth','boxShadow','backgroundColor','color'].map(k=>[k,c[k]]))]}))''');page.close()
   assert measurements['before']==measurements['after'],width
   assert pixels['before']==pixels['after'],width
   results.append(dict(width=width,pixels_equal=True,computed_styles_equal=True,sha256=pixels,styles=measurements['after']))
  browser.close()
finally:server.shutdown();server.server_close();thread.join(5)
(OUT/'parity.json').write_text(json.dumps({'same_fixture_theme_data':True,'t5_stylesheet_loaded_after':True,'viewports':results},indent=2)+'\n')
print('PASS: native component pixels/styles equal at five widths with T5 stylesheet loaded.')
