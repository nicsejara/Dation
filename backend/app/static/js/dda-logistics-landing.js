(function(){
  "use strict";

  var ROOT_SELECTOR = ".dda-landing";
  var WORKSPACE_KEY = "dation.dispatch.workspace.v4";

  function root(){
    return document.querySelector(ROOT_SELECTOR);
  }

  function navigate(view){
    if(typeof window.dationNavigate === "function"){
      window.dationNavigate(view, view === "logistics-data" ? "data" : null);
    }
  }

  function savedWorkspace(){
    try{
      return JSON.parse(sessionStorage.getItem(WORKSPACE_KEY) || "{}");
    }catch(error){
      return {};
    }
  }

  function scrollToExample(){
    var target = document.getElementById("dda-logistics-example-result");
    if(target){
      target.scrollIntoView({behavior:"smooth",block:"start"});
    }
  }

  function enhanceReveal(container){
    container.classList.add("is-enhanced");
    var nodes = Array.prototype.slice.call(container.querySelectorAll("[data-reveal]"));

    if(!("IntersectionObserver" in window)){
      nodes.forEach(function(node){node.classList.add("is-visible");});
      return;
    }

    var observer = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if(entry.isIntersecting){
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },{threshold:.08});

    nodes.forEach(function(node){observer.observe(node);});
  }

  function animateCount(container){
    var node = container.querySelector("[data-count]");
    if(!node || node.dataset.counted === "true") return;
    var target = Number(node.dataset.count || 0);
    if(!Number.isFinite(target)) return;

    node.dataset.counted = "true";
    if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){
      node.textContent = String(target);
      return;
    }

    var current = 0;
    var timer = window.setInterval(function(){
      current += 1;
      node.textContent = String(Math.min(current,target));
      if(current >= target) window.clearInterval(timer);
    },120);
  }

  function syncDecisionNodes(container){
    var saved = savedWorkspace();
    var nodes = saved && saved.decisionCase && saved.decisionCase.nodes
      ? saved.decisionCase.nodes
      : null;

    if(!nodes) return;

    Object.keys(nodes).forEach(function(nodeId){
      var card = container.querySelector('[data-decision-node="'+nodeId+'"]');
      if(!card) return;

      var status = nodes[nodeId] && nodes[nodeId].status;
      var badge = card.querySelector("[data-node-state]");
      var action = card.querySelector("[data-node-action]");
      var mapping = {
        available:["Disponible","is-available"],
        review:["Requiere revisión","is-review"],
        approved:["Aprobada","is-available"],
        running:["Procesando","is-review"],
        locked:["Bloqueado","is-locked"],
        needs_data:["Requiere datos","is-review"],
        stale:["Desactualizada","is-review"],
        error:["Error","is-review"]
      };
      var resolved = mapping[status] || null;
      if(!resolved) return;

      card.classList.remove("is-available","is-review","is-locked");
      card.classList.add(resolved[1]);

      if(badge){
        badge.className = "dda-landing__state "+resolved[1];
        badge.textContent = resolved[0];
      }

      if(action && nodes[nodeId] && nodes[nodeId].run_id){
        action.disabled = false;
        action.textContent = status === "approved" || status === "review"
          ? "Abrir análisis →"
          : action.textContent;
      }
    });
  }

  function bindActions(container){
    container.querySelectorAll("[data-go-data]").forEach(function(button){
      button.addEventListener("click",function(){navigate("logistics-data");});
    });

    container.querySelectorAll("[data-go-home]").forEach(function(button){
      button.addEventListener("click",function(){navigate("inicio");});
    });

    container.querySelectorAll("[data-scroll-example]").forEach(function(button){
      button.addEventListener("click",scrollToExample);
    });

    var jsonButton = container.querySelector("[data-example-json]");
    var jsonDetails = container.querySelector("#dda-example-json");
    if(jsonButton && jsonDetails){
      jsonButton.addEventListener("click",function(){
        jsonDetails.open = !jsonDetails.open;
        if(jsonDetails.open){
          jsonDetails.scrollIntoView({behavior:"smooth",block:"nearest"});
        }
      });
    }

    var csvButton = container.querySelector("[data-example-csv]");
    if(csvButton){
      csvButton.addEventListener("click",function(){
        var csv = [
          "trip_id,origin,destination,vehicle,estimated_cost",
          "TRIP-01,Córdoba,Rosario,VEH-003,1280",
          "TRIP-02,Córdoba,Santa Fe,VEH-007,940",
          "TRIP-03,Córdoba,Villa María,VEH-002,610"
        ].join("\n");
        var blob = new Blob([csv],{type:"text/csv;charset=utf-8"});
        var url = URL.createObjectURL(blob);
        var anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "dation-ejemplo-calendario.csv";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
      });
    }

    var assignmentAction = container.querySelector('[data-node-action="logistics_assignment"]');
    if(assignmentAction){
      assignmentAction.addEventListener("click",function(){
        var saved = savedWorkspace();
        if(saved && saved.orders && saved.fleet){
          navigate("logistics-data");
        }else{
          navigate("logistics-data");
        }
      });
    }

    container.querySelectorAll("[data-node-action]:not([data-node-action='logistics_assignment'])")
      .forEach(function(button){
        button.addEventListener("click",function(){
          var saved = savedWorkspace();
          if(saved && saved.orders && saved.fleet){
            navigate("logistics-map");
          }else{
            navigate("logistics-data");
          }
        });
      });
  }

  function syncPrimaryCopy(container){
    var saved = savedWorkspace();
    var hasData = Boolean(saved && saved.orders && saved.fleet);
    container.querySelectorAll("[data-dda-data-cta]").forEach(function(button){
      if(button.dataset.fixedCopy === "true") return;
      button.childNodes[0].nodeValue = hasData
        ? "Iniciar nueva decisión "
        : "Cargar mis datos ";
    });
  }

  function boot(){
    var container = root();
    if(!container) return;
    enhanceReveal(container);
    animateCount(container);
    syncDecisionNodes(container);
    syncPrimaryCopy(container);
    bindActions(container);
  }

  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded",boot,{once:true});
  }else{
    boot();
  }

  window.addEventListener("dation:view",function(event){
    if(event.detail && event.detail.view === "logistics-overview"){
      var container = root();
      if(container){
        syncDecisionNodes(container);
        syncPrimaryCopy(container);
      }
    }
  });
})();