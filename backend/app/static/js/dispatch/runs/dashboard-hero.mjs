import {scopeFor} from '../lifecycle.mjs';

/** The two approved illustrations occupy the same physical slot, outside result copy. */
export function dashboardHeroVisual(kind){
  const asset=kind==='scheduling'?'scheduling-isometric.webp':'assignment-isometric.webp';
  return '<div class="dashboard-hero__visual" data-dashboard-visual>'
    +'<div class="dashboard-hero__media '+kind+'-hero__art" aria-hidden="true">'
      +'<img src="/static/assets/'+asset+'" width="724" height="543" alt="" decoding="async">'
    +'</div></div>';
}

export function bindDashboardHeroVisual(root){
  const frame=root.querySelector('.dashboard-hero__media'),image=frame?.querySelector('img');if(!image)return;
  const fallback=()=>{image.hidden=true;frame.dataset.fallback='true';};
  scopeFor(root)?.listen(image,'error',fallback);
  if(image.complete&&!image.naturalWidth)fallback();
}
