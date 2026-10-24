import {mountDialog} from '../../platform/components.mjs';
import {scopeFor} from '../lifecycle.mjs';

/** UI confirmation only. Admission remains the sole authority for invalidation. */
export function confirmNewRun(root){
  const owner=scopeFor(root),dialog=document.createElement('dialog'),id='new-run-'+crypto.randomUUID();
  dialog.className='d-platform new-run-warning';dialog.dataset.newRunWarning='';
  dialog.setAttribute('aria-labelledby',id+'-title');dialog.setAttribute('aria-describedby',id+'-description');
  const title=document.createElement('h2');title.id=id+'-title';title.textContent='Crear una nueva corrida';
  const description=document.createElement('p');description.id=id+'-description';
  description.textContent='Al ejecutar una nueva corrida, la aprobación vigente de esta decisión y las decisiones posteriores dejarán de estar vigentes. Las corridas anteriores y sus aprobaciones se conservarán en el historial.';
  const upstream=document.createElement('p');upstream.textContent='Las decisiones anteriores aprobadas se conservan.';
  const actions=document.createElement('div');actions.className='new-run-warning__actions';
  for(const [value,label,variant] of [['cancel','Cancelar','secondary'],['confirm','Confirmar nueva corrida','primary']]){
    const button=document.createElement('button');button.type='button';button.value=value;
    button.className='d-button d-button--'+variant;button.dataset.dialogClose='';button.textContent=label;actions.append(button);
  }
  dialog.append(title,description,upstream,actions);root.append(dialog);
  const view=mountDialog({dialog,initialFocus:'button[value=cancel]'}),scope=scopeFor(dialog);
  return new Promise(resolve=>{
    let settled=false,release=()=>{};
    const finish=accepted=>{if(settled)return;settled=true;release();view.dispose();dialog.remove();resolve(accepted);};
    scope.listen(dialog,'close',()=>finish(dialog.returnValue==='confirm'));
    release=owner?.own(()=>finish(false))||release;
    view.open();
  });
}
