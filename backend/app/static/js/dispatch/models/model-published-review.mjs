// Projection of server-owned, pinned resources. Never read a draft or write API.
import {el,button} from './forms.mjs';
import {mountHistorical} from './model-historical-view.mjs';
import {volume} from './cargo-guided-state.mjs';
import {unitArt,bultoArt,volumeText} from './cargo-presentation-ui.mjs';
import {readout,note} from './guided-ui.mjs';
import {wizardIcon} from './wizard-ui.mjs';
import {evaluateCoherence,coherenceCopy} from './cargo-volume-coherence.mjs';
const labels={weight_kg:'Peso (kg)',volume_m3:'Volumen (m³)',pallets:'Pallets',units:'Unidades',PALLET:'Pallet',BOX:'Caja',CRATE:'Cajón',BIG_BAG:'Big bag',OTHER:'Otra unidad'};
const available=v=>v===null||v===undefined||v===''?'No disponible':String(v);
function facts(host,entries){const dl=el('dl',undefined,'r5-history-facts');for(const [label,value]of entries)readout(dl,label,available(value));host.append(dl);}
function card(host,title){const section=el('section',undefined,'d-card r6-review-card');section.append(el('h3',title,'d-card-title'));host.append(section);return section;}
export function mountPublishedReview(panel,current,{onChooseVersion=null}={}){
 const {model,model_version:version,case:linked}=current,c=version.config_jsonb,g=c.cargo||{},units=g.logistic_units||[],types=g.presentations||[];
 panel.details.classList.add('r6-model-review');panel.details.dataset.modelReview='';panel.details.dataset.reviewVersion=version.id;panel.details.dataset.reviewCase=linked.id;
 const header=panel.details.querySelector(':scope > summary'),copy=el('span',undefined,'r6-review-copy model-wizard-heading'),title=el('span','01 Logistics Model','ultimate-disclosure__title'),actions=el('span',undefined,'r6-review-actions'),cta=button('Crear Case con otra versión',onChooseVersion),status=el('span','Publicado','ultimate-disclosure__status r6-review-header-action');
 cta.classList.add('r6-review-header-action');cta.dataset.reviewChooseVersion='';cta.disabled=!onChooseVersion;status.dataset.reviewPublished='';status.dataset.state='complete';status.role='status';
 copy.append(title,el('p','Modelo y versión publicados vinculados a este Case. Se muestran en modo consulta.','d-metadata'));actions.append(cta,status);header.classList.add('r6-review-header');const tile=el('span',undefined,'model-wizard-tile');tile.append(wizardIcon('layers'));header.replaceChildren(tile,copy,actions);panel.details.querySelector('.ultimate-disclosure__content > .d-metadata')?.remove();
 panel.body.classList.add('r6-review-body');const layout=el('div',undefined,'r6-review-layout'),left=el('div',undefined,'r6-review-sections'),right=el('aside',undefined,'r6-review-sidebar');layout.append(left,right);panel.body.append(layout);
 const original={name:model.name,description:model.description,created_at:model.created_at,updated_at:model.updated_at,version:version.version,configuration:c};
 const projection=mountHistorical(left,original,{reason:'Configuración publicada vinculada a este Case. Se conserva sin cambios.'},true);
 for(const [i,block]of left.querySelectorAll('.model-v2-block').entries())block.open=i===0;
 const dims=(c.active_dimensions||[]).map(v=>labels[v]||v).join(' + ')||'No declarado';left.append(el('p',(g.input_mode==='catalog'?'Catálogo publicado · '+types.length+' tipos':'Contrato publicado sin catálogo')+' · '+dims,'r6-review-compact'));
 const summary=card(right,'Resumen del modelo');summary.append((units.length===1?unitArt(units[0].type,{loaded:true}):bultoArt('otra')).node);if(units.length!==1)summary.append(el('p','Ilustración genérica; consultá las unidades declaradas en el contrato.','d-metadata'));
 facts(summary,[['Modelo',model.name],['Unidad logística',units.map(u=>u.label||labels[u.type]||u.type).join(' · ')],['Tipos de carga',g.input_mode==='catalog'?types.length:'Sin catálogo'],['Tara del soporte',units.length===1&&units[0].tare_mass?units[0].tare_mass.value+' '+units[0].tare_mass.unit:null],...types.map(t=>['Volumen exterior · '+t.label,t.loaded_dimensions?volumeText(volume(t.loaded_dimensions)):t.external_volume?volumeText(Number(t.external_volume.value)/(t.external_volume.unit==='l'?1000:1)):null]),['Capacidades controladas',dims],['Moneda',c.currency_policy?.currency]]);
 const state=card(right,'Estado y vinculación'),date=version.published_at||version.created_at,parsed=date?new Date(date):null;
 facts(state,[['Estado','Publicado'],['Case vinculado',linked.label||linked.id],['Versión',version.version],['Publicado el',parsed&&!Number.isNaN(parsed.getTime())?new Intl.DateTimeFormat('es-AR',{dateStyle:'medium',timeStyle:'short',hourCycle:'h23',timeZone:'America/Argentina/Buenos_Aires'}).format(parsed):null],['Modelo ID',model.id],['Versión ID',version.id],['Edición','Consulta de la versión vinculada']]);
 note(right,'Esta versión ya está vinculada al Case actual. Para trabajar con otra versión, creá un nuevo Case; se conserva el original.');
 for(const t of types){const p=(g.products||[]).find(p=>p.product_id===t.components?.[0]?.product_id);if(!p||t.components?.length!==1)continue;const d=t.loaded_dimensions,external=t.external_volume,u={type:d?'PALLET':'OTHER',...(d?{length:d.length,width:d.width,height:d.height,measure:d.unit}:{exteriorVolume:external?.unit==='m3'?external.value:null})},result=evaluateCoherence(u,{...(p.dimensions||{}),packageType:p.unit_label,quantity:t.components[0].quantity});if(result.blocking)note(summary,'Aviso sobre '+t.label+': '+coherenceCopy(result)+' El contrato publicado se conserva sin cambios.');}
 return {read:projection.read};
}
