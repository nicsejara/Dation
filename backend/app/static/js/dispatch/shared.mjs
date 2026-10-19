import {describeFailure,responseFailure} from './recovery.mjs';
import {chartPalette,themedChartOptions} from "./chart-theme.mjs";
import {scopeFor} from "./lifecycle.mjs";
export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const num=(v,d=0)=>v==null?'—':new Intl.NumberFormat('es-AR',{maximumFractionDigits:d}).format(v);
export const money=v=>v==null?'—':'$ '+num(v,2);
export const pct=v=>v==null?'—':num(v*100,1)+' %';
export const date=v=>v?new Intl.DateTimeFormat('es-AR',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(v+'T00:00:00Z')):'—';
export const vehicle=v=>({Truck_S:'Camión pequeño',Truck_M:'Camión mediano',Truck_L:'Camión grande',Third_Party_L:'Camión grande tercerizado'}[v]||String(v).replaceAll('_',' '));
export const metricInfo={total_cost:['Costo total',money,'Costo de ida y vuelta más costo fijo por viaje.'],on_time_rate:['Entregas a tiempo',pct,'Órdenes completadas dentro de su plazo / órdenes incluidas. El SLA se optimiza antes que el objetivo de negocio.'],late_orders:['Órdenes tardías',num,'Cantidad de órdenes cuya última entrega supera el plazo.'],avg_lead_time_days:['Tiempo medio',v=>num(v,2)+' días','Días desde disponibilidad hasta entrega, ponderados por unidades.'],own_weight_share:['Uso de flota propia',pct,'Peso transportado por recursos propios / peso total.'],own_load_utilization:['Ocupación de carga propia',pct,'Peso transportado / capacidad de los viajes propios utilizados.'],outsourced_weight_share:['Kg tercerizados',pct,'Peso tercerizado / peso total transportado.'],co2_kg:['CO₂ estimado',v=>num(v,1)+' kg','Kilómetros de ida y vuelta × factor informado; no certificado.'],total_trips:['Viajes',num,'Cantidad total de salidas; es KPI y desempate, no prioridad configurable.']};
export async function api(path,options={}){
 let r;try{r=await fetch(path,options);}catch(error){if(error.name==='AbortError'||error.name==='TimeoutError')throw error;throw Object.assign(new Error('No pudimos conectar con Dation.'),{kind:'disconnected'});}
 let data;try{data=await r.json();}catch{throw Object.assign(new Error('La respuesta del servicio no está disponible. Reintentá.'),{status:r.status||503,kind:'unavailable'});}
 if(!r.ok)throw responseFailure(r,data);return data;
}
export const post=(path,body,options={})=>api(path,{...options,method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export function download(name,content,type='application/json'){
  const blob=new Blob([content],{type});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');
  anchor.href=url;
  anchor.download=name;
  anchor.rel='noopener';
  anchor.style.display='none';
  document.body.append(anchor);
  try{
    anchor.click();
  }finally{
    anchor.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),5000);
  }
  return true;
}
export function csv(rows){return '\ufeff'+rows.map(row=>row.map(x=>{let s=String(x??'');if(/^[=+@\-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}).join(';')).join('\r\n');}
export function errorBox(root,error,retry){root.replaceChildren();const state=describeFailure(error),panel=document.createElement('section');panel.className='dispatch-panel d-recovery';panel.dataset.recoveryKind=state.kind;
 const title=document.createElement('h2');title.textContent=state.title;const p=document.createElement('p');p.className='dispatch-alert';p.role='alert';p.textContent=state.message;panel.append(title,p);
 if(state.errorDetail&&state.errorDetail!==state.message){const details=document.createElement('details'),summary=document.createElement('summary'),copy=document.createElement('p');summary.textContent='Detalles del problema';copy.textContent=state.errorDetail;details.append(summary,copy);panel.append(details);}
 const actions=document.createElement('div');actions.className='d-recovery__actions';
 if(state.kind==='session'){const a=document.createElement('a');a.className='d-button d-button--primary';a.href='/login?reason=session';a.textContent='Volver a ingresar';actions.append(a);}
 else if(retry){const b=document.createElement('button');b.type='button';b.textContent=error?.actionLabel||'Reintentar';b.onclick=retry;actions.append(b);}
 if(error?.status===404){const b=document.createElement('button');b.type='button';b.textContent='Ver Decision Center';b.onclick=()=>window.DationDispatch.openDecisionCenter({});actions.append(b);}
 panel.append(actions);root.append(panel);
}
export function chart(root,options){
  if(!window.DationCharts){root.textContent='El gráfico no está disponible. Consultá la tabla de esta sección.';return null;}
  root._dispose?.();
  const palette=chartPalette(root);
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const c=window.DationCharts.init(root,{color:palette.series,textStyle:{color:palette.text}},{renderer:'svg'});
  c.setOption({...themedChartOptions(options,palette,root.clientWidth),...(motion.matches?{animation:false}:{})});
  const updateMotion=()=>c.setOption({animation:!motion.matches&&options.animation!==false});
  motion.addEventListener('change',updateMotion);
  let disposed=false,release,compact=root.clientWidth<480;
  const observer=new ResizeObserver(()=>{
    if(disposed)return;
    const nextCompact=root.clientWidth<480;
    if(nextCompact!==compact){
      const themed=themedChartOptions(options,palette,root.clientWidth);
      c.setOption({...(themed.grid?{grid:themed.grid}:{}),...(themed.yAxis?{yAxis:themed.yAxis}:{})});
      compact=nextCompact;
    }
    c.resize();
  });observer.observe(root);
  root._dispose=()=>{if(disposed)return;disposed=true;observer.disconnect();motion.removeEventListener('change',updateMotion);c.dispose();release?.();};
  release=scopeFor(root)?.own(root._dispose);
  return c;
}

export function dispose(root){root.querySelectorAll('.dispatch-chart').forEach(n=>n._dispose?.());}
