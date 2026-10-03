import {esc,num,date} from "./shared.mjs";
import {STATUS,deriveDecisionNodes} from "./decision-case.mjs";

const ORDER=[
  "logistics_assignment",
  "logistics_scheduling",
  "logistics_final_assignment",
];

const LABELS={
  [STATUS.AVAILABLE]:"Disponible",
  [STATUS.RUNNING]:"Procesando",
  [STATUS.REVIEW]:"En revisión",
  [STATUS.APPROVED]:"Aprobada",
  [STATUS.LOCKED]:"Bloqueada",
  [STATUS.NEEDS_DATA]:"Requiere datos",
  [STATUS.ERROR]:"Error",
  [STATUS.STALE]:"Desactualizada",
};

const COPY={
  logistics_assignment:{
    index:"01",
    title:"Asignación de carga",
    short:"Assignment",
    question:"¿Cómo conviene construir los viajes y distribuir la carga?",
    output:"Viajes propuestos + distribución de carga",
    configureLabel:"Configurar Assignment →",
    implemented:true,
  },
  logistics_scheduling:{
    index:"02",
    title:"Planificación",
    short:"Planificación",
    question:"¿Cuándo conviene ejecutar los viajes ya definidos?",
    output:"Calendario operativo + secuencia",
    configureLabel:"Configurar Planificación →",
    implemented:true,
  },
  logistics_final_assignment:{
    index:"03",
    title:"Asignación final",
    short:"Asignación final",
    question:"¿Qué camión y patente ejecuta cada viaje programado?",
    output:"Asignación física lista para ejecución",
    configureLabel:"Configurar Asignación final →",
    implemented:false,
  },
};

function readinessById(readiness){
  return Object.fromEntries(
    (readiness?.decisions||[]).map(item=>[item.id,item]),
  );
}

function safeDate(value){
  if(!value)return null;
  const raw=String(value).slice(0,10);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(raw))return null;
  try{
    return date(raw);
  }catch{
    return null;
  }
}

function dependencyState(nodeId,nodes){
  if(nodeId==="logistics_assignment"){
    return {
      ready:true,
      label:"Sin dependencia previa",
      waiting:null,
    };
  }

  const previousId=nodeId==="logistics_scheduling"
    ?"logistics_assignment"
    :"logistics_scheduling";
  const previous=nodes?.[previousId]||{};
  const previousMeta=COPY[previousId];
  const ready=previous.status===STATUS.APPROVED;

  return {
    ready,
    label:ready
      ?previousMeta.short+" aprobada"
      :"Esperando "+previousMeta.short,
    waiting:ready?null:previousMeta.short,
  };
}

function dataIssueText(decision){
  const missing=(decision?.missing||[])
    .map(item=>item.label||item.code)
    .filter(Boolean);
  if(missing.length){
    return missing.slice(0,2).join(" · ")
      +(missing.length>2?" · +"+(missing.length-2):"");
  }

  const blockers=(decision?.blockers||[])
    .map(item=>item.detail||item.code)
    .filter(Boolean);
  if(blockers.length){
    return blockers.slice(0,1).join("");
  }

  return null;
}

function actionFor(nodeId,status,node){
  const meta=COPY[nodeId];

  if(
    [STATUS.RUNNING,STATUS.REVIEW,STATUS.APPROVED,STATUS.STALE]
      .includes(status)
  ){
    if(node?.run_id){
      return {
        action:"open-result",
        label:status===STATUS.RUNNING?"Ver ejecución →":"Abrir análisis →",
        disabled:false,
      };
    }
    return {
      action:null,
      label:"Resultado no disponible",
      disabled:true,
    };
  }

  if(status===STATUS.NEEDS_DATA){
    return {
      action:"data",
      label:"Completar datos →",
      disabled:false,
    };
  }

  if(status===STATUS.LOCKED){
    return {
      action:null,
      label:"Bloqueada por jerarquía",
      disabled:true,
    };
  }

  if(status===STATUS.ERROR){
    if(meta.implemented){
      return {
        action:"configure",
        label:"Revisar y reintentar →",
        disabled:false,
      };
    }
    return {
      action:null,
      label:"Motor aún no disponible",
      disabled:true,
    };
  }

  if(status===STATUS.AVAILABLE){
    if(meta.implemented){
      return {
        action:"configure",
        label:meta.configureLabel,
        disabled:false,
      };
    }
    return {
      action:null,
      label:"Motor en próxima fase",
      disabled:true,
    };
  }

  return {
    action:null,
    label:"Sin acción disponible",
    disabled:true,
  };
}

export function deriveNodePresentationState(
  nodeId,
  node,
  decision,
  nodes,
){
  const dependency=dependencyState(nodeId,nodes);
  const dataReady=Boolean(decision?.data_ready);

  const runtimeStatus=[
    STATUS.RUNNING,
    STATUS.REVIEW,
    STATUS.APPROVED,
    STATUS.ERROR,
    STATUS.STALE,
  ].includes(node?.status)
    ?node.status
    :null;

  const status=runtimeStatus
    ||(!dependency.ready
      ?STATUS.LOCKED
      :(dataReady?STATUS.AVAILABLE:STATUS.NEEDS_DATA));

  const capabilities=(decision?.capabilities||[])
    .filter(item=>item.available)
    .map(item=>item.label)
    .filter(Boolean);

  return {
    nodeId,
    status,
    dataReady,
    dependencyReady:dependency.ready,
    dependencyLabel:dependency.label,
    missingData:dataIssueText(decision),
    capabilities,
    action:actionFor(nodeId,status,node),
    runId:node?.run_id||null,
    approvedAt:safeDate(node?.approved_at),
    error:node?.error||null,
  };
}

function nodeCard(nodeId,node,presentation,isNext){
  const meta=COPY[nodeId];
  const caps=presentation.capabilities.slice(0,3);
  const extraCaps=Math.max(0,presentation.capabilities.length-caps.length);
  const action=presentation.action;
  const statusIcon=presentation.status===STATUS.APPROVED
    ?"✓"
    :presentation.status===STATUS.ERROR
      ?"!"
      :presentation.status===STATUS.RUNNING
        ?"↻"
        :"●";

  return (
    '<article class="dispatch-decision-node is-'+esc(presentation.status)
      +(isNext?' is-next':'')
      +(action?.disabled?'':' is-actionable')
      +'" aria-label="Decisión '+esc(meta.index)+': '+esc(meta.title)+'"'
      +(isNext?' aria-current="step"':'')
      +'>'
      +'<header class="dispatch-decision-node__head">'
        +'<span class="dispatch-decision-node__index">'+esc(meta.index)+'</span>'
        +'<span class="dispatch-decision-node__state is-'+esc(presentation.status)+'">'
          +'<i aria-hidden="true">'+esc(statusIcon)+'</i>'
          +esc(LABELS[presentation.status]||presentation.status)
        +'</span>'
      +'</header>'
      +(isNext?'<span class="dispatch-decision-node__next">SIGUIENTE DECISIÓN</span>':'')
      +'<h2>'+esc(meta.title)+'</h2>'
      +'<p class="dispatch-decision-node__question">'+esc(meta.question)+'</p>'
      +'<div class="dispatch-decision-node__output">'
        +'<small>SALIDA</small>'
        +'<strong>'+esc(meta.output)+'</strong>'
      +'</div>'
      +'<div class="dispatch-decision-node__readiness" aria-label="Condiciones de la decisión">'
        +'<div class="'+(presentation.dataReady?'is-ready':'is-pending')+'">'
          +'<span aria-hidden="true">'+(presentation.dataReady?'✓':'○')+'</span>'
          +'<div><small>Datos</small><strong>'
            +(presentation.dataReady?'Suficientes':'Incompletos')
          +'</strong>'
          +(!presentation.dataReady&&presentation.missingData
            ?'<em>'+esc(presentation.missingData)+'</em>'
            :'')
          +'</div>'
        +'</div>'
        +'<div class="'+(presentation.dependencyReady?'is-ready':'is-pending')+'">'
          +'<span aria-hidden="true">'+(presentation.dependencyReady?'✓':'○')+'</span>'
          +'<div><small>Dependencia</small><strong>'
            +esc(presentation.dependencyLabel)
          +'</strong></div>'
        +'</div>'
      +'</div>'
      +(caps.length
        ?'<div class="dispatch-decision-node__capabilities">'
          +caps.map(value=>'<span>✓ '+esc(value)+'</span>').join("")
          +(extraCaps?'<span>+'+num(extraCaps)+' capacidades</span>':'')
        +'</div>'
        :'')
      +'<div class="dispatch-decision-node__meta">'
        +(presentation.runId
          ?'<small>Corrida '+esc(String(presentation.runId).slice(0,8))+'…</small>'
          :'')
        +(presentation.approvedAt
          ?'<small>Aprobada '+esc(presentation.approvedAt)+'</small>'
          :'')
      +'</div>'
      +(presentation.error
        ?'<p class="dispatch-decision-node__error">'+esc(presentation.error)+'</p>'
        :'')
      +'<button type="button" class="dispatch-decision-node__action"'
        +(action?.action?' data-map-action="'+esc(action.action)+'"':'')
        +' data-map-node="'+esc(nodeId)+'"'
        +(action?.disabled?' disabled aria-disabled="true"':'')
        +'>'
        +esc(action?.label||"Sin acción disponible")
      +'</button>'
    +'</article>'
  );
}

function connector(fromId,toId,presentations){
  const source=presentations[fromId];
  const target=presentations[toId];
  const complete=source?.status===STATUS.APPROVED;
  const active=complete&&target?.status===STATUS.AVAILABLE;

  return (
    '<div class="dispatch-decision-edge'
      +(complete?' is-complete':' is-pending')
      +(active?' is-active':'')
      +'" aria-label="Dependencia entre decisiones">'
      +'<span class="dispatch-decision-edge__label">'
        +(complete?'Output aprobado':'Requiere aprobación')
      +'</span>'
      +'<span class="dispatch-decision-edge__line" aria-hidden="true"></span>'
    +'</div>'
  );
}

export function renderDecisionMap(
  root,
  {
    decisionCase,
    readiness,
    orders,
    fleet,
    onConfigure,
    onOpenResult,
    onData,
  },
){
  const nodes=deriveDecisionNodes(decisionCase,readiness);
  const evidence=readinessById(readiness);
  const presentations=Object.fromEntries(
    ORDER.map(nodeId=>[
      nodeId,
      deriveNodePresentationState(
        nodeId,
        nodes[nodeId]||{},
        evidence[nodeId],
        nodes,
      ),
    ]),
  );

  const approved=ORDER.filter(
    nodeId=>presentations[nodeId].status===STATUS.APPROVED,
  ).length;
  const nextNodeId=ORDER.find(
    nodeId=>presentations[nodeId].status===STATUS.AVAILABLE,
  )||null;

  root.className="dispatch dispatch-decision-map dispatch-decision-map--nodal";
  root.innerHTML=
    '<header class="dispatch-map-hero dispatch-map-hero--nodal">'
      +'<div>'
        +'<span class="dispatch-kicker">DECISION CASE</span>'
        +'<h1>Mapa de decisiones</h1>'
        +'<p>Cada decisión transforma evidencia en un nuevo nivel de ejecución. Revisá resultados anteriores y avanzá cuando se cumplan datos y dependencias.</p>'
      +'</div>'
      +'<div class="dispatch-map-case">'
        +'<small>Caso</small>'
        +'<strong>'+esc(String(decisionCase?.id||"—").slice(0,8))+'…</strong>'
        +'<span>'+num(approved)+' de 3 aprobadas</span>'
      +'</div>'
    +'</header>'
    +(decisionCase?.stale_predecessor
      ?'<section class="dispatch-map-stale">'
        +'<span aria-hidden="true">↻</span>'
        +'<div><strong>Los datos cambiaron</strong>'
        +'<p>Esta cadena usa las versiones actuales de Orders y Fleet. Los resultados anteriores se conservan como historial.</p></div>'
      +'</section>'
      :'')
    +'<section class="dispatch-map-datapack" aria-label="Data Pack activo">'
      +'<div class="dispatch-map-datapack__title">'
        +'<span class="dispatch-kicker">DATA PACK ACTIVO</span>'
        +'<strong>Evidencia del caso</strong>'
      +'</div>'
      +'<div class="dispatch-map-datapack__file">'
        +'<small>Orders</small>'
        +'<strong>'+esc(orders?.original_filename||"—")+'</strong>'
        +'<span>'+num(orders?.row_count||0)+' registros</span>'
      +'</div>'
      +'<div class="dispatch-map-datapack__file">'
        +'<small>Fleet</small>'
        +'<strong>'+esc(fleet?.label||fleet?.original_filename||"—")+'</strong>'
        +'<span>'+num(fleet?.row_count||0)+' vehículos</span>'
      +'</div>'
      +'<button type="button" data-map-action="data" class="dispatch-map-datapack__action">Cambiar datos</button>'
    +'</section>'
    +'<section class="dispatch-node-map" aria-label="Cadena nodal de decisiones">'
      +nodeCard(
        "logistics_assignment",
        nodes.logistics_assignment||{},
        presentations.logistics_assignment,
        nextNodeId==="logistics_assignment",
      )
      +connector(
        "logistics_assignment",
        "logistics_scheduling",
        presentations,
      )
      +nodeCard(
        "logistics_scheduling",
        nodes.logistics_scheduling||{},
        presentations.logistics_scheduling,
        nextNodeId==="logistics_scheduling",
      )
      +connector(
        "logistics_scheduling",
        "logistics_final_assignment",
        presentations,
      )
      +nodeCard(
        "logistics_final_assignment",
        nodes.logistics_final_assignment||{},
        presentations.logistics_final_assignment,
        nextNodeId==="logistics_final_assignment",
      )
    +'</section>'
    +'<p class="dispatch-node-map-note">'
      +'<strong>Cómo avanza el caso:</strong> una aprobación convierte el resultado de un nodo en evidencia de entrada para el siguiente. Las decisiones con resultado pueden abrirse nuevamente desde su propio nodo.'
    +'</p>';

  root.querySelectorAll("[data-map-action]").forEach(button=>{
    button.onclick=()=>{
      if(button.disabled)return;
      const action=button.dataset.mapAction;
      const nodeId=button.dataset.mapNode;
      if(action==="configure")onConfigure?.(nodeId);
      if(action==="open-result")onOpenResult?.(nodeId);
      if(action==="data")onData?.();
    };
  });
}
