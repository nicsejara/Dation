// Shared product definitions, independent of the optional catalog renderer.
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

