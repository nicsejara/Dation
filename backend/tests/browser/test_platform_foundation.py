"""Internal-only gallery: exercise the real runtime cascade without APIs or app routes."""
import json
import mimetypes
import os
from pathlib import Path
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "app/static"
FIXTURE = Path(__file__).parent / "fixtures/platform-foundation.html"
VIEWPORTS = (1440, 1280, 1024, 768, 390)


class _FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/foundation":
            template = (ROOT / "app/templates/app.html").read_text()
            links = re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*>', template)
            # The fixture uses runtime ordering, including any future additions.
            html = FIXTURE.read_text().replace("<!-- runtime-styles -->", "\n".join(links))
            body, mime = html.encode(), "text/html; charset=utf-8"
        elif path.startswith("/static/"):
            target = (STATIC / path.removeprefix("/static/")).resolve()
            if not target.is_relative_to(STATIC.resolve()) or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            mime = "text/javascript" if target.suffix == ".mjs" else mimetypes.guess_type(target)[0]
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PlatformFoundationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/foundation"
        cls.artifacts = Path(os.getenv("DATION_FOUNDATION_ARTIFACTS", str(Path(tempfile.gettempdir()) / "dation-foundation")))
        cls.artifacts.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    async def asyncSetUp(self):
        self.errors, self.api_requests = [], []
        self.pw = await async_playwright().start()
        executable = os.getenv("CHROMIUM_EXECUTABLE")
        if not executable and Path("/usr/bin/chromium").exists():
            executable = "/usr/bin/chromium"
        self.browser = await self.pw.chromium.launch(executable_path=executable, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        self.context = await self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.page = await self.context.new_page()
        self.page.set_default_timeout(6000)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("request", lambda request: self.api_requests.append(request.url) if "/api/" in request.url else None)
        await self.page.goto(self.url)
        await self.page.wait_for_selector('html[data-foundation-ready="true"]')

    async def asyncTearDown(self):
        await self.browser.close()
        await self.pw.stop()
        self.assertEqual(self.errors, [], "Gallery JavaScript errors")
        self.assertEqual(self.api_requests, [], "The internal gallery must not call business APIs")

    async def test_real_runtime_cascade_fits_five_widths_and_mobile_targets(self):
        """Long content wraps; only the explicitly scrollable table may overflow."""
        actual = await self.page.locator('link[rel="stylesheet"]').evaluate_all("nodes => nodes.map(n=>new URL(n.href).pathname)")
        template = (ROOT / "app/templates/app.html").read_text()
        expected = [urlsplit(src).path for src in re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"', template)]
        self.assertEqual(actual, expected)
        self.assertIn("/static/css/platform-components.css", actual)
        self.assertGreater(actual.index("/static/css/platform-components.css"), actual.index("/static/css/dation-design-system.css"))
        measurements = []
        for width in VIEWPORTS:
            with self.subTest(width=width):
                await self.page.set_viewport_size({"width": width, "height": 1000})
                await self.page.wait_for_timeout(40)
                geometry = await self.page.evaluate("""() => {
                  const box=n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width,height:r.height}};
                  const visible=n=>n.getClientRects().length && getComputedStyle(n).visibility!=='hidden';
                  const table=document.querySelector('.d-table-container');
                  const controls=[...document.querySelectorAll('.d-platform button:not(:disabled),.d-platform input:not(:disabled),.d-platform select,.d-platform textarea,.d-sidebar-item[href]')]
                    .filter(visible).map(n=>({name:n.getAttribute('aria-label')||n.id||n.textContent.trim().slice(0,30),
                      ...box(n.matches('.d-check,.d-radio,.d-switch')?n.closest('label'):n)}));
                  return {width:innerWidth,pageWidth:document.documentElement.scrollWidth,controls,
                    table:{...box(table),scrollWidth:table.scrollWidth},
                    headings:[...document.querySelectorAll('.d-page-header__title,.d-page-header__subtitle,.d-empty-state,.d-error-state')].map(n=>({...box(n),scrollWidth:n.scrollWidth})),
                    families:[...new Set([...document.querySelectorAll('[data-family]')].map(n=>n.dataset.family))]};
                }""")
                self.assertLessEqual(geometry["pageWidth"], width + 1, geometry)
                self.assertEqual(len(geometry["families"]), 9)
                self.assertLessEqual(geometry["table"]["right"], width + 1)
                for box in geometry["headings"]:
                    self.assertGreaterEqual(box["left"], -1)
                    self.assertLessEqual(box["right"], width + 1)
                    self.assertLessEqual(box["scrollWidth"], box["width"] + 1)
                if width == 390:
                    for control in geometry["controls"]:
                        self.assertGreaterEqual(control["height"], 40, control)
                        self.assertGreaterEqual(control["width"], 40, control)
                    self.assertGreater(geometry["table"]["scrollWidth"], geometry["table"]["width"])
                    # Keyboard users can reach and horizontally scroll the data region.
                    table = self.page.get_by_role("region", name="Archivos de ejemplo desplazables")
                    await table.focus()
                    await self.page.keyboard.press("ArrowRight")
                    await self.page.wait_for_timeout(80)
                    self.assertGreater(await table.evaluate("n=>n.scrollLeft"), 0)
                await self.page.screenshot(path=str(self.artifacts / f"foundation-{width}.png"), full_page=True)
                measurements.append(geometry)
        (self.artifacts / "geometry.json").write_text(json.dumps(measurements, indent=2, ensure_ascii=False))

    async def test_form_labels_validation_and_native_choice_keyboard(self):
        """Fields have real accessible labels and feedback; native controls remain usable."""
        unlabelled = await self.page.locator('input,select,textarea').evaluate_all("nodes=>nodes.filter(n=>!n.labels?.length||![...n.labels].some(l=>l.textContent.trim())).map(n=>n.outerHTML)")
        self.assertEqual(unlabelled, [])
        email = self.page.get_by_role("textbox", name="Correo de contacto")
        self.assertEqual(await email.get_attribute("aria-invalid"), "true")
        descriptions = (await email.get_attribute("aria-describedby")).split()
        self.assertIn("email-error", descriptions)
        for description in descriptions:
            self.assertTrue(await self.page.locator(f"#{description}").is_visible())
        await self.page.get_by_role("button", name="Validar formulario").click()
        self.assertTrue(await email.evaluate("n=>document.activeElement===n"))
        await email.fill("equipo@empresa.test")
        await self.page.get_by_role("button", name="Validar formulario").click()
        self.assertEqual(await email.get_attribute("aria-invalid"), "false")
        self.assertFalse(await self.page.locator("#email-error").is_visible())
        self.assertIn("Formulario válido", await self.page.locator("#form-result").inner_text())
        checkbox = self.page.get_by_role("checkbox", name="Recibir novedades del espacio")
        await checkbox.focus()
        await self.page.keyboard.press("Space")
        self.assertFalse(await checkbox.is_checked())
        switch = self.page.get_by_role("switch", name="Activar avisos")
        await switch.focus()
        await self.page.keyboard.press("Space")
        self.assertFalse(await switch.is_checked())
        await self.page.get_by_role("radio", name="Cómoda").focus()
        await self.page.keyboard.press("ArrowDown")
        self.assertTrue(await self.page.get_by_role("radio", name="Compacta").is_checked())
        await self.page.get_by_label("Formato", exact=True).select_option(label="XLSX")
        self.assertEqual(await self.page.get_by_label("Formato", exact=True).input_value(), "XLSX")
        self.assertTrue(await self.page.get_by_label("Fuente administrada").is_disabled())
        self.assertTrue(await self.page.get_by_label("Identificador", exact=True).evaluate("n=>n.readOnly"))
        self.assertTrue(await self.page.get_by_role("button", name="Guardando cambios").is_disabled())
        self.assertEqual(await self.page.get_by_role("button", name="Guardando cambios").get_attribute("aria-busy"), "true")
        disabled_item = self.page.get_by_role("button", name="Próximamente", exact=True)
        self.assertTrue(await disabled_item.is_disabled())
        appearance = await disabled_item.evaluate("n=>{const s=getComputedStyle(n);return [s.color,s.backgroundColor,s.cursor]}")
        await disabled_item.hover()
        self.assertEqual(await disabled_item.evaluate("n=>{const s=getComputedStyle(n);return [s.color,s.backgroundColor,s.cursor]}"), appearance)
        self.assertEqual(appearance[2], "not-allowed")

    async def test_dropdown_keyboard_outside_and_viewport_position(self):
        trigger = self.page.get_by_role("button", name="Más acciones", exact=True)
        menu = self.page.get_by_role("menu", name="Más acciones", exact=True)
        await trigger.focus()
        await self.page.keyboard.press("ArrowDown")
        self.assertTrue(await menu.is_visible())
        self.assertEqual(await trigger.get_attribute("aria-expanded"), "true")
        self.assertTrue(await self.page.locator("#menu-first").evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("ArrowDown")
        self.assertTrue(await self.page.locator("#menu-last").evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("Home")
        self.assertTrue(await self.page.locator("#menu-first").evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("End")
        self.assertTrue(await self.page.locator("#menu-last").evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("Escape")
        self.assertFalse(await menu.is_visible())
        self.assertTrue(await trigger.evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("ArrowUp")
        self.assertTrue(await self.page.locator("#menu-last").evaluate("n=>document.activeElement===n"))
        await self.page.keyboard.press("Enter")
        self.assertFalse(await menu.is_visible())
        self.assertTrue(await trigger.evaluate("n=>document.activeElement===n"))
        await trigger.click()
        await self.page.get_by_role("heading", name="Acciones", exact=True).click()
        self.assertFalse(await menu.is_visible())
        self.assertEqual(await trigger.get_attribute("aria-expanded"), "false")
        await trigger.focus()
        await self.page.keyboard.press("ArrowDown")
        await self.page.keyboard.press("Shift+Tab")
        await self.page.wait_for_timeout(30)
        self.assertFalse(await menu.is_visible(), "Leaving the menu with Tab must close it")
        await self.page.set_viewport_size({"width": 390, "height": 640})
        await trigger.click()
        box = await menu.bounding_box()
        self.assertGreaterEqual(box["x"], 0)
        self.assertLessEqual(box["x"] + box["width"], 390)
        self.assertGreaterEqual(box["y"], 0)
        self.assertLessEqual(box["y"] + box["height"], 640)
        for item in await menu.locator('button:not(:disabled)').all():
            item_box = await item.bounding_box()
            self.assertGreaterEqual(item_box["height"], 40)
        await self.page.screenshot(path=str(self.artifacts / "foundation-dropdown-390.png"))

    async def test_native_modal_traps_tab_escape_and_returns_focus(self):
        opener = self.page.get_by_role("button", name="Crear espacio de trabajo")
        await opener.click()
        dialog = self.page.get_by_role("dialog", name="Nuevo espacio de trabajo")
        self.assertTrue(await dialog.is_visible())
        self.assertTrue(await dialog.evaluate("n=>n.matches(':modal')"))
        self.assertTrue(await self.page.get_by_label("Nombre del nuevo espacio").evaluate("n=>document.activeElement===n"))
        await self.page.screenshot(path=str(self.artifacts / "foundation-modal-1440.png"))
        for key in ["Tab"] * 7 + ["Shift+Tab"] * 7:
            await self.page.keyboard.press(key)
            # Native dialog may focus its document between cycles, but never a background control.
            self.assertTrue(await dialog.evaluate("n=>n.contains(document.activeElement)||document.activeElement===document.body"))
        await self.page.keyboard.press("Escape")
        self.assertFalse(await dialog.is_visible())
        self.assertTrue(await opener.evaluate("n=>document.activeElement===n"))
        await self.page.set_viewport_size({"width": 390, "height": 640})
        await opener.click()
        box = await dialog.bounding_box()
        self.assertGreaterEqual(box["x"], 0)
        self.assertLessEqual(box["x"] + box["width"], 390)
        self.assertGreaterEqual(box["y"], 0)
        self.assertLessEqual(box["y"] + box["height"], 640)
        self.assertLessEqual(await dialog.evaluate("n=>n.scrollWidth-n.clientWidth"), 1)
        await self.page.screenshot(path=str(self.artifacts / "foundation-modal-390.png"))
        await self.page.locator("#modal-description").evaluate("n=>n.textContent=n.textContent.repeat(40)")
        self.assertGreater(await dialog.evaluate("n=>n.scrollHeight"), await dialog.evaluate("n=>n.clientHeight"))
        await self.page.get_by_role("button", name="Cancelar", exact=True).scroll_into_view_if_needed()
        await self.page.get_by_role("button", name="Cancelar", exact=True).click()
        self.assertFalse(await dialog.is_visible())
        self.assertTrue(await opener.evaluate("n=>document.activeElement===n"))

    async def test_actual_text_control_and_keyboard_focus_contrast(self):
        """Compute contrast from the rendered cascade, including primary gradient stops."""
        ratios = await self.page.evaluate("""() => {
          const rgba=s=>{const n=s.match(/[\\d.]+/g)?.map(Number)||[0,0,0,0];return [...n.slice(0,3),n[3]??1]};
          const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3]));
          const background=n=>{if(!n)return [7,16,21];const c=rgba(getComputedStyle(n).backgroundColor);return blend(c,background(n.parentElement))};
          const luminance=c=>c.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
          const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
          const nodes=[...document.querySelectorAll('.d-platform .d-button:not(:disabled),.d-field__label,.d-field__help,.d-field__error,.d-status,.d-page-header__title,.d-page-header__subtitle,.d-empty-state__title,.d-empty-state__description,.d-error-state__description,.d-sidebar-item:not(:disabled),.d-input:not(:disabled),.d-select,.d-textarea,.d-choice__copy,.d-caption,.d-metadata,.d-table th,.d-table td,.d-page-header__breadcrumbs a')]
            .filter(n=>n.getClientRects().length&&!n.closest('.d-choice:has(:disabled)'));
          return nodes.map(n=>{
            const s=getComputedStyle(n), bg=background(n), stops=s.backgroundImage.match(/rgba?\\([^)]*\\)/g), backgrounds=stops?stops.map(c=>blend(rgba(c),background(n.parentElement))):[bg];
            const label=n.id||n.className;
            return {label,text:Math.min(...backgrounds.map(b=>contrast(blend(rgba(s.color),b),b))),
              control:n.matches('.d-input,.d-select,.d-textarea')?contrast(blend(rgba(s.borderTopColor),bg),bg):null};
          });
        }""")
        for result in ratios:
            with self.subTest(element=result["label"]):
                self.assertGreaterEqual(result["text"], 4.5, result)
                if result["control"] is not None:
                    self.assertGreaterEqual(result["control"], 3, result)
        focus = []
        for selector in ("#primary-action", "#workspace-name", "#foundation-check", "#foundation-switch", ".d-sidebar-item[aria-current]"):
            control = self.page.locator(selector)
            await control.focus()
            await self.page.keyboard.press("Tab")
            await self.page.keyboard.press("Shift+Tab")
            result = await control.evaluate("""n=>{
              const s=getComputedStyle(n); const c=x=>x.match(/[\\d.]+/g).map(Number).slice(0,3);
              const l=x=>x.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
              let p=n.parentElement;while(p&&getComputedStyle(p).backgroundColor==='rgba(0, 0, 0, 0)')p=p.parentElement;
              const a=l(c(s.outlineColor)),b=l(c(getComputedStyle(p).backgroundColor));
              return {focused:document.activeElement===n,visible:n.matches(':focus-visible'),width:parseFloat(s.outlineWidth),style:s.outlineStyle,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
            }""")
            self.assertTrue(result["focused"], (selector, result))
            self.assertTrue(result["visible"], (selector, result))
            self.assertGreaterEqual(result["width"], 2, (selector, result))
            self.assertNotEqual(result["style"], "none", (selector, result))
            self.assertGreaterEqual(result["ratio"], 3, (selector, result))
            focus.append({"selector": selector, **result})
        (self.artifacts / "contrast.json").write_text(json.dumps({"text_and_controls": ratios, "focus": focus}, indent=2))

    async def test_remount_disposal_and_drawer_keep_single_handlers_and_focus(self):
        """Replacing scopes on the same DOM must remove listeners and close top layers."""
        trigger = self.page.get_by_role("button", name="Más acciones", exact=True)
        menu = self.page.get_by_role("menu", name="Más acciones", exact=True)
        for _ in range(3):
            await self.page.evaluate("""() => {
              const q=window.foundationQA, previous=q.dropdown;
              q.dropdown=q.mountDropdown({trigger:document.getElementById('menu-trigger'),panel:document.getElementById('foundation-menu')});
              if(previous.isOpen)throw new Error('Replaced dropdown remained open');
            }""")
            # Duplicate live click listeners toggle open then closed and fail this check.
            await trigger.click()
            self.assertTrue(await menu.is_visible())
            self.assertTrue(await self.page.evaluate("window.foundationQA.dropdown.isOpen"))
        await self.page.evaluate("window.foundationQA.dropdown.dispose()")
        self.assertFalse(await menu.is_visible())
        await trigger.click()
        self.assertFalse(await menu.is_visible(), "Disposed dropdown must not react to its old trigger")

        opener = self.page.get_by_role("button", name="Crear espacio de trabajo")
        dialog = self.page.get_by_role("dialog", name="Nuevo espacio de trabajo")
        await opener.click()
        self.assertTrue(await dialog.is_visible())
        # Replace an open dialog and reopen immediately, before its queued close event.
        await self.page.evaluate("""() => {
          const q=window.foundationQA, modal=document.getElementById('foundation-modal'), trigger=document.getElementById('open-modal');
          q.backgroundActivations=0;
          document.getElementById('primary-action').addEventListener('click',()=>q.backgroundActivations++);
          q.dialog=q.mountDialog({dialog:modal,trigger,initialFocus:document.getElementById('modal-name')});
          if(modal.open)throw new Error('Remount did not dispose the previous modal');
          trigger.click();
        }""")
        await self.page.wait_for_timeout(50)
        self.assertTrue(await dialog.is_visible())
        self.assertTrue(await dialog.evaluate("n=>n.matches(':modal')&&n.contains(document.activeElement)"))
        await self.page.keyboard.press("Escape")
        await self.page.wait_for_function("document.activeElement===document.getElementById('open-modal')")
        self.assertFalse(await dialog.is_visible())
        self.assertEqual(await self.page.evaluate("window.foundationQA.backgroundActivations"), 0)

        await opener.click()
        self.assertTrue(await dialog.is_visible())
        await self.page.evaluate("window.foundationQA.dialog.dispose()")
        self.assertFalse(await dialog.is_visible())
        self.assertTrue(await opener.evaluate("n=>document.activeElement===n"))
        await opener.click()
        self.assertFalse(await dialog.is_visible(), "Disposed modal must not react to its old trigger")

        await self.page.set_viewport_size({"width": 390, "height": 640})
        await self.page.evaluate("""() => {
          const q=window.foundationQA, dialog=document.getElementById('foundation-modal');
          dialog.classList.replace('d-modal','d-drawer');
          for(const suffix of ['header','title','body','actions']){
            const node=dialog.querySelector('.d-modal__'+suffix);node.classList.replace('d-modal__'+suffix,'d-drawer__'+suffix);
          }
          document.getElementById('modal-description').textContent+=' Contenido adicional con contexto de trabajo.'.repeat(100);
          q.dialog=q.mountDialog({dialog,trigger:document.getElementById('open-modal'),initialFocus:document.getElementById('modal-name')});
        }""")
        await opener.click()
        box = await dialog.bounding_box()
        self.assertGreaterEqual(box["x"], 0)
        self.assertLessEqual(box["x"] + box["width"], 390)
        self.assertGreaterEqual(box["y"], 0)
        self.assertLessEqual(box["y"] + box["height"], 640)
        self.assertLessEqual(await dialog.evaluate("n=>n.scrollWidth-n.clientWidth"), 1)
        self.assertGreater(await dialog.evaluate("n=>n.scrollHeight"), await dialog.evaluate("n=>n.clientHeight"))
        cancel = self.page.get_by_role("button", name="Cancelar", exact=True)
        await cancel.scroll_into_view_if_needed()
        self.assertGreater(await dialog.evaluate("n=>n.scrollTop"), 0)
        await self.page.screenshot(path=str(self.artifacts / "foundation-drawer-390.png"))
        await cancel.click()
        await self.page.wait_for_function("document.activeElement===document.getElementById('open-modal')")
        self.assertFalse(await dialog.is_visible())
        self.assertEqual(await self.page.evaluate("window.foundationQA.backgroundActivations"), 0)

    async def test_reduced_motion_and_zoom_preserve_readability(self):
        await self.page.emulate_media(reduced_motion="reduce")
        motion = await self.page.locator('.d-skeleton,.d-button[aria-busy="true"]').evaluate_all("nodes=>nodes.map(n=>({animation:getComputedStyle(n).animationName,after:getComputedStyle(n,'::after').animationName,duration:getComputedStyle(n).transitionDuration}))")
        for item in motion:
            self.assertEqual(item["animation"], "none", item)
            self.assertEqual(item["after"], "none", item)
            self.assertTrue(all(float(n.strip().removesuffix("s")) <= .01 for n in item["duration"].split(",")), item)
        # Browser zoom changes layout viewport; 200% at 1280px is a 640 CSS-pixel viewport.
        await self.page.set_viewport_size({"width": 640, "height": 500})
        self.assertLessEqual(await self.page.evaluate("document.documentElement.scrollWidth"), 641)
        await self.page.get_by_role("button", name="Crear espacio de trabajo").click()
        dialog = self.page.get_by_role("dialog", name="Nuevo espacio de trabajo")
        self.assertLessEqual(await dialog.evaluate("n=>n.scrollWidth-n.clientWidth"), 1)
        await self.page.get_by_role("button", name="Cancelar", exact=True).scroll_into_view_if_needed()
        await self.page.get_by_role("button", name="Cancelar", exact=True).click()
        self.assertFalse(await dialog.is_visible())


if __name__ == "__main__":
    unittest.main()
