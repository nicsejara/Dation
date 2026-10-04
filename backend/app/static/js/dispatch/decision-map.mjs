import {api,esc,num} from "./shared.mjs";
import {STATUS,deriveDecisionNodes} from "./decision-case.mjs";
import {createGuideDrawer} from "./upload/guide-drawer.mjs?v=decision-map-case-v2";
import {
  DECISION_ORDER,
  DECISION_META,
  iconSvg,
  statusUi,
} from "./decision-ui.mjs?v=decision-map-case-v2";

const STYLE_ID="decision-map-case-v2-styles";
const STYLE_HREF="/static/css/decision-map-case-v2.css?v=decision-map-case-v2";
let guideDrawer=null;

function ensureDecisionMapStyles(){
  if(document.getElementById(STYLE_ID))return;
  const link=document.createElement("link");
  link.id=STYLE_ID;
  link.rel="stylesheet";
  link.href=STYLE_HREF;
  document.head.append(link);
}

function workflowStep(id,fallback){
  const steps=(window.DationDdaFlow&&Array.isArray(window.DationDdaFlow.steps))
    ?window.DationDdaFlow.steps
    :[];
  return steps.find(step=>step.id===id)||fallback;
}

function readinessById(readiness){
  return Object.fromEntries(
    (readiness?.decisions||[]).map(item=>[item.id,item]),
  );
}

function dateTime(value){
  if(!value)return null;
  const parsed=new Date(value);
  if(Number.isNaN(parsed.getTime()))return null;
  return new Intl.DateTimeFormat("es-AR",{
    day:"2-digit",
    month:"short",
    year:"numeric",
    hour:"2-digit",
    minute:"2-digit",
  }).format(parsed);
}

function compactDateTime(value){
  if(!value)return null;
  const parsed=new Date(value);
  if(Number.isNaN(parsed.getTime()))return null;
  return new Intl.DateTimeFormat("es-AR",{
    day:"2-digit",
    month:"short",
    hour:"2-digit",
    minute:"2-digit",
  }).format(parsed);
}

function displayCaseId(value){
  if(!value)return "—";
  return "DC-"+String(value).slice(0,8).toUpperCase();
}

function middleEllipsis(value,max=34){
  const text=String(value||"—");
  if(text.length<=max)return text;
  const extension=text.toLowerCase().endsWith(".csv")?".csv":"";
  const stem=extension?text.slice(0,-4):text;
  const tailLength=Math.min(12,Math.max(8,Math.floor(max*.32)));
  const headLength=Math.max(10,max-tailLength-extension.length-1);
  return stem.slice(0,headLength)+"…"+stem.slice(-tailLength)+extension;
}

function dependencyState(nodeId,nodes){
  if(nodeId==="logistics_assignment"){
    return {ready:true,label:"Sin dependencia previa",waiting:null};
  }
  const previousId=nodeId==="logistics_scheduling"
    ?"logistics_assignment"
    :"logistics_scheduling";
  const previous=nodes?.[previousId]||{};
  const previousMeta=DECISION_META[previousId];
  const ready=previous.status===STATUS.APPROVED;
  return {
    ready,
    label:ready?previousMeta.short+" aprobada":"Esperando "+previousMeta.short,
    waiting:ready?null:previousMeta.short,
    previousId,
  };
}

function dataIssueText(decision){
  const missing=(decision?.missing||[])
    .map(item=>item.label||item.code)
    .filter(Boolean);
  if(missing.length){
    return missing.slice(0,2).join(" · ")+(missing.length>2?" · +"+(missing.length-2):"");
  }
  const blockers=(decision?.blockers||[])
    .map(item=>item.detail||item.code)
    .filter(Boolean);
  return blockers.length?blockers[0]:null;
}

function actionFor(nodeId,status,node,dataReady){
  const meta=DECISION_META[nodeId];
  if(status===STATUS.APPROVED){
    return node?.run_id
      ?{action:"open-result",label:"Ver resultado",disabled:false}
      :{action:null,label:"Resultado no disponible",disabled:true};
  }
  if(status===STATUS.RUNNING){
    return node?.run_id
      ?{action:"open-result",label:"Ver ejecución →",disabled:false}
      :{action:null,label:"Ejecución en curso",disabled:true};
  }
  if([STATUS.REVIEW,STATUS.STALE].includes(status)){
    return node?.run_id
      ?{action:"open-result",label:"Revisar →",disabled:false}
      :{action:"configure",label:"Revisar configuración →",disabled:false};
  }
  if(!dataReady&&[STATUS.NEEDS_DATA,STATUS.LOCKED].includes(status)){
    return {action:"data",label:"Completar datos →",disabled:false};
  }
  if(status===STATUS.LOCKED){
    return {action:null,label:null,disabled:true};
  }
  if(status===STATUS.ERROR){
    return meta.implemented
      ?{action:"configure",label:"Revisar y reintentar →",disabled:false}
      :{action:null,label:"Motor aún no disponible",disabled:true};
  }
  if(status===STATUS.AVAILABLE){
    return meta.implemented
      ?{action:"configure",label:meta.configureLabel,disabled:false}
      :{action:null,label:"Motor en próxima fase",disabled:true};
  }
  return {action:null,label:null,disabled:true};
}

export function deriveNodePresentationState(nodeId,node,decision,nodes){
  const dependency=dependencyState(nodeId,nodes);
  const dataReady=Boolean(decision?.data_ready);
  const runtimeStatus=[
    STATUS.RUNNING,
    STATUS.REVIEW,
    STATUS.APPROVED,
    STATUS.ERROR,
    STATUS.STALE,
  ].includes(node?.status)?node.status:null;
  const status=runtimeStatus||(
    !dependency.ready
      ?STATUS.LOCKED
      :(dataReady?STATUS.AVAILABLE:STATUS.NEEDS_DATA)
  );
  return {
    nodeId,
    status,
    dataReady,
    dependencyReady:dependency.ready,
    dependencyLabel:dependency.label,
    waitingFor:dependency.waiting,
    previousId:dependency.previousId||null,
    missingData:dataIssueText(decision),
    action:actionFor(nodeId,status,node,dataReady),
    runId:node?.run_id||null,
    approvedAt:compactDateTime(node?.approved_at),
    error:node?.error||null,
  };
}

function statusDetail(presentation){
  if(presentation.status===STATUS.APPROVED){
    return presentation.approvedAt
      ?"Aprobada el "+presentation.approvedAt+"."
      :"Decisión aprobada.";
  }
  if(presentation.status===STATUS.RUNNING){
    return "Dation está procesando esta decisión.";
  }
  if(presentation.status===STATUS.REVIEW){
    return "El resultado está listo para revisar y aprobar.";
  }
  if(presentation.status===STATUS.STALE){
    return "Cambiaron los datos de entrada.";
  }
  if(presentation.status===STATUS.ERROR){
    return presentation.error||"La ejecución necesita revisión antes de continuar.";
  }
  if(!presentation.dataReady){
    return presentation.missingData
      ?"Faltan datos para esta decisión: "+presentation.missingData+"."
      :"Faltan datos para esta decisión.";
  }
  if(presentation.status===STATUS.LOCKED){
    return "Tus datos alcanzan.";
  }
  if(presentation.status===STATUS.AVAILABLE){
    return "Tus datos alcanzan y no hay dependencias.";
  }
  return "Esta decisión está esperando sus condiciones de habilitación.";
}

function stateChip(status){
  const ui=statusUi(status);
  return '<span class="dispatch-map-state-chip is-'+esc(ui.tone)+'" '
    +'title="'+esc(ui.description)+'" tabindex="0">'
    +iconSvg(ui.icon,"dispatch-map-icon")
    +'<span>'+esc(ui.label)+'</span>'
    +'</span>';
}

function nodeActionMarkup(nodeId,presentation){
  const action=presentation.action;
  const approved=presentation.status===STATUS.APPROVED;
  const waiting=presentation.status===STATUS.LOCKED;
  if(approved&&action?.action){
    return '<div class="dispatch-decision-node__actions">'
      +'<button type="button" class="dispatch-map-secondary-action" '
        +'data-map-action="'+esc(action.action)+'" data-map-node="'+esc(nodeId)+'">Ver resultado</button>'
      +'<button type="button" class="dispatch-map-icon-action" '
        +'data-map-action="'+esc(action.action)+'" data-map-node="'+esc(nodeId)+'" '
        +'title="Reabrir análisis" aria-label="Reabrir análisis">'
        +iconSvg("rotate","dispatch-map-icon")
      +'</button>'
    +'</div>';
  }
  if(action?.action){
    return '<button type="button" class="dispatch-decision-node__action" '
      +'data-map-action="'+esc(action.action)+'" data-map-node="'+esc(nodeId)+'">'
      +esc(action.label||"Continuar →")
      +iconSvg("arrowRight","dispatch-map-icon")
    +'</button>';
  }
  if(waiting&&presentation.waitingFor){
    return '<div class="dispatch-decision-node__waiting">'
      +iconSvg("lock","dispatch-map-icon")
      +'<span>Se habilita al aprobar '+esc(presentation.waitingFor)+'.</span>'
    +'</div>';
  }
  if(action?.label){
    return '<div class="dispatch-decision-node__waiting">'
      +iconSvg("clock","dispatch-map-icon")
      +'<span>'+esc(action.label)+'</span>'
    +'</div>';
  }
  return "";
}

function nodeCard(nodeId,presentation,isNext){
  const meta=DECISION_META[nodeId];
  const waiting=presentation.status===STATUS.LOCKED
    ||presentation.status===STATUS.NEEDS_DATA;
  const approved=presentation.status===STATUS.APPROVED;
  const review=[STATUS.REVIEW,STATUS.STALE,STATUS.ERROR].includes(presentation.status);
  const statusId="decision-status-"+nodeId;
  const cardClass="dispatch-decision-node is-"+esc(presentation.status)
    +(isNext?" is-next":"")
    +(approved?" is-approved":"")
    +(review?" is-review":"")
    +(waiting?" is-waiting":"");

  return '<article class="'+cardClass+'" '
    +'aria-label="Decisión '+esc(meta.index)+': '+esc(meta.label)+'" '
    +(isNext?'aria-current="step" ':'')
    +(waiting?'tabindex="0" aria-disabled="true" aria-describedby="'+esc(statusId)+'" ':'')
    +'>'
    +(isNext?'<span class="dispatch-decision-node__next">SIGUIENTE DECISIÓN</span>':'')
    +'<header class="dispatch-decision-node__head">'
      +'<span class="dispatch-decision-node__icon">'
        +iconSvg(approved?"checkCircle":meta.icon,"dispatch-map-icon")
      +'</span>'
      +'<span class="dispatch-decision-node__decision-label">DECISIÓN '+esc(meta.index)+'</span>'
      +stateChip(presentation.status)
    +'</header>'
    +'<h3>'+esc(meta.label)+'</h3>'
    +'<p class="dispatch-decision-node__question">'+esc(meta.question)+'</p>'
    +'<div class="dispatch-decision-node__output">'
      +'<span class="dispatch-decision-node__output-icon">'+iconSvg("clipboardCheck","dispatch-map-icon")+'</span>'
      +'<div><small>QUÉ ENTREGA</small><strong>'+esc(meta.output)+'</strong></div>'
    +'</div>'
    +'<p class="dispatch-decision-node__statusline" id="'+esc(statusId)+'">'
      +iconSvg(
        approved?"checkCircle":review?"alertTriangle":presentation.dataReady?"checkCircle":"alertTriangle",
        "dispatch-map-icon",
      )
      +'<span>'+esc(statusDetail(presentation))+'</span>'
    +'</p>'
    +(presentation.runId
      ?'<small class="dispatch-decision-node__run">Corrida '+esc(String(presentation.runId).slice(0,8))+'</small>'
      :'<small class="dispatch-decision-node__run is-empty" aria-hidden="true">&nbsp;</small>')
    +'<div class="dispatch-decision-node__actionrow">'
      +nodeActionMarkup(nodeId,presentation)
    +'</div>'
  +'</article>';
}

// Legacy visible copy removed from connector UI: "Requiere aprobación".
function connector(fromId,toId,presentations,nextNodeId){
  const source=presentations[fromId];
  const target=presentations[toId];
  const fromMeta=DECISION_META[fromId];
  const sourceApproved=source?.status===STATUS.APPROVED;
  const targetApproved=target?.status===STATUS.APPROVED;
  const active=[STATUS.RUNNING,STATUS.REVIEW,STATUS.STALE].includes(source?.status)
    ||(sourceApproved&&toId===nextNodeId&&target?.status===STATUS.AVAILABLE);
  const tone=sourceApproved?"complete":active?"active":"waiting";
  const icon=sourceApproved?"checkCircle":active?"chevronRight":"lock";
  const label=sourceApproved
    ?fromMeta.short+" aprobada"
    :"Se habilita al aprobar "+fromMeta.short;
  const detail=targetApproved?label:label;
  return '<div class="dispatch-decision-edge is-'+tone+'" '
    +'role="img" aria-label="'+esc(detail)+'" title="'+esc(detail)+'" tabindex="0">'
    +'<span class="dispatch-decision-edge__line" aria-hidden="true"></span>'
    +'<span class="dispatch-decision-edge__marker" aria-hidden="true">'
      +iconSvg(icon,"dispatch-map-icon")
    +'</span>'
  +'</div>';
}

function heroMarkup(){
  const mapStep=workflowStep("map",{number:2,label:"Mapa de decisiones"});
  return '<section class="dispatch-pro-hero dispatch-map-premium__hero" data-reveal>'
    +'<div class="dispatch-pro-hero-copy">'
      +'<span class="dispatch-pro-hero-badge is-step">Paso '+esc(mapStep.number)+': '+esc(mapStep.label)+'</span>'
      +'<h1>Elegí la decisión que tus datos ya pueden resolver.</h1>'
      +'<p class="dispatch-pro-hero-lead">Según los datos que cargaste, Dation te muestra qué decisiones podés resolver ahora y cuáles se habilitan después. Elegí una, configurala y aprobala para desbloquear la siguiente.</p>'
    +'</div>'
    +'<div class="dispatch-pro-hero-visual">'
      +'<img class="dispatch-pro-hero-watermark" src="/static/assets/dda-logistics.svg?v=decision-map-case-v2" alt="">'
      +'<div class="dispatch-pro-how-panel">'
        +'<div class="dispatch-pro-how-title"><span>CÓMO AVANZA EL CASO</span></div>'
        +[
          ["1 · ELEGÍ","La decisión que está disponible.","mousePointer"],
          ["2 · CONFIGURÁ","Definí tu prioridad y compará escenarios.","sliders"],
          ["3 · APROBÁ","El resultado desbloquea la siguiente decisión.","checkCircle"],
        ].map(([label,description,icon],index)=>(
          '<div class="dispatch-pro-how-node">'
            +'<span class="dispatch-pro-how-icon">'+iconSvg(icon,"dispatch-pro-icon dispatch-map-icon")+'</span>'
            +'<div><small>'+esc(label)+'</small><strong>'+esc(description)+'</strong></div>'
          +'</div>'
          +(index<2?'<span class="dispatch-pro-how-connector" aria-hidden="true"></span>':'')
        )).join("")
        +'<div class="dispatch-pro-how-history">'
          +iconSvg("history","dispatch-pro-icon dispatch-map-icon")
          +'<span>Podés reabrir una decisión aprobada desde su tarjeta.</span>'
        +'</div>'
      +'</div>'
    +'</div>'
  +'</section>';
}

function caseState(approved,presentations){
  if(approved===DECISION_ORDER.length){
    return {label:"Completo",tone:"complete",icon:"checkCircle"};
  }
  const needsReview=DECISION_ORDER.some(nodeId=>[
    STATUS.REVIEW,
    STATUS.STALE,
    STATUS.ERROR,
  ].includes(presentations[nodeId]?.status));
  if(needsReview){
    return {label:"Con revisión pendiente",tone:"review",icon:"alertTriangle"};
  }
  return {label:"En curso",tone:"active",icon:"clock"};
}

function caseStatusChip(approved,presentations){
  const item=caseState(approved,presentations);
  return '<span class="dispatch-case-state is-'+item.tone+'">'
    +iconSvg(item.icon,"dispatch-map-icon")
    +'<span>'+esc(item.label)+'</span>'
  +'</span>';
}

function progressMarkup(presentations,approved,activeNodeId){
  return '<div class="dispatch-case-progress">'
    +'<div class="dispatch-case-progress__heading">'
      +'<small>PROGRESO</small><strong>'+num(approved)+' de 3 aprobadas</strong>'
    +'</div>'
    +'<div class="dispatch-case-progress__grid" role="progressbar" aria-valuemin="0" aria-valuemax="3" aria-valuenow="'+approved+'">'
      +DECISION_ORDER.map(nodeId=>{
        const meta=DECISION_META[nodeId];
        const approvedNode=presentations[nodeId].status===STATUS.APPROVED;
        const active=nodeId===activeNodeId&&!approvedNode;
        const tooltip=approvedNode
          ?meta.short+": aprobada"
          :active
            ?meta.short+": decisión actual"
            :meta.short+": en espera";
        return '<div class="dispatch-case-progress__item '+(approvedNode?'is-approved':active?'is-active':'is-waiting')+'" title="'+esc(tooltip)+'">'
          +'<span class="dispatch-case-progress__segment">'
            +(approvedNode?iconSvg("check","dispatch-map-icon"):'')
          +'</span>'
          +'<span class="dispatch-case-progress__label">'+esc(meta.progressLabel)+'</span>'
        +'</div>';
      }).join("")
    +'</div>'
  +'</div>';
}

function datasetHealth(dataset){
  const report=dataset?.profile_json||null;
  const errors=Number(report?.counts?.errors||0);
  return errors>0
    ?{tone:"review",label:"Revisar",icon:"alertTriangle"}
    :{tone:"valid",label:"Validado",icon:"checkCircle"};
}

function dataPackHealth(orders,fleet){
  if(!orders||!fleet){
    return {tone:"waiting",label:"Datos pendientes",icon:"clock"};
  }
  const hasIssues=[orders,fleet].some(dataset=>Number(dataset?.profile_json?.counts?.errors||0)>0);
  return hasIssues
    ?{tone:"review",label:"Revisar datos",icon:"alertTriangle"}
    :{tone:"valid",label:"Datos validados",icon:"checkCircle"};
}

function datasetCard(kind,dataset){
  const isOrders=kind==="orders";
  const label=isOrders?"ÓRDENES":"FLOTA";
  const rows=Number(dataset?.row_count||0);
  const rowLabel=isOrders
    ?num(rows)+" "+(rows===1?"orden":"órdenes")
    :num(rows)+" "+(rows===1?"vehículo":"vehículos");
  const fullName=dataset?.canonical_filename||dataset?.label||dataset?.original_filename||"Archivo sin nombre";
  const shownName=middleEllipsis(fullName);
  const uploaded=compactDateTime(dataset?.created_at);
  const health=datasetHealth(dataset);
  return '<article class="dispatch-datapack-file is-'+kind+'">'
    +'<span class="dispatch-datapack-file__accent" aria-hidden="true"></span>'
    +'<span class="dispatch-datapack-file__icon">'+iconSvg(isOrders?"clipboardList":"truck","dispatch-map-icon")+'</span>'
    +'<div class="dispatch-datapack-file__body">'
      +'<div class="dispatch-datapack-file__topline">'
        +'<small>'+label+'</small>'
        +'<span class="dispatch-file-state is-'+health.tone+'">'+iconSvg(health.icon,"dispatch-map-icon")+esc(health.label)+'</span>'
      +'</div>'
      +'<strong class="dispatch-datapack-file__name" title="'+esc(fullName)+'">'+esc(shownName)+'</strong>'
      +'<div class="dispatch-datapack-file__meta">'
        +'<span class="is-count">'+esc(rowLabel)+'</span>'
        +(uploaded?'<span>Cargado '+esc(uploaded)+'</span>':'')
      +'</div>'
    +'</div>'
    +'<button type="button" class="dispatch-datapack-file__columns" data-map-columns="'+kind+'" '
      +'title="Ver columnas" aria-label="Ver columnas de '+esc(label.toLowerCase())+'">'
      +iconSvg("columns","dispatch-map-icon")
    +'</button>'
  +'</article>';
}

function caseCardMarkup(decisionCase,presentations,orders,fleet,approved,activeNodeId){
  const fullId=String(decisionCase?.id||"");
  const caseId=displayCaseId(fullId);
  const created=dateTime(decisionCase?.created_at);
  const pack=dataPackHealth(orders,fleet);
  return '<section class="dispatch-map-casebar dispatch-case-card" aria-label="Decision Case y Data Pack activo">'
    +'<div class="dispatch-case-card__top">'
      +'<div class="dispatch-case-identity">'
        +'<span class="dispatch-case-identity__icon">'+iconSvg("folderOpen","dispatch-map-icon")+'</span>'
        +'<div class="dispatch-case-identity__copy">'
          +'<small>DECISION CASE</small>'
          +'<div class="dispatch-case-identity__idrow">'
            +'<strong title="'+esc(fullId||caseId)+'">'+esc(caseId)+'</strong>'
            +'<button type="button" data-copy-case-id title="Copiar ID" aria-label="Copiar ID completo del caso">'+iconSvg("copy","dispatch-map-icon")+'</button>'
            +caseStatusChip(approved,presentations)
          +'</div>'
          +(created?'<span class="dispatch-case-identity__created">Creado el '+esc(created)+'</span>':'')
          +'<span class="dispatch-case-identity__trust">Todo lo que decidas queda registrado en este caso.</span>'
          +'<span class="dispatch-case-identity__feedback" data-case-copy-feedback aria-live="polite"></span>'
        +'</div>'
      +'</div>'
      +progressMarkup(presentations,approved,activeNodeId)
    +'</div>'
    +'<div class="dispatch-case-card__divider" aria-hidden="true"></div>'
    +'<div class="dispatch-datapack-panel">'
      +'<div class="dispatch-datapack-panel__head">'
        +'<div class="dispatch-datapack-panel__title">'
          +'<span class="dispatch-datapack-panel__icon">'+iconSvg("database","dispatch-map-icon")+'</span>'
          +'<div><small>DATA PACK ACTIVO</small><span class="dispatch-datapack-panel__support">2 archivos</span></div>'
          +'<span class="dispatch-datapack-status is-'+pack.tone+'">'+iconSvg(pack.icon,"dispatch-map-icon")+esc(pack.label)+'</span>'
        +'</div>'
        +'<button type="button" class="dispatch-map-change-data" data-map-action="data" '
          +(approved>0?'data-confirm-data-change="true" ':'')+'>'
          +iconSvg("refresh","dispatch-map-icon")+'<span>Cambiar datos</span>'
        +'</button>'
      +'</div>'
      +'<div class="dispatch-datapack-grid">'
        +datasetCard("orders",orders)
        +datasetCard("fleet",fleet)
      +'</div>'
    +'</div>'
  +'</section>';
}

function legendMarkup(){
  return '<div class="dispatch-map-legend" aria-label="Estados de las decisiones">'
    +[
      ["Disponible","playCircle","available","Podés configurarla ahora."],
      ["Requiere revisión","alertTriangle","review","Hay un resultado o cambio que requiere revisión."],
      ["Aprobada","checkCircle","approved","La decisión quedó aprobada y registrada."],
      ["En espera","clock","waiting","Se habilita cuando se cumplen sus condiciones."],
    ].map(([label,icon,tone,description])=>(
      '<span class="dispatch-map-state-chip is-'+tone+'" title="'+esc(description)+'" tabindex="0">'
        +iconSvg(icon,"dispatch-map-icon")+'<span>'+label+'</span>'
      +'</span>'
    )).join("")
  +'</div>';
}

function completeBanner(approved,lastRunId){
  if(approved!==3||!lastRunId)return "";
  return '<section class="dispatch-map-complete">'
    +'<span>'+iconSvg("checkCircle","dispatch-map-icon")+'</span>'
    +'<div><small>CASO COMPLETO</small><strong>Las tres decisiones están aprobadas.</strong>'
      +'<p>Podés volver al resultado final o reabrir cualquier decisión desde su tarjeta.</p></div>'
    +'<button type="button" data-map-action="open-result" data-map-node="logistics_final_assignment">Ir al dashboard →</button>'
  +'</section>';
}

function changeDataDialog(presentations){
  const affected=DECISION_ORDER.filter(nodeId=>presentations[nodeId]?.status===STATUS.APPROVED);
  const impact=affected.length
    ?'<div class="dispatch-map-dialog__impact"><strong>Decisiones aprobadas afectadas</strong><ul>'
      +affected.map(nodeId=>'<li>'+esc(DECISION_META[nodeId].label)+'</li>').join("")
      +'</ul></div>'
    :'<div class="dispatch-map-dialog__impact is-empty"><strong>No hay decisiones aprobadas todavía.</strong></div>';
  return '<dialog class="dispatch-map-dialog" data-change-data-dialog>'
    +'<form method="dialog">'
      +'<span class="dispatch-map-dialog__icon">'+iconSvg("refresh","dispatch-map-icon")+'</span>'
      +'<h3>¿Cambiar los datos del caso?</h3>'
      +'<p>Si cambiás los datos, Dation va a crear un nuevo Decision Case y conservará el historial del caso actual.</p>'
      +impact
      +'<div class="dispatch-map-dialog__actions">'
        +'<button value="cancel" class="dispatch-map-secondary-action">Cancelar</button>'
        +'<button value="confirm" class="dispatch-map-primary-action" data-confirm-change>Cambiar datos</button>'
      +'</div>'
    +'</form>'
  +'</dialog>';
}

async function openDatasetColumns(kind,source,orders,fleet){
  try{
    if(!guideDrawer){
      const contracts=await api("/api/dispatch/contracts");
      guideDrawer=createGuideDrawer(contracts);
    }
    guideDrawer.open(kind,source,{
      orders:orders?.profile_json||null,
      fleet:fleet?.profile_json||null,
    });
  }catch(error){
    source.setAttribute("title","No pudimos abrir las columnas");
    source.setAttribute("aria-label","No pudimos abrir las columnas");
  }
}

export function renderDecisionMap(
  root,
  {decisionCase,readiness,orders,fleet,onConfigure,onOpenResult,onData},
){
  ensureDecisionMapStyles();
  const nodes=deriveDecisionNodes(decisionCase,readiness);
  const evidence=readinessById(readiness);
  const presentations=Object.fromEntries(
    DECISION_ORDER.map(nodeId=>[
      nodeId,
      deriveNodePresentationState(nodeId,nodes[nodeId]||{},evidence[nodeId],nodes),
    ]),
  );
  const approved=DECISION_ORDER.filter(
    nodeId=>presentations[nodeId].status===STATUS.APPROVED,
  ).length;
  const nextNodeId=DECISION_ORDER.find(nodeId=>(
    presentations[nodeId].status===STATUS.AVAILABLE&&DECISION_META[nodeId].implemented
  ))||null;
  const attentionNodeId=DECISION_ORDER.find(nodeId=>[
    STATUS.RUNNING,
    STATUS.REVIEW,
    STATUS.STALE,
    STATUS.ERROR,
  ].includes(presentations[nodeId].status))||null;
  const activeNodeId=nextNodeId||attentionNodeId;

  root.className="dispatch dispatch-upload-pro dispatch-decision-map dispatch-decision-map--premium dispatch-decision-map--case-v2";
  root.innerHTML=
    heroMarkup()
    +(decisionCase?.stale_predecessor
      ?'<section class="dispatch-map-stale dispatch-map-stale--premium">'
        +iconSvg("alertTriangle","dispatch-map-icon")
        +'<div><strong>Los datos cambiaron</strong><p>Este es un nuevo Decision Case. El caso anterior se conserva para mantener la trazabilidad.</p></div>'
      +'</section>'
      :'')
    +caseCardMarkup(decisionCase,presentations,orders,fleet,approved,activeNodeId)
    +'<section class="dispatch-map-chain-section dispatch-map-chain-section--open" aria-labelledby="decision-chain-title">'
      +'<header class="dispatch-map-chain-heading">'
        +'<div><span class="dispatch-map-eyebrow">DECISIONES DEL CASO</span>'
          +'<h2 id="decision-chain-title">Tu cadena de decisiones.</h2>'
          +'<p>Cada decisión se aprueba antes de habilitar la siguiente.</p></div>'
        +legendMarkup()
      +'</header>'
      +completeBanner(approved,presentations.logistics_final_assignment.runId)
      +'<div class="dispatch-node-map" aria-label="Cadena de decisiones">'
        +nodeCard("logistics_assignment",presentations.logistics_assignment,nextNodeId==="logistics_assignment")
        +connector("logistics_assignment","logistics_scheduling",presentations,nextNodeId)
        +nodeCard("logistics_scheduling",presentations.logistics_scheduling,nextNodeId==="logistics_scheduling")
        +connector("logistics_scheduling","logistics_final_assignment",presentations,nextNodeId)
        +nodeCard("logistics_final_assignment",presentations.logistics_final_assignment,nextNodeId==="logistics_final_assignment")
      +'</div>'
    +'</section>'
    +changeDataDialog(presentations);

  const fullCaseId=String(decisionCase?.id||"");
  const copyButton=root.querySelector("[data-copy-case-id]");
  const feedback=root.querySelector("[data-case-copy-feedback]");
  if(copyButton){
    copyButton.onclick=async()=>{
      try{
        await navigator.clipboard.writeText(fullCaseId);
        copyButton.classList.add("is-copied");
        copyButton.setAttribute("title","ID copiado");
        if(feedback)feedback.textContent="ID copiado";
        window.setTimeout(()=>{
          copyButton.classList.remove("is-copied");
          copyButton.setAttribute("title","Copiar ID");
          if(feedback)feedback.textContent="";
        },2000);
      }catch{
        if(feedback)feedback.textContent="No se pudo copiar el ID";
      }
    };
  }

  root.querySelectorAll("[data-map-columns]").forEach(button=>{
    button.onclick=()=>openDatasetColumns(button.dataset.mapColumns,button,orders,fleet);
  });

  const changeDialog=root.querySelector("[data-change-data-dialog]");
  const confirmChange=root.querySelector("[data-confirm-change]");
  if(confirmChange){
    confirmChange.onclick=event=>{
      event.preventDefault();
      changeDialog?.close();
      onData?.();
    };
  }

  root.querySelectorAll("[data-map-action]").forEach(button=>{
    button.onclick=()=>{
      const action=button.dataset.mapAction;
      const nodeId=button.dataset.mapNode;
      if(action==="configure"){
        onConfigure?.(nodeId);
        return;
      }
      if(action==="open-result"){
        onOpenResult?.(nodeId);
        return;
      }
      if(action==="data"){
        if(button.dataset.confirmDataChange==="true"){
          if(changeDialog?.showModal){
            changeDialog.showModal();
          }else if(window.confirm(
            "Si cambiás los datos, Dation va a crear un nuevo Decision Case y conservará el historial del actual. ¿Querés continuar?",
          )){
            onData?.();
          }
          return;
        }
        onData?.();
      }
    };
  });
}
