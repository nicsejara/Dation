import {esc,num} from "./shared.mjs";
import {STATUS,deriveDecisionNodes} from "./decision-case.mjs";
import {
  DECISION_ORDER,
  DECISION_META,
  iconSvg,
  statusUi,
} from "./decision-ui.mjs?v=decision-map-premium-v1";

function workflowStep(id, fallback) {
  const steps = (
    window.DationDdaFlow
    && Array.isArray(window.DationDdaFlow.steps)
  )
    ? window.DationDdaFlow.steps
    : [];
  return steps.find((step) => step.id === id) || fallback;
}

function readinessById(readiness){
  return Object.fromEntries(
    (readiness?.decisions||[]).map(item=>[item.id,item]),
  );
}

function approvedDateTime(value){
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
  const previousMeta=DECISION_META[previousId];
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
    return {
      action:"data",
      label:"Completar datos →",
      disabled:false,
    };
  }

  if(status===STATUS.LOCKED){
    return {
      action:null,
      label:null,
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
    label:null,
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

  return {
    nodeId,
    status,
    dataReady,
    dependencyReady:dependency.ready,
    dependencyLabel:dependency.label,
    waitingFor:dependency.waiting,
    missingData:dataIssueText(decision),
    action:actionFor(nodeId,status,node,dataReady),
    runId:node?.run_id||null,
    approvedAt:approvedDateTime(node?.approved_at),
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
    return "Cambiaron los datos de entrada. Revisá antes de continuar.";
  }

  if(presentation.status===STATUS.ERROR){
    return presentation.error||"La ejecución necesita revisión antes de continuar.";
  }

  if(!presentation.dataReady){
    return presentation.missingData
      ?"Faltan datos para esta decisión: "+presentation.missingData+"."
      :"Faltan datos para esta decisión.";
  }

  if(presentation.status===STATUS.LOCKED&&presentation.waitingFor){
    return "Tus datos alcanzan. Se habilita al aprobar "+presentation.waitingFor+".";
  }

  if(presentation.status===STATUS.AVAILABLE){
    return "Tus datos alcanzan y no hay dependencias.";
  }

  return "Esta decisión se habilitará cuando estén listas sus condiciones.";
}

function stateChip(status){
  const ui=statusUi(status);
  return '<span class="dispatch-map-state-chip is-'+esc(ui.tone)+'">'
    +iconSvg(ui.icon,"dispatch-map-icon")
    +'<span>'+esc(ui.label)+'</span>'
    +'</span>';
}

function nodeCard(nodeId,presentation,isNext){
  const meta=DECISION_META[nodeId];
  const action=presentation.action;
  const statusId="decision-status-"+nodeId;
  const waiting=presentation.status===STATUS.LOCKED
    ||presentation.status===STATUS.NEEDS_DATA;
  const approved=presentation.status===STATUS.APPROVED;
  const review=[STATUS.REVIEW,STATUS.STALE,STATUS.ERROR].includes(
    presentation.status,
  );

  let actionMarkup="";
  if(approved&&action?.action){
    actionMarkup=
      '<div class="dispatch-decision-node__actions">'
        +'<button type="button" class="dispatch-map-secondary-action" '
          +'data-map-action="'+esc(action.action)+'" '
          +'data-map-node="'+esc(nodeId)+'">Ver resultado</button>'
        +'<button type="button" class="dispatch-map-icon-action" '
          +'data-map-action="'+esc(action.action)+'" '
          +'data-map-node="'+esc(nodeId)+'" '
          +'title="Reabrir análisis" aria-label="Reabrir análisis">'
          +iconSvg("rotate","dispatch-map-icon")
        +'</button>'
      +'</div>';
  }else if(action?.action){
    actionMarkup=
      '<button type="button" class="dispatch-decision-node__action" '
        +'data-map-action="'+esc(action.action)+'" '
        +'data-map-node="'+esc(nodeId)+'">'
        +esc(action.label||"Continuar →")
      +'</button>';
  }else if(waiting){
    actionMarkup=
      '<div class="dispatch-decision-node__waiting">'
        +iconSvg(presentation.dataReady?"lock":"alertTriangle","dispatch-map-icon")
        +'<span>'+esc(
          presentation.dataReady&&presentation.waitingFor
            ?"Se habilita al aprobar "+presentation.waitingFor
            :"Completá los datos para habilitar esta decisión",
        )+'</span>'
      +'</div>';
  }else if(action?.label){
    actionMarkup=
      '<div class="dispatch-decision-node__waiting">'
        +iconSvg("clock","dispatch-map-icon")
        +'<span>'+esc(action.label)+'</span>'
      +'</div>';
  }

  return (
    '<article class="dispatch-decision-node is-'+esc(presentation.status)
      +(isNext?' is-next':'')
      +(approved?' is-approved':'')
      +(review?' is-review':'')
      +(waiting?' is-waiting':'')
      +'" aria-label="Decisión '+esc(meta.index)+': '+esc(meta.label)+'"'
      +(isNext?' aria-current="step"':'')
      +(waiting
        ?' tabindex="0" aria-disabled="true" aria-describedby="'+esc(statusId)+'"'
        :'')
      +'>'
      +'<header class="dispatch-decision-node__head">'
        +'<span class="dispatch-decision-node__icon">'
          +iconSvg(
            approved?"checkCircle":meta.icon,
            "dispatch-map-icon",
          )
        +'</span>'
        +'<span class="dispatch-decision-node__index">'+esc(meta.index)+'</span>'
        +stateChip(presentation.status)
      +'</header>'
      +(isNext?'<span class="dispatch-decision-node__next">SIGUIENTE DECISIÓN</span>':'')
      +'<h3>'+esc(meta.label)+'</h3>'
      +'<p class="dispatch-decision-node__question">'+esc(meta.question)+'</p>'
      +'<div class="dispatch-decision-node__output">'
        +'<span class="dispatch-decision-node__output-icon">'
          +iconSvg("clipboardCheck","dispatch-map-icon")
        +'</span>'
        +'<div><small>QUÉ ENTREGA</small>'
        +'<strong>'+esc(meta.output)+'</strong></div>'
      +'</div>'
      +'<p class="dispatch-decision-node__statusline" id="'+esc(statusId)+'">'
        +iconSvg(
          approved
            ?"checkCircle"
            :review
              ?"alertTriangle"
              :waiting
                ?"lock"
                :"checkCircle",
          "dispatch-map-icon",
        )
        +'<span>'+esc(statusDetail(presentation))+'</span>'
      +'</p>'
      +(presentation.runId
        ?'<small class="dispatch-decision-node__run">Corrida '
          +esc(String(presentation.runId).slice(0,8))+'</small>'
        :'')
      +'<div class="dispatch-decision-node__actionrow">'
        +actionMarkup
      +'</div>'
    +'</article>'
  );
}

function connector(fromId,toId,presentations,nextNodeId){
  const source=presentations[fromId];
  const complete=source?.status===STATUS.APPROVED;
  const active=complete&&toId===nextNodeId;
  const tone=active?"active":complete?"complete":"waiting";
  const icon=complete?"checkCircle":active?"playCircle":"lock";

  return (
    '<div class="dispatch-decision-edge is-'+tone
      +'" aria-label="'+(complete?"Aprobada":"Requiere aprobación")+'">'
      +'<span class="dispatch-decision-edge__line" aria-hidden="true"></span>'
      +'<span class="dispatch-decision-edge__marker" aria-hidden="true">'
        +iconSvg(icon,"dispatch-map-icon")
      +'</span>'
      +'<span class="dispatch-decision-edge__label">'
        +(complete?"Aprobada":"Requiere aprobación")
      +'</span>'
    +'</div>'
  );
}

function heroMarkup(){
  const mapStep=workflowStep(
    "map",
    {number:2,label:"Mapa de decisiones"},
  );

  return (
    '<section class="dispatch-pro-hero dispatch-map-premium__hero" data-reveal>'
      +'<div class="dispatch-pro-hero-copy">'
        +'<span class="dispatch-pro-hero-badge is-step">'
          +'Paso '+esc(mapStep.number)+': '+esc(mapStep.label)
        +'</span>'
        +'<h1>Elegí la decisión que tus datos ya pueden resolver.</h1>'
        +'<p class="dispatch-pro-hero-lead">'
          +'Según los datos que cargaste, Dation te muestra qué decisiones podés resolver ahora y cuáles se habilitan después. '
          +'Elegí una, configurala y aprobala para desbloquear la siguiente.'
        +'</p>'
      +'</div>'
      +'<div class="dispatch-pro-hero-visual">'
        +'<img class="dispatch-pro-hero-watermark" src="/static/assets/dda-logistics.svg?v=decision-map-premium-v1" alt="">'
        +'<div class="dispatch-pro-how-panel">'
          +'<div class="dispatch-pro-how-title"><span>CÓMO AVANZA EL CASO</span></div>'
          +[
            ["1 · ELEGÍ","La decisión que está disponible.","mousePointer"],
            ["2 · CONFIGURÁ","Definí tu prioridad y compará escenarios.","sliders"],
            ["3 · APROBÁ","El resultado desbloquea la siguiente decisión.","checkCircle"],
          ].map(([label,description,icon],index)=>(
            '<div class="dispatch-pro-how-node">'
              +'<span class="dispatch-pro-how-icon">'
                +iconSvg(icon,"dispatch-pro-icon dispatch-map-icon")
              +'</span>'
              +'<div><small>'+esc(label)+'</small>'
              +'<strong>'+esc(description)+'</strong></div>'
            +'</div>'
            +(index<2?'<span class="dispatch-pro-how-connector" aria-hidden="true"></span>':'')
          )).join("")
          +'<div class="dispatch-pro-how-history">'
            +iconSvg("rotate","dispatch-pro-icon dispatch-map-icon")
            +'<span>Podés reabrir una decisión aprobada desde su tarjeta.</span>'
          +'</div>'
        +'</div>'
      +'</div>'
    +'</section>'
  );
}

function caseBarMarkup(decisionCase,presentations,orders,fleet,approved){
  const fullId=String(decisionCase?.id||"—");
  const shortId=fullId==="—"?"—":fullId.slice(0,8);
  const ordersName=orders?.canonical_filename
    ||orders?.label
    ||orders?.original_filename
    ||"—";
  const fleetName=fleet?.canonical_filename
    ||fleet?.label
    ||fleet?.original_filename
    ||"—";

  return (
    '<section class="dispatch-map-casebar" aria-label="Resumen del Decision Case">'
      +'<div class="dispatch-map-casebar__case">'
        +'<span class="dispatch-map-casebar__icon">'
          +iconSvg("folderOpen","dispatch-map-icon")
        +'</span>'
        +'<div><small>TU DECISION CASE</small>'
          +'<div class="dispatch-map-casebar__id">'
            +'<strong title="'+esc(fullId)+'">'+esc(shortId)+'</strong>'
            +'<button type="button" data-copy-case-id title="Copiar ID" aria-label="Copiar ID del caso">'
              +iconSvg("copy","dispatch-map-icon")
            +'</button>'
          +'</div>'
        +'</div>'
      +'</div>'
      +'<div class="dispatch-map-casebar__progress">'
        +'<div class="dispatch-map-casebar__progress-copy">'
          +'<small>PROGRESO</small><strong>'+num(approved)+' de 3 aprobadas</strong>'
        +'</div>'
        +'<div class="dispatch-map-casebar__segments" role="progressbar" '
          +'aria-valuemin="0" aria-valuemax="3" aria-valuenow="'+approved+'">'
          +DECISION_ORDER.map(nodeId=>(
            '<span class="'+(
              presentations[nodeId].status===STATUS.APPROVED
                ?"is-approved"
                :""
            )+'"></span>'
          )).join("")
        +'</div>'
      +'</div>'
      +'<div class="dispatch-map-casebar__pack">'
        +'<div class="dispatch-map-casebar__packhead">'
          +'<small>DATA PACK ACTIVO</small>'
          +'<span class="dispatch-map-validated">'
            +iconSvg("checkCircle","dispatch-map-icon")
            +'Datos validados'
          +'</span>'
        +'</div>'
        +'<div class="dispatch-map-casebar__files">'
          +'<div class="dispatch-map-casebar__file is-orders">'
            +'<span>'+iconSvg("clipboardList","dispatch-map-icon")+'</span>'
            +'<div><small>Órdenes</small><strong>'+esc(ordersName)+'</strong></div>'
            +'<em>'+num(orders?.row_count||0)+' órdenes</em>'
          +'</div>'
          +'<div class="dispatch-map-casebar__file is-fleet">'
            +'<span>'+iconSvg("truck","dispatch-map-icon")+'</span>'
            +'<div><small>Flota</small><strong>'+esc(fleetName)+'</strong></div>'
            +'<em>'+num(fleet?.row_count||0)+' vehículos</em>'
          +'</div>'
        +'</div>'
      +'</div>'
      +'<button type="button" class="dispatch-map-change-data" data-map-action="data"'
        +(approved>0?' data-confirm-data-change="true"':'')
        +'>'
        +iconSvg("refresh","dispatch-map-icon")
        +'<span>Cambiar datos</span>'
      +'</button>'
    +'</section>'
  );
}

function legendMarkup(){
  return (
    '<div class="dispatch-map-legend" aria-label="Estados de las decisiones">'
      +[
        ["Disponible","playCircle","available"],
        ["Requiere revisión","alertTriangle","review"],
        ["Aprobada","checkCircle","approved"],
        ["En espera","clock","waiting"],
      ].map(([label,icon,tone])=>(
        '<span class="dispatch-map-state-chip is-'+tone+'">'
          +iconSvg(icon,"dispatch-map-icon")
          +'<span>'+label+'</span>'
        +'</span>'
      )).join("")
    +'</div>'
  );
}

function completeBanner(lastRunId){
  if(!lastRunId)return "";
  return (
    '<section class="dispatch-map-complete">'
      +'<span>'+iconSvg("checkCircle","dispatch-map-icon")+'</span>'
      +'<div><small>CASO COMPLETO</small>'
        +'<strong>Las tres decisiones están aprobadas.</strong>'
        +'<p>Podés volver al resultado final o reabrir cualquier decisión desde su tarjeta.</p>'
      +'</div>'
      +'<button type="button" data-map-action="open-result" '
        +'data-map-node="logistics_final_assignment">Ir al dashboard →</button>'
    +'</section>'
  );
}

function changeDataDialog(){
  return (
    '<dialog class="dispatch-map-dialog" data-change-data-dialog>'
      +'<form method="dialog">'
        +'<span class="dispatch-map-dialog__icon">'
          +iconSvg("refresh","dispatch-map-icon")
        +'</span>'
        +'<h3>¿Cambiar los datos del caso?</h3>'
        +'<p>Si cambiás los datos, Dation va a crear un nuevo Decision Case y conservará el historial del caso actual.</p>'
        +'<div class="dispatch-map-dialog__actions">'
          +'<button value="cancel" class="dispatch-map-secondary-action">Cancelar</button>'
          +'<button value="confirm" class="dispatch-map-primary-action" data-confirm-change> Cambiar datos </button>'
        +'</div>'
      +'</form>'
    +'</dialog>'
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
    DECISION_ORDER.map(nodeId=>[
      nodeId,
      deriveNodePresentationState(
        nodeId,
        nodes[nodeId]||{},
        evidence[nodeId],
        nodes,
      ),
    ]),
  );

  const approved=DECISION_ORDER.filter(
    nodeId=>presentations[nodeId].status===STATUS.APPROVED,
  ).length;
  const nextNodeId=DECISION_ORDER.find(nodeId=>(
    presentations[nodeId].status===STATUS.AVAILABLE
    &&DECISION_META[nodeId].implemented
  ))||null;

  root.className=(
    "dispatch dispatch-upload-pro dispatch-decision-map "
    +"dispatch-decision-map--premium"
  );
  root.innerHTML=
    heroMarkup()
    +(decisionCase?.stale_predecessor
      ?'<section class="dispatch-map-stale dispatch-map-stale--premium">'
        +iconSvg("alertTriangle","dispatch-map-icon")
        +'<div><strong>Los datos cambiaron</strong>'
        +'<p>Este es un nuevo Decision Case. El caso anterior se conserva en el historial para mantener la trazabilidad.</p></div>'
      +'</section>'
      :'')
    +caseBarMarkup(
      decisionCase,
      presentations,
      orders,
      fleet,
      approved,
    )
    +'<section class="dispatch-map-chain-section" aria-labelledby="decision-chain-title">'
      +'<header class="dispatch-map-chain-heading">'
        +'<div><span class="dispatch-map-eyebrow">DECISIONES DEL CASO</span>'
          +'<h2 id="decision-chain-title">Tu cadena de decisiones.</h2>'
          +'<p>Cada decisión se aprueba antes de habilitar la siguiente.</p>'
        +'</div>'
        +legendMarkup()
      +'</header>'
      +completeBanner(
        presentations.logistics_final_assignment.runId,
      )
      +'<div class="dispatch-node-map" aria-label="Cadena de decisiones">'
        +nodeCard(
          "logistics_assignment",
          presentations.logistics_assignment,
          nextNodeId==="logistics_assignment",
        )
        +connector(
          "logistics_assignment",
          "logistics_scheduling",
          presentations,
          nextNodeId,
        )
        +nodeCard(
          "logistics_scheduling",
          presentations.logistics_scheduling,
          nextNodeId==="logistics_scheduling",
        )
        +connector(
          "logistics_scheduling",
          "logistics_final_assignment",
          presentations,
          nextNodeId,
        )
        +nodeCard(
          "logistics_final_assignment",
          presentations.logistics_final_assignment,
          nextNodeId==="logistics_final_assignment",
        )
      +'</div>'
    +'</section>'
    +changeDataDialog();

  const fullCaseId=String(decisionCase?.id||"");
  const copyButton=root.querySelector("[data-copy-case-id]");
  if(copyButton){
    copyButton.onclick=async()=>{
      try{
        await navigator.clipboard.writeText(fullCaseId);
        copyButton.classList.add("is-copied");
        copyButton.setAttribute("title","ID copiado");
        window.setTimeout(()=>{
          copyButton.classList.remove("is-copied");
          copyButton.setAttribute("title","Copiar ID");
        },1400);
      }catch{
        copyButton.setAttribute("title","No se pudo copiar");
      }
    };
  }

  const changeDialog=root.querySelector("[data-change-data-dialog]");
  const confirmChange=root.querySelector("[data-confirm-change]");
  if(confirmChange){
    confirmChange.onclick=(event)=>{
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
