import {el,field,section,percentToRatio,ratioToPercent} from './forms.mjs';
export const GOALS=[['MINIMIZE_COST','Minimizar costo'],['MAXIMIZE_SERVICE','Maximizar servicio'],['MAXIMIZE_OWN_CAPACITY','Maximizar capacidad propia'],['MINIMIZE_TRIPS','Minimizar viajes'],['BALANCED','Balanceado'],['CUSTOM','Personalizado']];
const GUARDS=[['MINIMUM_DEMAND_COVERAGE','Cobertura mínima de demanda'],['CRITICAL_DEMAND_COVERAGE','Cobertura de demanda crítica'],['MAXIMUM_EXTERNAL_SHARE','Participación externa máxima'],['MINIMUM_OWN_SHARE','Participación propia mínima']];
const PREFS=[['COST','Costo'],['TRIPS','Viajes'],['SERVICE','Servicio'],['OWN_CAPACITY','Capacidad propia']];
export function policyInputValues(policy){
 return {goal:policy.primary_goal,guards:Object.fromEntries(GUARDS.map(([kind])=>[kind,{enabled:(policy.guardrails||[]).some(x=>x.kind===kind),percent:ratioToPercent(policy.guardrails?.find(x=>x.kind===kind)?.limit??(kind.startsWith('MAXIMUM')?'1':'0'))}])),weights:Object.fromEntries(PREFS.map(([kind])=>[kind,ratioToPercent(policy.preferences?.find(x=>x.kind===kind)?.weight??'.25')]))};
}
export function mountPolicy(form,scope,policy={version:1,primary_goal:'MINIMIZE_COST',guardrails:[],preferences:[]},{readOnly=false,draftValues}={}){
 const body=section(form,'Objetivo global y reglas','El objetivo orienta la decisión. Los límites obligatorios y las preferencias se guardan por separado.');
 const goal=field(body,'Objetivo global',{name:'primary_goal',options:GOALS,value:draftValues?.goal||policy.primary_goal,required:true});goal.disabled=readOnly;
 const details=el('details',undefined,'ultimate-policy'),summary=el('summary','Límites obligatorios y preferencias');details.append(summary);body.append(details);
 const guards=el('div',undefined,'ultimate-grid');details.append(guards);
 const controls=GUARDS.map(([kind,label])=>{
  const wrap=el('div',undefined,'d-field'),choice=el('label',undefined,'d-choice'),check=el('input',undefined,'d-check');check.type='checkbox';check.name='enable_'+kind;check.checked=(policy.guardrails||[]).some(x=>x.kind===kind);check.disabled=readOnly;choice.append(check,el('span',label));wrap.append(choice);guards.append(wrap);
  if(draftValues?.guards?.[kind])check.checked=draftValues.guards[kind].enabled;
  const value=field(wrap,label+' (%)',{name:'guard_'+kind,type:'number',value:draftValues?.guards?.[kind]?.percent??ratioToPercent(policy.guardrails?.find(x=>x.kind===kind)?.limit??(kind.startsWith('MAXIMUM')?'1':'0'))});value.min='0';value.max='100';value.step='.01';value.disabled=readOnly||!check.checked;
  scope.listen(check,'change',()=>value.disabled=readOnly||!check.checked);return {kind,check,value};
 });
 const prefs=el('div',undefined,'ultimate-grid');details.append(prefs);
 const weights=PREFS.map(([kind,label])=>{const value=field(prefs,label+' (%)',{name:'weight_'+kind,type:'number',value:draftValues?.weights?.[kind]??ratioToPercent(policy.preferences?.find(x=>x.kind===kind)?.weight??'.25')});value.min='0';value.max='100';value.step='.01';return {kind,value};});
 function update(){prefs.hidden=goal.value!=='CUSTOM';for(const w of weights)w.value.disabled=readOnly||goal.value!=='CUSTOM';}scope.listen(goal,'change',update);update();
 return {draft(){return {goal:goal.value,guards:Object.fromEntries(controls.map(x=>[x.kind,{enabled:x.check.checked,percent:x.value.value}])),weights:Object.fromEntries(weights.map(x=>[x.kind,x.value.value]))};},read(){return {version:1,primary_goal:goal.value,guardrails:controls.filter(x=>x.check.checked).map(x=>({kind:x.kind,hard:true,limit:percentToRatio(x.value.value)})),preferences:goal.value==='CUSTOM'?weights.map(x=>({kind:x.kind,weight:percentToRatio(x.value.value)})):[]};},validate(){
  const errors={};for(const c of controls)if(c.check.checked)try{percentToRatio(c.value.value);}catch(e){errors[c.value.name]=e.message;}
  if(goal.value==='CUSTOM'){try{const total=weights.reduce((sum,x)=>sum+Math.round(Number(percentToRatio(x.value.value))*10000),0);if(total!==10000)errors.weight_COST='Las preferencias deben sumar 100 %.';}catch(e){errors.weight_COST=e.message;}}
  return errors;
 }};
}
