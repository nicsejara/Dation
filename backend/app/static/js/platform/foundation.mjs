import registry from '../../contracts/foundation-v2.json' with {type:'json'};

function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
export const FOUNDATION=freeze(registry);
export function objectivePresentation(value){const id=FOUNDATION.objectiveAliases[value]||value;return id?{id,label:FOUNDATION.objectives[id]||id}:null;}
export function statePresentation(status,selected=false){return {status,tone:FOUNDATION.statusTones[status]||'neutral',selected,selectionTone:selected?FOUNDATION.selectionTone:null};}
export function caseContext(value={}){
 if(value.context)return value.context;
 const id=value.id||value.case_id||null,dda=value.dda||value.domain||'logistics';
 return {caseId:id,friendlyId:id?'DC-'+String(id).slice(0,8).toUpperCase():null,label:value.label||null,dda,
  status:value.status||'active',currentNode:value.current_step||value.node_id||null,progress:value.progress||null};
}
