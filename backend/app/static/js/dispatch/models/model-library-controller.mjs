// Explicit model mutations only. Persist exact intent BEFORE each network write.
export function modelController({record,saveRecord,request}){
 let state=structuredClone(record);
 const persist=patch=>{state=saveRecord({...state,...structuredClone(patch)});return state;};
 const pending=()=>!!(state.createIntent||state.saveIntent||state.publishIntent);
 function updateDraft(draft){if(pending())throw new Error('Hay una operación pendiente. Resolvela antes de modificar el modelo.');persist({draft});}
 async function save({valid=false}={}){
  if(state.publishIntent)throw new Error('Resolvé la publicación pendiente antes de guardar.');
  if(!valid&&!state.createIntent&&!state.saveIntent){persist({savedDraft:state.draft,savedWhere:'browser'});return {where:'browser'};}
  const d=state.draft,body={name:d.name,description:d.description||null,configuration:d.configuration};
  let result;
  if(!state.modelId){
   if(!state.createIntent)persist({createIntent:{id:d.id,...body}});
   result=await request('/api/platform/logistics-models','POST',state.createIntent);
  }else{
   if(!state.saveIntent)persist({saveIntent:{...body,status:'active',expected_revision:d.expected_revision}});
   result=await request('/api/platform/logistics-models/'+state.modelId,'PUT',state.saveIntent);
  }
  const expected=state.createIntent?1:state.saveIntent.expected_revision+1;
  if(result.model?.id!==d.id||result.model.revision!==expected)throw Object.assign(new Error('El servidor no confirmó la identidad y revisión originales del borrador. Se conserva el intento; revisá el estado actual antes de continuar.'),{status:409});
  const draft={...state.draft,expected_revision:result.model.revision};
  persist({modelId:result.model.id,draft,savedDraft:draft,savedWhere:'server',createIntent:null,saveIntent:null});
  return {where:'server',result};
 }
 async function publish(){
  if(!state.publishIntent){await save({valid:true});persist({publishIntent:{version_id:crypto.randomUUID(),expected_revision:state.draft.expected_revision}});}
  const result=await request('/api/platform/logistics-models/'+state.modelId+'/versions','POST',state.publishIntent);
  if(result.version?.id!==state.publishIntent.version_id||result.version?.model_id!==state.modelId||!Number.isSafeInteger(result.version.version)||result.version.version<1||!/^[a-f0-9]{64}$/.test(result.version.config_hash||''))throw new Error('La publicación no confirmó su versión, modelo y hash. Se conserva el intento original.');
  persist({publishedVersionId:result.version.id,publishIntent:null});return result;
 }
 return {get record(){return structuredClone(state);},get pending(){return pending();},updateDraft,save,publish};
}
