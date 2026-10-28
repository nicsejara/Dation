import {esc} from '../shared.mjs';
import {sankeyLayout,ganttLayout} from './package.mjs';
const button=(type,id,label,graphNodeId=null)=>'<button type="button" class="d-button d-button--secondary" data-entity-type="'+esc(type)+'" data-entity-id="'+esc(id)+'" '+(graphNodeId?'data-graph-node="'+esc(graphNodeId)+'"':'')+'>'+esc(label)+'</button>';
export function sankeyMarkup(projection){
  const layout=sankeyLayout(projection),nodes=new Map(layout.nodes.map(n=>[n.id,n]));
  const links=layout.links.map(l=>{const a=nodes.get(l.source),b=nodes.get(l.target);if(!a||!b)throw new Error('INVALID_VISUAL_REFERENCE');
    return '<path data-flow-source="'+esc(a.id)+'" data-flow-target="'+esc(b.id)+'" d="M '+(a.x+12)+' '+a.y+' C '+(a.x+150)+' '+a.y+', '+(b.x-150)+' '+b.y+', '+b.x+' '+b.y+'" stroke-width="'+l.width+'"><title>'+esc(a.label+' → '+b.label+': '+l.value+' '+projection.value_dimension)+'</title></path>';}).join('');
  const marks=layout.nodes.map(n=>'<g role="button" tabindex="0" aria-label="'+esc(n.type+': '+n.label)+'" data-graph-node="'+esc(n.id)+'" data-entity-type="'+esc(n.type)+'" data-entity-id="'+esc(n.label)+'" transform="translate('+n.x+','+n.y+')"><title>'+esc(n.label)+'</title><rect x="-5" y="-18" width="24" height="36" rx="6"/><text x="25" y="5">'+esc(n.label.length>25?n.label.slice(0,24)+'…':n.label)+'</text></g>').join('');
  return '<p>Destino → Viaje → Recurso · ancho del flujo: '+esc(projection.value_dimension)+'. Las dos capas representan la misma demanda.</p>'
    +'<div class="ultimate-results__chart-scroll" role="region" tabindex="0" aria-label="Flujo de demanda desplazable"><svg class="ultimate-results__sankey" viewBox="0 0 940 '+layout.height+'" role="group" aria-label="Sankey del plan publicado">'+links+marks+'</svg></div>'
    +(!projection.nodes.length?'<p role="status">No hay flujos publicados para dibujar. Consultá la cobertura y las excepciones del resultado.</p>':'')
    +'<details class="ultimate-results__chart-list"><summary>Lista accesible de destinos, viajes y recursos</summary><ul>'+projection.nodes.map(n=>'<li>'+button(n.type,n.label,n.type+' · '+n.label,n.id)+'</li>').join('')+'</ul><table><caption>Flujos certificados · '+esc(projection.value_dimension)+'</caption><thead><tr><th>Desde</th><th>Hasta</th><th>Cantidad</th></tr></thead><tbody>'+projection.links.map(l=>'<tr><td>'+esc(nodes.get(l.source)?.label)+'</td><td>'+esc(nodes.get(l.target)?.label)+'</td><td>'+esc(l.value)+'</td></tr>').join('')+'</tbody></table></details>';
}
export function ganttMarkup(projection){
  const layout=ganttLayout(projection);
  const bars=layout.items.map(i=>{const own=projection.rows.find(r=>r.resource_id===i.resource_id)?.source==='OWN';
    const label=i.trip_id+' · '+i.dispatch_date+' → '+i.arrival_date+(own?' · ocupación hasta '+i.occupancy_end+' (fin exclusivo)':' · sin retorno modelado')+' · '+i.status;
    return '<g role="button" tabindex="0" aria-label="'+esc(label)+'" data-entity-type="TRIP" data-entity-id="'+esc(i.trip_id)+'" transform="translate('+(160+i.x)+','+i.y+')"><title>'+esc(label)+'</title><rect width="'+Math.max(6,i.endX-i.x)+'" height="24" rx="6" class="'+(own?'is-own':'is-external')+'"/><text x="2" y="42">'+esc(i.trip_id)+'</text></g>';}).join('');
  const date=ms=>new Date(ms).toISOString().slice(0,10);
  return '<p>Propio: ocupación certificada con fin exclusivo. Externo: salida → llegada, sin retorno ficticio. Horizonte: '+esc(projection.planning_start)+' → '+esc(projection.planning_end)+'.</p>'
    +'<div class="ultimate-results__chart-scroll" role="region" tabindex="0" aria-label="Programación diaria desplazable"><svg class="ultimate-results__gantt" viewBox="0 0 940 '+layout.height+'" role="group" aria-label="Gantt diario publicado"><text x="160" y="20">'+date(layout.start)+'</text><text x="800" y="20">'+date(layout.end)+'</text>'+layout.rows.map(r=>'<text x="4" y="'+r.y+'"><title>'+esc(r.label)+'</title>'+esc(r.label.slice(0,20))+'</text>').join('')+bars+'</svg></div>'
    +(!projection.items.length?'<p role="status">No hay barras de viajes programados en esta proyección. Los viajes sin fechas se conservan en Schedule.</p>':'')
    +'<details class="ultimate-results__chart-list"><summary>Lista accesible de la programación</summary><ul>'+projection.items.map(i=>'<li>'+button('TRIP',i.trip_id,i.trip_id)+'<span>'+esc(i.resource_id+' · '+i.dispatch_date+' → '+i.arrival_date+' · '+i.status+(i.occupancy_end?' · Disponible nuevamente '+i.occupancy_end:''))+'</span></li>').join('')+'</ul></details>';
}
export function highlightSankey(root,projection,graphNodeId){
  const selected=projection.nodes.find(n=>n.id===graphNodeId);if(!selected)return;
  const connected=new Set([selected.id]);
  const adjacent=projection.links.filter(l=>l.source===selected.id||l.target===selected.id);
  adjacent.forEach(l=>{connected.add(l.source);connected.add(l.target);});
  const trips=new Set(projection.nodes.filter(n=>n.type==='TRIP'&&connected.has(n.id)).map(n=>n.id));
  projection.links.filter(l=>trips.has(l.source)||trips.has(l.target)).forEach(l=>{connected.add(l.source);connected.add(l.target);});
  root.querySelectorAll('[data-graph-node]').forEach(n=>{n.setAttribute('aria-pressed',String(connected.has(n.dataset.graphNode)));n.classList.toggle('is-selected',connected.has(n.dataset.graphNode));});
  root.querySelectorAll('[data-flow-source]').forEach(n=>n.classList.toggle('is-muted',!(connected.has(n.dataset.flowSource)&&connected.has(n.dataset.flowTarget))));
}
