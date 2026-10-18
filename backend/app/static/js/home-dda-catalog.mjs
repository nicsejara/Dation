import {esc} from './dispatch/shared.mjs';
import {ddaEnabled} from './platform/entitlements.mjs';

export const DDA_CATEGORIES=Object.freeze([
  {id:'all',label:'Todos'},
  {id:'supply-chain',label:'Supply Chain'},
  {id:'operations',label:'Operaciones'},
  {id:'production',label:'Producción'},
  {id:'commercial',label:'Comercial'},
  {id:'assets',label:'Activos'},
].map(Object.freeze));

export const DDA_CATALOG=Object.freeze([
  {id:'logistics',title:'DDA Logística',status:'available',category:'supply-chain',
    description:'Optimizá cómo asignar, planificar y ejecutar tus despachos.',
    capabilities:['Asignación','Planificación','Ejecución'],icon:'logistics',targetView:'logistics-overview'},
  {id:'production',title:'DDA Producción',status:'coming-soon',category:'production',
    description:'Capacidad, secuenciación y planificación productiva.',
    capabilities:['Capacidad','Secuenciación','Planificación'],icon:'production'},
  {id:'inventory',title:'DDA Inventarios',status:'coming-soon',category:'supply-chain',
    description:'Stock, cobertura y reposición inteligente.',
    capabilities:['Stock','Cobertura','Reposición'],icon:'inventory'},
  {id:'demand',title:'DDA Demanda',status:'coming-soon',category:'commercial',
    description:'Forecast y decisiones de planificación de demanda.',
    capabilities:['Pronóstico','Planificación','Escenarios'],icon:'demand'},
  {id:'procurement',entitlementId:'purchasing',title:'DDA Compras',status:'coming-soon',category:'operations',
    description:'Abastecimiento, evaluación y decisión de compra.',
    capabilities:['Abastecimiento','Evaluación','Decisión'],icon:'procurement'},
  {id:'maintenance',title:'DDA Mantenimiento',status:'coming-soon',category:'assets',
    description:'Priorización de intervenciones y mantenimiento.',
    capabilities:['Intervenciones','Confiabilidad','Disponibilidad'],icon:'maintenance'},
  {id:'pricing',title:'DDA Pricing & Comercial',status:'coming-soon',category:'commercial',
    description:'Pricing, margen y decisiones comerciales.',
    capabilities:['Pricing','Margen','Mix'],icon:'pricing'},
].map(item=>Object.freeze({...item,capabilities:Object.freeze(item.capabilities)})));

const ICONS=Object.freeze({
  inventory:'<path d="m3 7 9-5 9 5v10l-9 5-9-5Z"/><path d="m3 7 9 5 9-5M12 12v10M7.5 4.5l9 5"/>',
  demand:'<path d="M3 3v18h18M7 17v-4M12 17v-7M17 17V6"/><path d="m6 8 5-4 4 2 5-4"/>',
  procurement:'<path d="M2 3h3l3 12h11l3-9H6M9 19h.01M18 19h.01"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/>',
  maintenance:'<path d="M14 6a6 6 0 0 0-7 7l-4 4a3 3 0 0 0 4 4l4-4a6 6 0 0 0 7-7l-4 4-4-4Z"/>',
  pricing:'<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
});
const arrow='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>';
const ASSET_ICONS=Object.freeze({logistics:'/static/assets/dda-logistics.svg'});

export function catalogCounts(catalog=DDA_CATALOG){
  return {available:catalog.filter(item=>item.status==='available').length,
    comingSoon:catalog.filter(item=>item.status==='coming-soon').length};
}

export function filterCatalog(category='all',catalog=DDA_CATALOG){
  return catalog.filter(item=>category==='all'||item.category===category);
}

function assetIcon(item){
  if(item.icon==='production')return '<span class="d-home__production-icon"></span>';
  if(ASSET_ICONS[item.icon]){
    return '<img src="'+ASSET_ICONS[item.icon]+'" alt="">';
  }
  return '<svg viewBox="0 0 24 24" aria-hidden="true">'+ICONS[item.icon]+'</svg>';
}

export function catalogAccess(item,identity){
  if(item.status!=='available')return 'coming_soon';
  return ddaEnabled(identity,item.entitlementId||item.id)?'enabled':'disabled';
}

function assetCard(item,identity){
  const available=item.status==='available';
  const access=catalogAccess(item,identity),enabled=access==='enabled';
  const category=DDA_CATEGORIES.find(category=>category.id===item.category);
  return '<article class="d-home__asset d-home__asset--'+(enabled?'available':'coming-soon')+'"'
    +' data-dda-id="'+esc(item.id)+'" data-dda-status="'+esc(item.status)+'" data-dda-entitlement="'+access+'"'+(enabled?'':' aria-disabled="true"')+'>'
    +'<div class="d-home__asset-top"><span class="d-home__asset-icon" aria-hidden="true">'+assetIcon(item)+'</span>'
      +'<span class="d-home__badge'+(enabled?'':' d-home__badge--muted')+'">'+(enabled?'Disponible':available?'No habilitado':'Próximamente')+'</span></div>'
    +'<div class="d-home__asset-copy"><span class="d-home__asset-category">'+esc(category.label)+'</span>'
      +'<h3>'+esc(item.title)+'</h3><p>'+esc(item.description)+'</p></div>'
    +'<p class="d-home__asset-capabilities">'+item.capabilities.map(esc).join(' · ')+'</p>'
    +'<footer class="d-home__asset-footer">'+(enabled
      ?'<button type="button" id="'+(item.id==='logistics'?'home-open-logistics':'home-open-dda-'+esc(item.id))+'" class="d-home__asset-action"'
        +' data-view-target="'+esc(item.targetView)+'" aria-label="Abrir '+esc(item.title)+'">Abrir '+esc(item.title)+arrow+'</button>'
      :'<span class="d-home__asset-state">'+(available?'No habilitado en este workspace':'En desarrollo')+'</span>')+'</footer></article>';
}

const mounted=new WeakSet();

/** Mount before navigation binds; filtering preserves every card and its listeners. */
export function mountHomeCatalog(root){
  if(!root||mounted.has(root))return;
  const grid=root.querySelector('[data-dda-grid]'),filters=root.querySelector('[data-dda-filters]');
  const counts=root.querySelector('[data-dda-counts]'),feedback=root.querySelector('[data-dda-filter-status]');
  if(!grid||!filters||!counts||!feedback)return;
  // Build first so an unavailable enhancement leaves the fallback usable.
  const filterTemplate=document.createElement('template');
  filterTemplate.innerHTML=DDA_CATEGORIES.map(({id,label})=>
    '<button type="button" class="d-home__filter" data-dda-filter="'+esc(id)+'" aria-pressed="'+(id==='all')+'">'
      +'<span class="d-home__filter-check" aria-hidden="true">✓</span>'+esc(label)+'</button>').join('');
  filters.replaceChildren(filterTemplate.content);
  let selected='all';
  function render(){
    const identity=window.dationSession?.identity,template=document.createElement('template');
    template.innerHTML=DDA_CATALOG.map(item=>assetCard(item,identity)).join('');grid.replaceChildren(template.content);
    const {available,comingSoon}=catalogCounts(),enabled=DDA_CATALOG.filter(item=>catalogAccess(item,identity)==='enabled').length;
    counts.textContent=enabled+' '+(enabled===1?'disponible':'disponibles')+' · '+comingSoon+' '+(comingSoon===1?'próximo':'próximos')+(available>enabled?' · '+(available-enabled)+' no habilitado':'');
    select(selected);
  }
  function select(category){
    selected=category;
    const visible=new Set(filterCatalog(category).map(item=>item.id));
    for(const card of grid.children)card.hidden=!visible.has(card.dataset.ddaId);
    for(const button of filters.querySelectorAll('[data-dda-filter]')){
      button.setAttribute('aria-pressed',String(button.dataset.ddaFilter===category));
    }
    feedback.textContent=DDA_CATEGORIES.find(item=>item.id===category).label+' · '+visible.size+' '+(visible.size===1?'capacidad':'capacidades');
  }
  filters.addEventListener('click',event=>{
    const button=event.target.closest('[data-dda-filter]');
    if(button&&filters.contains(button))select(button.dataset.ddaFilter);
  });
  window.addEventListener('dation:identity',render);
  filters.hidden=false;feedback.hidden=false;render();mounted.add(root);
}
