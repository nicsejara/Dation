import {el,button} from './forms.mjs';
import {guidedBlock,note} from './guided-ui.mjs';

// UI assessment only: never normalize business data or infer a physical catalog.
export function assessGuidedDraft(draft){
 const c=draft.configuration,g=c.cargo,u=draft.guided_ux||{},catalog=u.catalogue||g;
 const no=reason=>({representable:false,reason});
 if(g.input_mode!=='catalog')return no('Configuración directa: dos CSV, sin catálogo físico.');
 if(!c.active_dimensions.length||c.active_dimensions.some(d=>!['weight_kg','volume_m3'].includes(d)))return no('Las dimensiones actuales incluyen límites que la vista guiada no puede reinterpretar.');
 const primary=c.active_dimensions.includes('weight_kg')?'weight_kg':'volume_m3';
 if(c.primary_dimension!==primary)return no('La dimensión principal actual se conserva; cambiarla requiere una decisión explícita en el editor compatible.');
 if(!['INDIVISIBLE','DISCRETE'].includes(g.split_policy))return no('El granel continuo conserva su unidad física y su contrato en el editor compatible.');
 const products=catalog.products||[],units=catalog.logistic_units||[],presentations=catalog.presentations||[];
 const editing=u.edition==='ultimate'||u.origin==='new-guided';
 if(!products.length&&!presentations.length&&!units.length)return editing?{representable:true,reason:'Borrador guiado nuevo, todavía sin catálogo.'}:no('El catálogo anterior está incompleto. Elegí cómo continuar sin inventar datos.');
 if(!editing&&(!products.length||!presentations.length))return no('El catálogo recuperado todavía no contiene productos y presentaciones representables.');
 if(products.some(p=>Number(p.units_per_package??1)!==1))return no('El catálogo contiene unidades comerciales adicionales por bulto que deben conservarse.');
 if(presentations.some(p=>(p.quantity_kind||'DISCRETE')!=='DISCRETE'||(p.quantity_unit||'presentation')!=='presentation'||p.components.length!==1))return no('Las composiciones mixtas o continuas requieren el editor compatible.');
 if(!editing&&presentations.some(p=>!units.some(v=>v.logistic_unit_id===p.logistic_unit_id)||!products.some(v=>v.product_id===p.components[0].product_id)))return no('Hay referencias pendientes de completar; el editor compatible conserva todos sus IDs.');
 return {representable:true,reason:'Catálogo homogéneo recuperable sin cambiar dimensiones, referencias ni cantidades.'};
}

export function mountEditorChoice(parent,scope,draft,assessment,{choose,startNew}){
 const root=el('div',undefined,'model-wizard-v2 model-editor-choice');root.dataset.editorChoice='';parent.append(root);
 const defs=[['Identidad del modelo','tag',draft.name||'Borrador sin nombre'],['Operación logística','resources',draft.configuration.operating_role],['Carga y capacidad','pallet','Elegí cómo continuar con tu configuración recuperada.'],['Recursos de transporte','resources',draft.configuration.allowed_sources.join(' + ')],['Moneda y costos','costs',draft.configuration.currency_policy.currency]];
 const blocks=defs.map(([title,icon,copy],i)=>guidedBlock(root,i+1,title,copy,icon,{open:i===2}));
 const body=blocks[2].body;note(body,assessment.reason+' El borrador original permanece intacto.');
 if(assessment.representable){const guided=button('Usar vista guiada de tres pasos',()=>choose('guided'),'primary');guided.dataset.useGuided='';body.append(guided);}
 const compatible=button('Continuar con configuración compatible',()=>choose('compatible'));compatible.dataset.continueCompatible='';body.append(compatible);
 if(!assessment.representable){const fresh=button('Iniciar una configuración guiada nueva',startNew);fresh.dataset.newGuided='';body.append(fresh);note(body,'La nueva configuración usa tres CSV. Se pedirá confirmación y se conservará una copia recuperable de este borrador, sin convertir ni borrar su catálogo.');}
 const errors=el('p',undefined,'d-field__error');errors.role='alert';body.append(errors);
 const read=()=>structuredClone(draft),validate=()=>({cargo_catalog:'Elegí una experiencia de edición para continuar.'});
 return {read,validate,sectionValidity:()=>[false,false,false,false,false],sectionCompletion:()=>[false,false,false,false,false],canPublish:()=>false,
  showErrors(){errors.textContent=validate().cargo_catalog;blocks[2].details.open=true;errors.tabIndex=-1;errors.focus();return validate();},showSectionErrors(){return this.showErrors();},refreshErrors(){},invalidateCompiled(){},setCompiled(){},showServerError(message){errors.textContent=message;},lock(){for(const n of root.querySelectorAll('button'))n.disabled=true;}};
}
