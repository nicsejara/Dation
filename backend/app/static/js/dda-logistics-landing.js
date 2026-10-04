(function(){
  "use strict";

  var ROOT_SELECTOR=".dda-landing";
  var WORKSPACE_KEY="dation.dispatch.workspace.v4";

  var ENGINE_VARIABLES={
    active:[
      {
        id:"cost",
        label:"Costo",
        description:"Costo total de los viajes según tu flota.",
        icon:"dda-i-dollar"
      },
      {
        id:"trips",
        label:"Viajes",
        description:"Cantidad de viajes necesarios para entregar todo.",
        icon:"dda-i-route"
      },
      {
        id:"time",
        label:"Tiempo",
        description:"Plazo total hasta completar las entregas.",
        icon:"dda-i-clock"
      }
    ],
    consolidating:[
      {
        id:"co2",
        label:"CO₂",
        description:"Hoy se informa como estimación; todavía no se optimiza.",
        icon:"dda-i-clock"
      },
      {
        id:"risk",
        label:"Riesgo",
        description:"Se suma a medida que se consolide el modelo.",
        icon:"dda-i-clock"
      },
      {
        id:"service",
        label:"Servicio",
        description:"Se suma a medida que se consolide el modelo.",
        icon:"dda-i-clock"
      }
    ]
  };

  var NODE_META={
    logistics_assignment:{
      dependency:null,
      lockedCopy:"Disponible al cargar datos."
    },
    logistics_scheduling:{
      dependency:"Asignación de carga",
      lockedCopy:"Se habilita al aprobar Asignación de carga."
    },
    logistics_final_assignment:{
      dependency:"Planificación de despachos",
      lockedCopy:"Se habilita al aprobar Planificación de despachos."
    }
  };

  function root(){
    return document.querySelector(ROOT_SELECTOR);
  }

  function navigate(view){
    if(typeof window.dationNavigate==="function"){
      window.dationNavigate(
        view,
        view==="logistics-data"?"data":null
      );
    }
  }

  function savedWorkspace(){
    try{
      return JSON.parse(
        sessionStorage.getItem(WORKSPACE_KEY)||"{}"
      );
    }catch(error){
      return {};
    }
  }

  function iconMarkup(symbol){
    return (
      '<svg class="dda-icon" aria-hidden="true">'
      +'<use href="#'+symbol+'"></use>'
      +'</svg>'
    );
  }

  function renderVariables(container){
    var target=container.querySelector(
      "[data-variables-inline]"
    );
    if(!target)return;

    var items=[]
      .concat(
        ENGINE_VARIABLES.active.map(function(item){
          return Object.assign({},item,{state:"active"});
        }),
        ENGINE_VARIABLES.consolidating.map(function(item){
          return Object.assign({},item,{state:"inactive"});
        })
      );

    target.innerHTML=items.map(function(item){
      var active=item.state==="active";
      return (
        '<span class="dda-landing__variable-pill '
        +(active?"is-active":"is-inactive")
        +'" title="'+item.description+'">'
          +'<span class="dda-landing__variable-pill-icon">'
            +iconMarkup(
              active
                ?"dda-i-check-circle"
                :"dda-i-clock"
            )
          +'</span>'
          +'<strong>'+item.label+'</strong>'
        +'</span>'
      );
    }).join("");
  }

  function enhanceReveal(container){
    container.classList.add("is-enhanced");

    var nodes=Array.prototype.slice.call(
      container.querySelectorAll("[data-reveal]")
    );

    if(
      !("IntersectionObserver" in window)
      || window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches
    ){
      nodes.forEach(function(node){
        node.classList.add("is-visible");
      });
      return;
    }

    var observer=new IntersectionObserver(
      function(entries){
        entries.forEach(function(entry){
          if(entry.isIntersecting){
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {threshold:.08}
    );

    nodes.forEach(function(node){
      observer.observe(node);
    });
  }

  function hasData(saved){
    return Boolean(
      saved
      && saved.orders
      && saved.fleet
    );
  }

  function decisionNodes(saved){
    return (
      saved
      && saved.decisionCase
      && saved.decisionCase.nodes
    )
      ?saved.decisionCase.nodes
      :{};
  }

  function normalizedRuntimeStatus(node){
    var status=node&&node.status;

    if(status==="approved")return "approved";

    if(
      status==="review"
      ||status==="running"
      ||status==="error"
      ||status==="stale"
      ||status==="needs_data"
    ){
      return "review";
    }

    return "available";
  }

  function deriveMapStates(saved){
    var dataReady=hasData(saved);
    var nodes=decisionNodes(saved);
    var assignment=nodes.logistics_assignment||{};
    var scheduling=nodes.logistics_scheduling||{};
    var finalAssignment=nodes.logistics_final_assignment||{};

    if(!dataReady){
      return {
        logistics_assignment:"pending",
        logistics_scheduling:"locked",
        logistics_final_assignment:"locked"
      };
    }

    var assignmentStatus=normalizedRuntimeStatus(assignment);

    if(assignmentStatus!=="approved"){
      return {
        logistics_assignment:assignmentStatus,
        logistics_scheduling:"locked",
        logistics_final_assignment:"locked"
      };
    }

    var schedulingStatus=normalizedRuntimeStatus(scheduling);

    if(schedulingStatus!=="approved"){
      return {
        logistics_assignment:"approved",
        logistics_scheduling:schedulingStatus,
        logistics_final_assignment:"locked"
      };
    }

    var finalStatus=normalizedRuntimeStatus(finalAssignment);

    return {
      logistics_assignment:"approved",
      logistics_scheduling:"approved",
      logistics_final_assignment:finalStatus
    };
  }

  function statePresentation(state){
    var map={
      pending:{
        label:"Pendiente de datos",
        css:"is-pending",
        icon:"dda-i-clock",
        action:null
      },
      available:{
        label:"Disponible",
        css:"is-available",
        icon:"dda-i-play-circle",
        action:"Abrir →"
      },
      review:{
        label:"Requiere revisión",
        css:"is-review",
        icon:"dda-i-alert-circle",
        action:"Revisar →"
      },
      approved:{
        label:"Aprobada",
        css:"is-approved",
        icon:"dda-i-check-circle",
        action:"Ver análisis →"
      },
      locked:{
        label:"Bloqueada",
        css:"is-locked",
        icon:"dda-i-lock",
        action:null
      }
    };

    return map[state]||map.locked;
  }

  function syncDecisionMap(container){
    var saved=savedWorkspace();
    var states=deriveMapStates(saved);

    Object.keys(states).forEach(function(nodeId){
      var card=container.querySelector(
        '[data-decision-node="'+nodeId+'"]'
      );
      if(!card)return;

      var presentation=statePresentation(states[nodeId]);
      var badge=card.querySelector("[data-node-state]");
      var action=card.querySelector("[data-node-action]");
      var lockCopy=card.querySelector("[data-node-lockcopy]");

      card.classList.remove(
        "is-pending",
        "is-available",
        "is-review",
        "is-approved",
        "is-locked"
      );
      card.classList.add(presentation.css);

      if(badge){
        badge.className=(
          "dda-landing__state "
          +presentation.css
        );
        badge.innerHTML=(
          iconMarkup(presentation.icon)
          +presentation.label
        );
      }

      if(action){
        if(presentation.action){
          action.hidden=false;
          action.disabled=false;
          action.textContent=presentation.action;
        }else{
          action.hidden=true;
          action.disabled=true;
        }
      }

      if(lockCopy){
        if(presentation.action){
          lockCopy.hidden=true;
        }else{
          lockCopy.hidden=false;
          lockCopy.textContent=(
            states[nodeId]==="pending"
              ?NODE_META[nodeId].lockedCopy
              :NODE_META[nodeId].lockedCopy
          );
        }
      }
    });
  }



  function scrollToDecisionMap(){
    var target=document.getElementById(
      "dda-logistics-decision-map"
    );

    if(target){
      target.scrollIntoView({
        behavior:"smooth",
        block:"start"
      });
    }
  }

  window.dationScrollToDecisionMap=scrollToDecisionMap;


  function bindActions(container){
    container.querySelectorAll(
      "[data-go-data]"
    ).forEach(function(button){
      button.addEventListener("click",function(){
        if(
          button.dataset.mode==="latest"
          &&typeof window.dationOpenLatestDecision==="function"
        ){
          window.dationOpenLatestDecision();
          return;
        }

        navigate("logistics-data");
      });
    });

    container.querySelectorAll(
      "[data-go-home]"
    ).forEach(function(button){
      button.addEventListener("click",function(){
        navigate("inicio");
      });
    });

    container.querySelectorAll(
      "[data-scroll-decision-map]"
    ).forEach(function(button){
      button.addEventListener(
        "click",
        scrollToDecisionMap
      );
    });

    container.querySelectorAll(
      "[data-node-action]"
    ).forEach(function(button){
      button.addEventListener("click",function(){
        var saved=savedWorkspace();

        if(hasData(saved)){
          navigate("logistics-map");
        }else{
          navigate("logistics-data");
        }
      });
    });

  }

  function refresh(container){
    renderVariables(container);
    syncDecisionMap(container);
  }

  function boot(){
    var container=root();
    if(!container)return;

    refresh(container);
    enhanceReveal(container);
    bindActions(container);
  }

  if(document.readyState==="loading"){
    document.addEventListener(
      "DOMContentLoaded",
      boot,
      {once:true}
    );
  }else{
    boot();
  }

  window.addEventListener(
    "dation:view",
    function(event){
      if(
        event.detail
        &&event.detail.view==="logistics-overview"
      ){
        var container=root();
        if(container){
          refresh(container);
        }
      }
    }
  );
})();