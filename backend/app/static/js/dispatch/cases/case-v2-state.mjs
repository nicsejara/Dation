// Pure Case definition state. Model navigation never changes this selection.
export const CASE_BLOCKS=['Identidad','Vinculación del modelo','Horizonte y modalidad','Objetivo global','Reglas y restricciones','Éxito y aprobación'];
export const CASE_GOALS=[['MINIMIZE_COST','Minimizar costo total'],['MAXIMIZE_SERVICE','Maximizar servicio'],['MAXIMIZE_OWN_CAPACITY','Maximizar flota propia'],['MINIMIZE_TRIPS','Minimizar viajes'],['BALANCED','Balanceado'],['CUSTOM','Personalizado']];
const copy=v=>structuredClone(v);
export const caseRoute=(values={})=>({view:'logistics-case-setup',caseId:null,nodeId:null,runId:null,...values,journeyVersion:'v2',caseView:values.caseView||(values.caseId?'definition':'library'),caseMode:values.caseMode||'review',coreStep:null});
export function newCaseDraft(){return {id:crypto.randomUUID(),workId:crypto.randomUUID(),name:'',description:'',binding:null,
 planning_start:'',planning_end:'',horizon_type:'WEEKLY',operating_mode:'OPERATIONAL',primary_goal:'MINIMIZE_COST',
 weights:{COST:'25',TRIPS:'25',SERVICE:'25',OWN_CAPACITY:'25'},preferOwn:false,critical:'100',success:'98',owner:'',
 confirmed:{},confirmedDefinition:null,provenance:null,preparation:{id:null,version_id:null},creationIntent:null,updateIntent:null};}
const ratio=v=>{const n=Number(v);if(!/^(?:100(?:\.0{1,2})?|\d{1,2}(?:\.\d{1,2})?)$/.test(String(v))||!Number.isFinite(n)||n<0||n>100)throw new Error('Ingresá un porcentaje de 0 a 100 con hasta dos decimales.');return String(Math.round(n*100)/10000);};
export function caseDefinition(d){
 const policy={version:1,primary_goal:d.primary_goal,guardrails:[{kind:'CRITICAL_DEMAND_COVERAGE',hard:true,limit:ratio(d.critical)}],preferences:[]};
 if(d.primary_goal==='CUSTOM')policy.preferences=Object.entries(d.weights).map(([kind,w])=>({kind,weight:ratio(w)}));
 return {schema_version:'decision_case_definition_v2',case_work_id:d.definitionWorkId||d.workId,
  identity:{name:d.name.normalize('NFC').trim(),description:d.description.trim()?d.description.normalize('NFC').trim():null},model_binding:copy(d.binding),
  decision_context:{planning_start:d.planning_start,planning_end:d.planning_end,horizon_type:d.horizon_type,operating_mode:d.operating_mode},
  case_policy:policy,business_rules:{version:1,prefer_own_fleet_on_cost_tie:d.preferOwn},
  acceptance_policy:{version:1,metric:'TOTAL_DEMAND_COVERAGE',comparator:'GTE',threshold:ratio(d.success),basis:'CANONICAL_MODEL_PRIMARY_DIMENSION'},
  approval_policy:{kind:'MANUAL_DECISION_OWNER'},provenance:copy(d.provenance)};
}
export function blockErrors(d,index,{canAssign=false}={}){
 const percent=v=>{try{ratio(v);return false;}catch{return true;}};
 if(index===1)return !d.name.trim()||d.name.trim().length>120||d.description.length>1000?'Ingresá un nombre de hasta 120 caracteres y una descripción de hasta 1000.':null;
 if(index===2)return !d.binding?.model_id||!d.binding?.model_version_id?'Todavía no seleccionaste un Logistics Model. Elegí y confirmá una versión publicada.':null;
 if(index===3)return !/^\d{4}-\d{2}-\d{2}$/.test(d.planning_start)||!/^\d{4}-\d{2}-\d{2}$/.test(d.planning_end)||d.planning_end<d.planning_start?'Completá las fechas inclusivas en orden.':null;
 if(index===4)return !CASE_GOALS.some(([v])=>v===d.primary_goal)||d.primary_goal==='CUSTOM'&&(Object.values(d.weights).some(percent)||Math.abs(Object.values(d.weights).reduce((s,v)=>s+Number(v),0)-100)>1e-8)?'Los cuatro pesos personalizados deben sumar 100 %.':null;
 if(index===5)return percent(d.critical)||d.preferOwn&&d.primary_goal!=='MINIMIZE_COST'?'La cobertura debe estar entre 0 y 100 %. El desempate requiere minimizar costo.':null;
 if(index===6)return percent(d.success)||canAssign&&!d.owner?'Definí la cobertura objetivo y seleccioná un Decision Owner elegible.':null;
 return null;
}
export function fromDefinition(snapshot,caseId=null){const d=newCaseDraft();Object.assign(d,snapshot.identity,snapshot.decision_context,{binding:copy(snapshot.model_binding),definitionWorkId:snapshot.case_work_id,
 primary_goal:snapshot.case_policy.primary_goal,preferOwn:snapshot.business_rules.prefer_own_fleet_on_cost_tie,
 critical:String(Number(snapshot.case_policy.guardrails[0].limit)*100),success:String(Number(snapshot.acceptance_policy.threshold)*100),provenance:copy(snapshot.provenance)});
 d.description=snapshot.identity.description||'';
 for(const p of snapshot.case_policy.preferences)d.weights[p.kind]=String(Number(p.weight)*100);
 if(caseId)d.id=caseId;d.confirmed=Object.fromEntries(CASE_BLOCKS.map((_,i)=>[i+1,true]));d.confirmedDefinition=copy(snapshot);return d;}
export function creationBody(d,canAssign){const definition=d.confirmedDefinition;if(!definition)throw new Error('Confirmá primero los seis bloques.');
 return {id:d.id,...definition.identity,...definition.decision_context,logistics_model_version_id:definition.model_binding.model_version_id,
 case_policy:copy(definition.case_policy),decision_owner_user_id:canAssign?d.owner||null:null,definition_v2:copy(definition)};}
export function invalidateBlock(d,index){delete d.confirmed[index];d.confirmedDefinition=null;if(index===2||index===4){delete d.confirmed[5];delete d.confirmed[6];}}
