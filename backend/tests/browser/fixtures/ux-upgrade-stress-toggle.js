// QA fixture only. This file is never referenced by the application template.
addEventListener('DOMContentLoaded',()=>{
 const panel=document.createElement('aside');panel.setAttribute('aria-label','QA data');panel.dataset.uxStressToggle='';
 panel.style.cssText='position:fixed;bottom:4px;left:50%;transform:translateX(-50%);z-index:20000;display:flex;gap:4px;padding:4px;background:#ddd;border-radius:8px;color:#111;font:12px system-ui';
 for(const [mode,label]of [['demo','Demo data'],['worst','Worst case'],['empty','Empty'],['one','One']]){
  const b=document.createElement('button');b.textContent=label;b.type='button';
  b.addEventListener('click',async()=>{await window.uxStressSetMode(mode);const url=new URL(location.href);url.searchParams.set('ux_stress',mode);location.assign(url);});panel.append(b);
 }
 document.body.append(panel);
});
