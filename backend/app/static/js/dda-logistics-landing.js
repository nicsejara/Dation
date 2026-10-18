(function(){
  var revealObserver=null;
  "use strict";

  var ROOT_SELECTOR=".dda-landing";
  var WORKSPACE_KEY="dation.dispatch.workspace.v5";

  var ENGINE_VARIABLES={
    active:[
      {id:"cost",label:"Costo",description:"Costo total de los viajes según tu flota.",icon:"dda-i-dollar"},
      {id:"trips",label:"Viajes",description:"Cantidad de viajes necesarios para entregar todo.",icon:"dda-i-route"},
      {id:"time",label:"Tiempo",description:"Plazo total hasta completar las entregas.",icon:"dda-i-clock"}
    ],
    consolidating:[
      {id:"co2",label:"CO₂",description:"Hoy se informa como estimación; todavía no se optimiza.",icon:"dda-i-clock"},
      {id:"risk",label:"Riesgo",description:"Se suma a medida que se consolide el modelo.",icon:"dda-i-clock"},
      {id:"service",label:"Servicio",description:"Se suma a medida que se consolide el modelo.",icon:"dda-i-clock"}
    ]
  };

  var DECISION_STEPS={
    logistics_assignment:"01",
    logistics_scheduling:"02",
    logistics_final_assignment:"03"
  };

  function root(){
    return document.querySelector(ROOT_SELECTOR);
  }

  function navigate(view){
    if(typeof window.dationNavigate==="function"){
      window.dationNavigate(view,view==="logistics-data"?"data":null);
    }
  }

  function savedWorkspace(){
    try{
      var saved=JSON.parse(sessionStorage.getItem(WORKSPACE_KEY)||"{}");
      return saved&&typeof saved==="object"&&!Array.isArray(saved)?saved:{};
    }catch(error){
      return {};
    }
  }

  function iconMarkup(symbol){
    return '<svg class="dda-icon" aria-hidden="true"><use href="#'+symbol+'"></use></svg>';
  }

  function renderVariables(container){
    var target=container.querySelector("[data-variables-inline]");
    if(!target)return;
    var items=[]
      .concat(
        ENGINE_VARIABLES.active.map(function(item){return Object.assign({},item,{state:"active"});}),
        ENGINE_VARIABLES.consolidating.map(function(item){return Object.assign({},item,{state:"inactive"});})
      );
    target.innerHTML=items.map(function(item){
      var active=item.state==="active";
      return '<span class="dda-landing__variable-pill '+(active?"is-active":"is-inactive")+'" title="'+item.description+'">'
        +'<span class="dda-landing__variable-pill-icon">'+iconMarkup(active?"dda-i-check-circle":"dda-i-clock")+'</span>'
        +'<strong>'+item.label+'</strong><small class="dda-landing__variable-status">'+(active?'Optimiza hoy':'En consolidación')+'</small></span>';
    }).join("");
  }

  function makeDecisionChainInformational(container){
    var section=container.querySelector("#dda-logistics-decision-map");
    if(!section)return;
    var eyebrow=section.querySelector(".dda-landing__section-eyebrow");
    var heading=section.querySelector(".dda-landing__section-head--map h2");
    var support=section.querySelector(".dda-landing__section-head--map p");
    var chain=section.querySelector(".dda-landing__chain");
    var close=section.querySelector(".dda-landing__map-close");
    if(eyebrow)eyebrow.textContent="Cómo se encadenan las decisiones";
    if(heading)heading.textContent="Una decisión alimenta a la siguiente.";
    if(support){
      support.textContent="El DDA Logística no entrega una respuesta aislada: construye una cadena de decisiones conectadas. El estado real de cada caso se consulta en tu Decision Map.";
    }
    if(chain)chain.setAttribute("aria-label","Cadena de decisiones del DDA Logística");
    section.querySelectorAll("[data-decision-node]").forEach(function(card){
      var nodeId=card.getAttribute("data-decision-node");
      var top=card.querySelector(".dda-landing__node-top");
      var state=card.querySelector("[data-node-state]");
      var footer=card.querySelector(".dda-landing__node-footer");
      card.classList.remove("is-pending","is-available","is-review","is-approved","is-locked");
      card.classList.add("is-conceptual");
      state&&state.remove();
      footer&&footer.remove();
      if(top&&!top.querySelector("[data-concept-index]")){
        var index=document.createElement("span");
        index.className="dda-landing__section-eyebrow";
        index.setAttribute("data-concept-index","");
        index.textContent="DECISIÓN "+(DECISION_STEPS[nodeId]||"—");
        top.appendChild(index);
      }
    });
    var legend=section.querySelector(".dda-landing__state-legend");
    legend&&legend.remove();
    if(close){
      close.textContent="Cada resultado se revisa y se aprueba antes de alimentar la decisión siguiente. Así mantenés una cadena trazable, paso a paso.";
    }
  }

  var refreshGeneration=0;
  function activeCase(){
    var current=window.DationDispatch?.getWorkspace?.();
    return Boolean((current||savedWorkspace()).decisionCase?.id);
  }
  function setMapAvailability(container,available){
    var button=container.querySelector('[data-open-decision-map]');
    if(!button)return;
    button.disabled=!available;
    button.setAttribute('aria-disabled',String(!available));
    button.title=available?'Abrir un Decision Case existente':'Todavía no hay Decision Cases para revisar';
  }
  async function syncHeroActions(container){
    var generation=++refreshGeneration;
    setMapAvailability(container,activeCase());
    var listCases=window.DationDispatch?.listDecisionCases;
    if(typeof listCases!=='function')return;
    try{
      var cases=await listCases();
      if(generation===refreshGeneration)setMapAvailability(container,activeCase()||Boolean(cases?.length));
    }catch(error){
      if(generation===refreshGeneration&&!activeCase()){
        setMapAvailability(container,false);
        container.querySelector('[data-open-decision-map]').title='No se pudo comprobar la disponibilidad de casos';
      }
    }
  }

  function enhanceReveal(container){
    revealObserver&&revealObserver.disconnect();
    container.classList.add("is-enhanced");
    var nodes=Array.prototype.slice.call(container.querySelectorAll("[data-reveal]"));
    if(!("IntersectionObserver" in window)||window.matchMedia("(prefers-reduced-motion: reduce)").matches){
      nodes.forEach(function(node){node.classList.add("is-visible");});
      return;
    }
    var observer=revealObserver=new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },{threshold:.08});
    nodes.forEach(function(node){observer.observe(node);});
  }

  function bindActions(container){
    var start=container.querySelector('[data-start-new-decision]');
    var map=container.querySelector('[data-open-decision-map]');
    if(start)start.addEventListener('click',function(){
      if(typeof window.DationDispatch?.startNewDecision==='function')window.DationDispatch.startNewDecision();
      else navigate('logistics-data');
    });
    if(map)map.addEventListener('click',function(){
      if(map.disabled)return;
      if(typeof window.DationDispatch?.openDecisionMap==='function')window.DationDispatch.openDecisionMap({trigger:map});
      else navigate('logistics-map');
    });
  }

  function refresh(container){
    renderVariables(container);
    makeDecisionChainInformational(container);
    syncHeroActions(container);
  }

  function boot(){
    var container=root();
    if(!container)return;
    makeDecisionChainInformational(container);
    bindActions(container);
    syncHeroActions(container);
    if(window.dationGetCurrentView?.()==="logistics-overview"){refresh(container);enhanceReveal(container);}
  }

  import("/static/js/dispatch/traceability-controller.mjs").catch(function(){});

  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",boot,{once:true});
  }else{
    boot();
  }

  window.addEventListener("dation:view",function(event){
    revealObserver&&revealObserver.disconnect();
    refreshGeneration++;
    if(event.detail&&event.detail.view==="logistics-overview"){
      var container=root();
      if(container){refresh(container);enhanceReveal(container);}
    }
  });

  window.addEventListener("dation:cases-ready",function(){
    var container=root();
    if(container&&window.dationGetCurrentView?.()==="logistics-overview")syncHeroActions(container);
  });
  window.addEventListener("pagehide",function(){refreshGeneration++;revealObserver&&revealObserver.disconnect();});
  window.addEventListener("pageshow",function(event){
    if(event.persisted&&window.dationGetCurrentView?.()==="logistics-overview"){
      var container=root();if(container){syncHeroActions(container);enhanceReveal(container);}
    }
  });
})();
