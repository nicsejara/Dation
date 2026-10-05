import {openCaseSelector,openRunHistory} from './traceability-ui.mjs?v=traceability-v3';
import {DECISION_ORDER,DECISION_META} from './decision-ui.mjs?v=traceability-v3';

const KEY='dation.dispatch.workspace.v5';
const OPEN_VIEW_KEY='dation.dispatch.trace.open-view.v3';
const STYLE_ID='decision-trace-v3-styles';
const STYLE_HREF='/static/css/decision-trace-v3.css?v=traceability-v3';
let originalNavigate=null;
let bypassMapRefresh=false;
let decorating=false;
let decorateTimer=null;

function ensureStyles(){
  if(document.getElementById(STYLE_ID))return;
  const link=document.createElement('link');
  link.id=STYLE_ID;
  link.rel='stylesheet';
  link.href=STYLE_HREF;
  document.head.append(link);
}

function savedWorkspace(){
  try{return JSON.parse(sessionStorage.getItem(KEY)||'{}');}catch{return {};}
}

function saveWorkspace(value){
  sessionStorage.setItem(KEY,JSON.stringify(value));
}

async function api(path){
  const response=await fetch(path);
  let data={};
  try{data=await response.json();}catch{}
  if(!response.ok){
    throw new Error(typeof data.detail==='string'?data.detail:'No se pudo completar la solicitud.');
  }
  return data;
}

function caseSnapshot(value){
  if(!value)return null;
  const nodes=value.nodes||{};
  return {
    id:value.id||null,
    updated_at:value.updated_at||null,
    signature:value.signature||null,
    nodes:Object.fromEntries(DECISION_ORDER.map(nodeId=>{
      const node=nodes[nodeId]||{};
      return [nodeId,{
        status:node.status||null,
        run_id:node.run_id||null,
        latest_run_id:node.latest_run_id||null,
        approved_run_id:node.approved_run_id||null,
        run_count:Number(node.run_count||0),
        approved_at:node.approved_at||null,
      }];
    })),
  };
}

function sameCaseState(a,b){
  return JSON.stringify(caseSnapshot(a))===JSON.stringify(caseSnapshot(b));
}

function resetConfig(workspace){
  return {
    ...workspace,
    dimensions:['trips','own_fleet'],
    weights:{trips:50,cost:0,own_fleet:50,co2:0},
    customWeights:null,
    lastPreset:'balanced',
    objective:'balanced',
    analysisDepth:'comparative',
    allow:true,
    resourceMode:'mixed',
    scopeFilters:[],
    decisions:{},
    configured:false,
    schedulingUseDueDates:true,
  };
}

function storeHydratedCase(item,{resetConfiguration=false,activeNode=null}={}){
  const current=savedWorkspace();
  const next=resetConfiguration?resetConfig(current):{...current};
  next.orders=item.orders||null;
  next.fleet=item.fleet||null;
  next.decisionCase=item.decision_case||null;
  next.activeNode=activeNode;
  next.navigationVersion='workspace-nav-v1';
  saveWorkspace(next);
  return next;
}

function reloadInto(view){
  sessionStorage.setItem(OPEN_VIEW_KEY,view);
  location.reload();
}

function navigateDirect(view){
  bypassMapRefresh=true;
  try{
    originalNavigate?.(view);
  }finally{
    bypassMapRefresh=false;
  }
}

export async function listDecisionCases(){
  const payload=await api('/api/decision-cases?status=active&limit=100&offset=0');
  return Array.isArray(payload.cases)?payload.cases:[];
}

async function hydrateCase(caseId){
  return api('/api/decision-cases/'+encodeURIComponent(caseId));
}

async function selectCase(item){
  const current=savedWorkspace();
  const selectedId=item.decision_case?.id||item.case?.id||'';
  const switching=String(current.decisionCase?.id||'')!==String(selectedId);
  if(!switching&&sameCaseState(current.decisionCase,item.decision_case)&&window.DationDispatch?.isReady?.()){
    navigateDirect('logistics-map');
    return;
  }
  storeHydratedCase(item,{resetConfiguration:switching,activeNode:null});
  reloadInto('logistics-map');
}

export async function openDecisionMap(){
  const cases=await listDecisionCases();
  const current=savedWorkspace();
  if(!cases.length){
    if(current.decisionCase?.id&&current.orders&&current.fleet){
      if(window.DationDispatch?.isReady?.())navigateDirect('logistics-map');
      else reloadInto('logistics-map');
    }else{
      navigateDirect('logistics-data');
    }
    return;
  }
  if(cases.length===1){
    await selectCase(cases[0]);
    return;
  }
  openCaseSelector(cases,{
    currentCaseId:current.decisionCase?.id||null,
    onSelect:async caseId=>{
      const selected=cases.find(item=>String(item.case?.id)===String(caseId));
      if(!selected)throw new Error('No se encontró el Decision Case seleccionado.');
      await selectCase(selected);
    },
  });
}

async function refreshCurrentCaseBeforeMap(args){
  const current=savedWorkspace();
  const caseId=current.decisionCase?.id;
  if(!caseId){
    originalNavigate?.(...args);
    return;
  }
  try{
    const fresh=await hydrateCase(caseId);
    if(!sameCaseState(current.decisionCase,fresh.decision_case)){
      storeHydratedCase(fresh,{resetConfiguration:false,activeNode:current.activeNode||null});
      reloadInto('logistics-map');
      return;
    }
  }catch(error){
    if(error?.message&&!/No se encontró/.test(error.message))console.warn(error);
  }
  originalNavigate?.(...args);
}

function wrapNavigation(){
  if(window.dationNavigate?._traceabilityWrapped)return;
  originalNavigate=window.dationNavigate;
  if(typeof originalNavigate!=='function')return;
  const wrapped=function(view,...rest){
    if(view==='logistics-map'&&!bypassMapRefresh){
      refreshCurrentCaseBeforeMap([view,...rest]);
      return;
    }
    return originalNavigate(view,...rest);
  };
  wrapped._traceabilityWrapped=true;
  window.dationNavigate=wrapped;
}

function setConfigNodeAndReload(nodeId){
  const current=savedWorkspace();
  current.activeNode=nodeId;
  current.navigationVersion='workspace-nav-v1';
  saveWorkspace(current);
  reloadInto('logistics-config');
}

function dashboardBanner(runState,nodeId){
  const root=document.getElementById('dispatch-dashboard-root');
  if(!root)return;
  root.querySelector('[data-trace-history-banner]')?.remove();
  const header=root.querySelector('.dispatch-command');
  if(!header)return;
  const status=root.querySelector('[data-case-status]');
  const approve=root.querySelector('[data-approve]');
  const banner=document.createElement('div');
  banner.dataset.traceHistoryBanner='';
  banner.className='dispatch-history-banner'+(runState==='superseded'?' is-superseded':'');
  if(runState==='superseded'){
    banner.innerHTML='<strong>Versión histórica.</strong><span>Esta corrida fue aprobada anteriormente y ya no es la decisión vigente del Case. Podés analizarla o reutilizar su configuración para crear una corrida nueva.</span>';
    if(status){status.textContent='Aprobación anterior';status.classList.add('is-superseded');}
    if(approve)approve.hidden=true;
  }else if(runState==='candidate'){
    banner.innerHTML='<strong>Alternativa sin aprobar.</strong><span>Esta corrida pertenece al mismo Decision Case, pero todavía no reemplaza a la decisión aprobada vigente.</span>';
    if(status){status.textContent='Alternativa';status.classList.add('is-candidate');}
  }else if(runState==='approved'){
    banner.innerHTML='<strong>Decisión vigente.</strong><span>Esta es la corrida aprobada actualmente para '+(DECISION_META[nodeId]?.label||'esta decisión')+'.</span>';
  }else{
    return;
  }
  header.insertAdjacentElement('afterend',banner);
}

async function openRun(runId,nodeId,runState){
  const run=await api('/api/runs/'+encodeURIComponent(runId));
  if(run.status!=='completed'||!run.result_json){
    throw new Error('La corrida todavía no tiene un análisis completo para abrir.');
  }
  window.DationDispatch?.show?.(run);
  window.requestAnimationFrame(()=>dashboardBanner(runState,nodeId));
}

async function showHistory(nodeId){
  const current=savedWorkspace();
  const caseId=current.decisionCase?.id;
  if(!caseId)return;
  const history=await api(
    '/api/decision-cases/'+encodeURIComponent(caseId)+'/runs?node_id='+encodeURIComponent(nodeId)+'&limit=100&offset=0'
  );
  openRunHistory({
    caseId,
    nodeId,
    history,
    onOpenRun:openRun,
  });
}

function traceBar(card,nodeId,history){
  card.querySelector('[data-trace-inline]')?.remove();
  const total=Number(history?.total||0);
  if(!total)return;
  const summary=history.summary||{};
  const latest=history.runs?.[0]||null;
  const hasCandidate=Boolean(
    latest?.decision_state==='candidate'
    &&summary.approved_run_id
    &&String(latest.id)!==String(summary.approved_run_id)
  );
  const bar=document.createElement('div');
  bar.className='dispatch-decision-node__tracebar';
  bar.dataset.traceInline='';
  bar.innerHTML='<div><strong>'+total+' corrida'+(total===1?'':'s')+'</strong>'
    +(hasCandidate?'<span class="is-candidate">Alternativa nueva</span>':'')+'</div>'
    +'<div class="dispatch-decision-node__trace-actions">'
      +(DECISION_META[nodeId]?.implemented&&['approved','stale'].includes(summary.status)
        ?'<button type="button" data-trace-new>+ Nueva corrida</button>':'')
      +'<button type="button" data-trace-history>Historial →</button>'
    +'</div>';
  const actionRow=card.querySelector('.dispatch-decision-node__actionrow');
  actionRow?.insertAdjacentElement('beforebegin',bar);
  bar.querySelector('[data-trace-history]').onclick=()=>showHistory(nodeId);
  const newRun=bar.querySelector('[data-trace-new]');
  if(newRun)newRun.onclick=()=>setConfigNodeAndReload(nodeId);
  if(hasCandidate){
    const line=card.querySelector('.dispatch-decision-node__statusline span');
    if(line)line.textContent='La decisión vigente sigue aprobada. Tenés una alternativa nueva para revisar en el historial.';
  }
}

async function decorateDecisionMap(){
  if(decorating)return;
  const root=document.getElementById('dispatch-map-root');
  const cards=[...root?.querySelectorAll('.dispatch-decision-node')||[]];
  const current=savedWorkspace();
  const caseId=current.decisionCase?.id;
  if(!caseId||cards.length<3)return;
  decorating=true;
  try{
    const histories=await Promise.all(
      DECISION_ORDER.map(nodeId=>api(
        '/api/decision-cases/'+encodeURIComponent(caseId)+'/runs?node_id='+encodeURIComponent(nodeId)+'&limit=100&offset=0'
      ).catch(()=>null))
    );
    DECISION_ORDER.forEach((nodeId,index)=>{
      if(cards[index]&&histories[index])traceBar(cards[index],nodeId,histories[index]);
    });
  }finally{
    decorating=false;
  }
}

function observeDecisionMap(){
  const root=document.getElementById('dispatch-map-root');
  if(!root||root._traceabilityObserver)return;
  const observer=new MutationObserver(()=>{
    clearTimeout(decorateTimer);
    decorateTimer=setTimeout(decorateDecisionMap,40);
  });
  observer.observe(root,{childList:true,subtree:true});
  root._traceabilityObserver=observer;
  decorateDecisionMap();
}

function exposeDispatchExtensions(){
  if(!window.DationDispatch)return false;
  window.DationDispatch.listDecisionCases=listDecisionCases;
  window.DationDispatch.openDecisionMap=openDecisionMap;
  window.DationDispatch.openRunHistory=showHistory;
  window.dispatchEvent(new CustomEvent('dation:cases-ready'));
  return true;
}

function waitForWorkspaceReady(timeoutMs=15000){
  const started=Date.now();
  return new Promise(resolve=>{
    const check=()=>{
      if(window.DationDispatch?.isReady?.()){
        resolve(true);
        return;
      }
      if(Date.now()-started>=timeoutMs){
        resolve(false);
        return;
      }
      window.setTimeout(check,80);
    };
    check();
  });
}

async function restoreRequestedView(){
  const view=sessionStorage.getItem(OPEN_VIEW_KEY);
  if(!view)return;
  sessionStorage.removeItem(OPEN_VIEW_KEY);

  // A full reload resets the global router's in-memory dataReady flag. Opening
  // Carga de datos first remounts the persisted Data Pack and runs preflight;
  // only then can Map/Config navigation pass the existing route guards.
  originalNavigate?.('logistics-data');
  const ready=await waitForWorkspaceReady();
  if(!ready)return;

  if(view==='logistics-map'){
    navigateDirect('logistics-map');
    return;
  }
  originalNavigate?.(view);
}

function boot(){
  ensureStyles();
  const wait=()=>{
    if(!window.DationDispatch||typeof window.dationNavigate!=='function'){
      window.setTimeout(wait,30);
      return;
    }
    wrapNavigation();
    exposeDispatchExtensions();
    observeDecisionMap();
    restoreRequestedView();
  };
  wait();
}

boot();
