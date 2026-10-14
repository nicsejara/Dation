() => {
  const element=document.activeElement;
  if(!element||element===document.body)return {skip:true};
  const style=getComputedStyle(element),rect=element.getBoundingClientRect();
  const points=[[.5,.5],[.2,.2],[.8,.8]].map(([x,y])=>document.elementFromPoint(rect.x+rect.width*x,rect.y+rect.height*y));
  return {
    skip:false,tag:element.tagName,text:(element.getAttribute('aria-label')||element.textContent||'').trim().slice(0,100),
    visibleFocus:element.matches(':focus-visible'),outline:style.outlineStyle,width:parseFloat(style.outlineWidth),color:style.outlineColor,
    occluded:points.some(hit=>!hit||!element.contains(hit)),
    outside:rect.left<-.5||rect.right>innerWidth+.5||rect.top<-.5||rect.bottom>innerHeight+.5,
    rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},
    identity:element.outerHTML.slice(0,280),
  };
}
