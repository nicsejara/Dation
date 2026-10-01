// Optional browser smoke test. Serve backend on :8765 and generate /tmp/dispatch100.json.
// Requires Playwright and a Chromium executable (CHROMIUM_PATH); APIs are mocked.
const {chromium}=require('playwright');
const fs=require('fs');
const assert=require('node:assert/strict');
const result=JSON.parse(fs.readFileSync(process.env.DATION_QA_RESULT||'/tmp/dispatch100.json','utf8'));
const ids={orders:'00000000-0000-4000-8000-000000000001',fleet:'00000000-0000-4000-8000-000000000002'};
const orders={id:ids.orders,dataset_type:'orders',original_filename:'orders.csv',row_count:100,created_at:'2026-10-01T00:00:00Z',profile_json:{profile:{total_units:2682,total_weight_kg:2384000,routes:28,date_from:'2026-10-01',date_to:'2026-10-10'}}};
const fleet={id:ids.fleet,dataset_type:'fleet',original_filename:'fleet.csv',label:'Flota sintética',row_count:4,created_at:'2026-10-01T00:00:00Z',is_default:true,profile_json:{profile:{fleet:result.fleet}}};
result.inputs.orders={...result.inputs.orders,dataset_id:ids.orders,filename:'orders.csv'};
result.inputs.fleet={...result.inputs.fleet,dataset_id:ids.fleet,filename:'fleet.csv',label:'Flota sintética',created_at:fleet.created_at};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/tmp/chromium',args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'],headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000},httpCredentials:{username:'dation',password:process.env.DATION_ACCESS_PASSWORD||'dispatch-qa'}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));let runId='00000000-0000-4000-8000-000000000003';
  await page.route('**/api/**',async route=>{
   const url=new URL(route.request().url()),p=url.pathname;let data={};
   if(p==='/api/dispatch/status')data={available:true};
   else if(p==='/api/datasets')data={items:url.searchParams.get('type')==='orders'?[orders]:url.searchParams.get('type')==='fleet'?[fleet]:[]};
   else if(p.endsWith('/profile'))data={dataset:p.includes(ids.orders)?orders:fleet};
   else if(p==='/api/runs/preflight')data={valid:true,warnings:result.inputs.preflight.warnings,errors:[],anomalies:[]};
   else if(p==='/api/runs'&&route.request().method()==='POST'){
    const body=route.request().postDataJSON();
    assert.equal(body.configuration.objective,'custom');
    assert.equal(Object.values(body.configuration.weights).reduce((a,b)=>a+b,0),1);
    runId=url.searchParams.get('run_id');data={id:runId,status:'completed',result_json:result};
   }
   else if(p==='/api/runs')data={items:[]};
   else if(p.endsWith('/interpretation'))data={messages:[],explanation:null};
   else if(p.startsWith('/api/runs/'))data={id:runId,status:'completed',result_json:result};
   else if(p==='/api/workspace/summary')data={datasets:2,runs:0};
   else if(p==='/api/system/supabase-check')data={ok:true};
   else if(p==='/api/system/llm-status')data={configured:false};
   await route.fulfill({json:data});
  });
  await page.goto(process.env.DATION_QA_URL||'http://127.0.0.1:8765/app');
  await page.waitForFunction(()=>window.DationDispatch);
  await page.evaluate(()=>window.dationNavigate('logistics-data'));
  await page.locator('[data-kind="orders"] [data-select]').selectOption(ids.orders);
  await page.locator('[data-next]').click();await page.locator('[data-review]').waitFor();
  await page.locator('[data-preset="min_time"]').click();await page.locator('[data-slider="cost"]').fill('40');
  await page.locator('[data-review]').click();await page.locator('[data-execute]').click();
  await page.locator('#dispatch-hero h1').waitFor();
  await page.screenshot({path:'/tmp/dation-desktop.png',fullPage:true,animations:'disabled'});
  const desktop=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,title:document.querySelector('#dispatch-hero h1').textContent,svg:document.querySelectorAll('#dispatch-dashboard-root svg').length}));
  await page.getByRole('tab',{name:'Viajes',exact:true}).click();await page.locator('input[name=search]').fill('V-00001');
  assert.equal(await page.locator('[data-count]').textContent(),'1 viajes encontrados');
  await page.getByRole('tab',{name:'Por orden',exact:true}).click();await page.locator('[data-chat]').click();
  await page.locator('.dispatch-chat textarea').waitFor();await page.locator('[data-close]').click();
  const downloaded=page.waitForEvent('download');await page.locator('[data-json]').click();assert.match((await downloaded).suggestedFilename(),/\.json$/);
  const csv=page.waitForEvent('download');await page.locator('[data-csv]').click();assert.equal((await csv).suggestedFilename(),'plan-de-viajes.csv');
  await page.reload();await page.locator('#dispatch-hero h1').waitFor();await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'/tmp/dation-mobile.png',fullPage:true,animations:'disabled'});
  const mobile=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
  await page.locator('[data-rerun]').click();await page.locator('[data-review]').waitFor();
  await page.screenshot({path:'/tmp/dation-config-mobile.png',fullPage:true,animations:'disabled'});
  const widths=await page.evaluate(()=>({footer:document.querySelector('#dispatch-config-root .dispatch-footer').getBoundingClientRect().width,panel:document.querySelector('#dispatch-config-root .dispatch-panel').getBoundingClientRect().width}));
  assert.equal(widths.footer,widths.panel);assert.equal(desktop.scroll,desktop.width);assert.equal(mobile.scroll,mobile.width);assert.deepEqual(errors,[]);
  console.log(JSON.stringify({desktop,mobile,widths,errors}));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
