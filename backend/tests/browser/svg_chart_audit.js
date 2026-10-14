(selector) => {
  const root=document.querySelector(selector);
  const value=text=>(text.match(/[\d.]+/g)||[]).map(Number).slice(0,3);
  const luminance=c=>c.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
  const ratio=(a,b)=>(Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
  const surface=value(getComputedStyle(root.closest('.dispatch-panel')).backgroundColor);
  const tooltip=value(getComputedStyle(root).getPropertyValue('--color-surface-overlay').trim().replace(/^#([0-9a-f]{6})$/i,(_,hex)=>'rgb('+[0,2,4].map(i=>parseInt(hex.slice(i,i+2),16)).join(',')+')'));
  const failures=[];let minimum=Infinity,count=0;
  for(const text of root.querySelectorAll('svg text')){
    const box=text.getBoundingClientRect(),style=getComputedStyle(text);
    if(!text.textContent.trim()||!box.width||!box.height||style.visibility==='hidden')continue;
    let hidden=false;for(let node=text;node&&node!==root;node=node.parentElement)if(getComputedStyle(node).opacity==='0')hidden=true;
    if(hidden)continue;
    const fg=value(style.fill);if(fg.length!==3)continue;
    const contrast=Math.min(ratio(fg,surface),ratio(fg,tooltip));
    minimum=Math.min(minimum,contrast);count++;
    if(contrast<4.5)failures.push({text:text.textContent,contrast,fill:style.fill});
  }
  return {count,minimum,failures};
}
