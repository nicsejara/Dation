import {el} from '../models/forms.mjs';
function fact(root,label,value){const row=el('div');row.append(el('dt',label),el('dd',value==null||value===''?'No informado':String(value)));root.append(row);}
export function renderSummary(root,context,pack,responsibilities){
 const model=el('section'),contract=el('section'),caseSection=el('section');root.append(model,contract,caseSection);
 model.append(el('h3','Logistics Model'));const m=el('dl');model.append(m);fact(m,'Modelo',context.model?.name);fact(m,'Versión',context.model_version?.version);fact(m,'Operating Role',context.model_version?.config_jsonb?.operating_role);fact(m,'Patrón',context.model_version?.config_jsonb?.transport_pattern);
 contract.append(el('h3','Data Contract + Preparation'));const d=el('dl');contract.append(d);fact(d,'Pack publicado',pack?.version?.version);fact(d,'Data Owner',responsibilities?.stages?.data_owner?.owner?.name);
 for(const [entity,value]of Object.entries(pack?.contracts||{}))fact(d,entity==='transport_demand'?'Contrato de demanda':'Contrato de recursos',value.contract_hash);
 for(const e of pack?.entries||[])fact(d,e.slot_key==='transport_demand'?'Demanda':'Recursos',e.record_count+' registros');
 caseSection.append(el('h3','Decision Case'));const c=el('dl');caseSection.append(c);const row=context.case||{},policy=context.planning_context?.case_policy||row.case_policy_jsonb||{};
 for(const [label,value]of [['Nombre',row.label],['Descripción',row.description],['Inicio',row.planning_start],['Fin',row.planning_end],['Horizonte',row.horizon_type],['Modalidad',row.operating_mode],['Objetivo',policy.primary_goal]])fact(c,label,value);
 for(const key of ['guardrails','preferences'])fact(c,key==='guardrails'?'Límites':'Preferencias',(policy[key]||[]).map(x=>typeof x==='string'?x:Object.entries(x).map(([k,v])=>k+': '+String(v)).join(', ')).join(' · ')||'Sin reglas declaradas');
 for(const id of ['logistics_assignment','logistics_scheduling'])fact(c,id==='logistics_assignment'?'Decision Owner D1':'Decision Owner D2',responsibilities?.stages?.[id]?.owner?.name);
}
