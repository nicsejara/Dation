/** T10 replaces only the T5 result placeholder; graph stays server-owned. */
import {api,post,esc,errorBox} from '../shared.mjs';
import {scopeFor} from '../lifecycle.mjs';
import {graphTarget,graphStateUi} from '../navigation/ultimate-graph.mjs';
import {render as dashboard} from '../dashboard.mjs';

export async function mountUltimateResult(root,{route,navigate,onContext}){
  const scope=scopeFor(root),base='/api/platform/logistics-cases/'+encodeURIComponent(route.caseId);
  root.className='dispatch';delete root.dataset.runId;delete root.dataset.resultFingerprint;delete root.dataset.graphHistoricalRun;delete root.dataset.graphReady;
  root.innerHTML='<section class="dispatch-panel" role="status">Recuperando la corrida publicada…</section>';
  let renderedScope=null;
  async function graph(){const own=renderedScope||scope;const data=await api(base+'/graph?'+new URLSearchParams({run_id:route.runId,node_id:route.nodeId}),{signal:own.signal});if(!own.active)throw new DOMException('Route changed','AbortError');return data;}
  const follow=target=>{const t=graphTarget(target);if(!t)throw new Error('Destino no disponible');return navigate(t.view,t);};
  try{
    const data=await graph();if(!scope.active)return;
    if(data.selected_run?.id!==route.runId||data.selected_run.node_id!==route.nodeId)throw new Error('La corrida no pertenece a este Case y decisión.');
    onContext?.(data.case,data.graph);
    const run=await api('/api/runs/'+encodeURIComponent(route.runId),{signal:scope.signal});if(!scope.active)return;
    if(run.decision_case_id!==route.caseId||run.node_id!==route.nodeId)throw new Error('RESULT_CONTEXT_MISMATCH');
    const refresh=()=>navigate('decision-dashboard',{...route,replace:true});
    if(run.status!=='completed'||!run.result_json){
      root.className='dispatch';root.dataset.graphHistoricalRun=run.id;root.dataset.graphReady='true';
      root.innerHTML='<section class="dispatch-panel" data-result-pending><h1>Corrida '+esc(run.id)+'</h1><p role="status">'+esc(run.status)+'</p><p>'+esc(run.error_message||'El resultado publicado todavía no está disponible.')+'</p>'
        +(run.upstream_run_id?'<p>Transport Plan fuente: '+esc(run.upstream_run_id)+'</p>':'')+'<button type="button" class="d-button d-button--secondary" data-refresh-result>Actualizar</button> <button type="button" class="d-button d-button--secondary" data-result-map>Mapa de decisiones</button></section>';
      scope.listen(root.querySelector('[data-refresh-result]'),'click',refresh);scope.listen(root.querySelector('[data-result-map]'),'click',()=>follow(data.graph.resume));
      let attempts=0;
      async function poll(){try{const current=await api('/api/runs/'+encodeURIComponent(run.id),{signal:scope.signal});if(!scope.active)return;
        if(current.status!==run.status||current.result_json)return refresh();
        if(++attempts<60)scope.timeout(poll,2000);
      }catch(error){if(scope.active)root.querySelector('[role=status]').textContent='No se pudo actualizar. Reintentá con Actualizar.';}}
      if(['queued','running'].includes(run.status))scope.timeout(poll,2000);
      return;
    }
    const railMarkup='<nav class="dispatch-decision-rail" aria-label="Decisiones del Case">'+data.graph.nodes.map((node,index)=>{
      const ui=graphStateUi(node.node_state),action=node.primary_action;
      return '<button type="button" class="dispatch-decision-tab'+(node.id===route.nodeId?' is-active':'')+'" data-decision-node="'+esc(node.id)+'" '+(node.id===route.nodeId?'aria-current="page" ':'')+(!action?.allowed?'disabled':'')+'><span>'+(index+1)+'</span><div><strong>'+esc(node.label)+'</strong><small>'+esc(ui.label)+'</small></div></button>';
    }).join('')+'</nav>';
    const pending=dashboard(root,run,async()=>{
      const current=await graph(),node=current.graph.nodes.find(n=>n.id===route.nodeId);
      if(!node?.actions.new_run.allowed)throw new Error('No se puede configurar una nueva corrida en el contexto actual.');
      return follow(node.actions.new_run.target);
    },{railMarkup,status:run.superseded_at?'superseded':run.approved_at?'approved':'review',activeNode:route.nodeId,
      onOpenNode:async id=>{const current=await graph(),node=current.graph.nodes.find(n=>n.id===id);if(node?.primary_action?.allowed)return follow(node.primary_action.target);},
      onRefresh:refresh,onApprove:()=>post('/api/runs/'+encodeURIComponent(run.id)+'/approve',{case_id:route.caseId,node_id:route.nodeId,expected_result_fingerprint:run.result_fingerprint}),
      onApprovalComplete:refresh,
      getContinuation:async()=>run.approved_at?{target:graphTarget(data.graph.resume),label:'Mapa de decisiones',state:'available'}:null,
      onContinue:async()=>follow((await graph()).graph.resume),
    });
    renderedScope=scopeFor(root);await pending;
    if(renderedScope.active){root.dataset.graphHistoricalRun=run.id;root.dataset.graphReady='true';}
  }catch(error){if((renderedScope||scope).active)errorBox(root,error,()=>navigate('decision-dashboard',{...route,replace:true}));}
}
