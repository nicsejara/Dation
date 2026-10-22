// UI projection only. Every business request rechecks database grants on the server.
export function ddaEnabled(identity,ddaId){
 return ddaId==='logistics'&&Boolean(identity?.membership?.workspace_id)&&
  (identity.ddas||[]).some(row=>row.workspace_id===identity.membership.workspace_id&&row.dda_id===ddaId&&row.status==='enabled');
}
export function logisticsView(view){
 return view?.startsWith('logistics-')||['overview','decision-dashboard','traceability','library'].includes(view);
}
export function currentLogisticsEnabled(){return ddaEnabled(window.dationSession?.identity,'logistics');}

// Kept independent of the optional catalog/app module so fallback HTML is safe.
export function syncEntitlementFallback(){
 const enabled=currentLogisticsEnabled();
 const sidebar=document.querySelector('.asset-item[data-view="logistics-overview"]');
 if(sidebar){
  sidebar.disabled=!enabled;sidebar.setAttribute('aria-disabled',String(!enabled));
  sidebar.title=enabled?'DDA Logística':'DDA Logística · No habilitado en este workspace';
  const dot=sidebar.querySelector('.status-dot');dot.hidden=!enabled;dot.style.display=enabled?'':'none';
  dot.setAttribute('aria-label',enabled?'Activo':'No habilitado');
 }
 const fallback=document.querySelector('[data-dda-fallback]');
 if(fallback){
  const button=fallback.querySelector('button');button.disabled=!enabled;
  button.setAttribute('aria-disabled',String(!enabled));
  fallback.querySelector('[data-dda-fallback-state]').textContent=enabled?'Disponible':'No habilitado';
  document.querySelector('[data-dda-counts]').textContent=enabled?'Logística disponible hoy':'Logística no habilitada en este workspace';
 }
}
