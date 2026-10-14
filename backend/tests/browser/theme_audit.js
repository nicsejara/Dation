(selector = '.view.is-active') => {
  const view = document.querySelector(selector || '.view.is-active');
  const rgb = value => {
    const found = value.match(/^rgba?\(([^)]+)\)$/);
    if (!found) throw Error('Unsupported computed color: '+value);
    const values = found[1].split(',').map(Number);
    return [...values.slice(0,3), values.length===4?values[3]:1];
  };
  const over = (front,back) => front.slice(0,3).map((x,i)=>x*front[3]+back[i]*(1-front[3]));
  const luminance = color => color.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
  const ratio = (a,b) => (Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
  const backgrounds = element => {
    const chain=[];
    for(let current=element;current;current=current.parentElement) chain.unshift(current);
    let candidates=[[255,255,255]];
    for(const current of chain) {
      const style=getComputedStyle(current);
      const solid=rgb(style.backgroundColor);
      candidates=candidates.map(bg=>over(solid,bg));
      const stops=(style.backgroundImage.match(/rgba?\([^)]+\)/g)||[]).map(rgb);
      if(!stops.length)continue;
      if(style.backgroundImage.startsWith('linear-gradient') && stops.length>1) {
        const samples=stops.slice(1).flatMap((last,i)=>Array.from({length:257},(_,k)=>last.map((v,j)=>stops[i][j]+(v-stops[i][j])*k/256)));
        candidates=candidates.flatMap(bg=>samples.map(color=>over(color,bg)));
      } else {
        // Radial positions are deliberately conservative: inspect every end color.
        candidates=candidates.flatMap(bg=>[bg,...stops.map(color=>over(color,bg))]);
      }
    }
    return candidates;
  };
  const walker=document.createTreeWalker(view,NodeFilter.SHOW_TEXT);
  let node,count=0,minimum=Infinity;
  const failures=[];
  while(node=walker.nextNode()) {
    const content=node.textContent.trim(),el=node.parentElement;
    if(!content||el.closest('svg,script,style,[aria-hidden="true"],button:disabled:not(.decision-advanced-option)'))continue;
    const bounds=el.getBoundingClientRect(),style=getComputedStyle(el);
    if(!bounds.width||!bounds.height||style.visibility!=='visible')continue;
    // Closed native details omit their body from layout.
    const details=el.closest('details:not([open])');
    if(details&&!el.closest('summary'))continue;
    const foreground=rgb(style.color), bgs=backgrounds(el);
    const contrast=Math.min(...bgs.map(bg=>ratio(over(foreground,bg),bg)));
    const font=parseFloat(style.fontSize),weight=parseFloat(style.fontWeight);
    const threshold=font>=24||(font>=18.66&&weight>=700)?3:4.5;
    count++;minimum=Math.min(minimum,contrast);
    if(contrast<threshold)failures.push({text:content.slice(0,90),element:el.className||el.tagName,contrast,threshold,color:style.color});
  }
  // Native values and placeholders have no text nodes. Audit their rendered roles too.
  for(const el of view.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]),select,textarea')) {
    const bounds=el.getBoundingClientRect(),style=getComputedStyle(el);
    if(el.disabled||!bounds.width||!bounds.height||style.visibility!=='visible')continue;
    const placeholder=el.tagName==='INPUT'&&!el.value&&el.placeholder;
    const foreground=rgb(placeholder?getComputedStyle(el,'::placeholder').color:style.color);
    const contrast=Math.min(...backgrounds(el).map(bg=>ratio(over(foreground,bg),bg)));
    count++;minimum=Math.min(minimum,contrast);
    if(contrast<4.5)failures.push({element:el.tagName,control:placeholder?'placeholder':'value',contrast,threshold:4.5});
  }
  const hero=view.querySelector('.d-page-hero');
  const geometry=el=>{const b=el.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,right:b.right,bottom:b.bottom};};
  return {textCount:count,minimumContrast:minimum,failures,hero:hero?geometry(hero):null,
    overflow:document.documentElement.scrollWidth>innerWidth,
    legacyBoundary:!!view.closest('[data-dation-surface="legacy-light"]'),
    scheme:getComputedStyle(view).colorScheme,
    cards:[...view.querySelectorAll('.d-home__asset,.dda-landing__section,.dda-landing__step,.dda-landing__node,.dda-landing__summary-card,.dda-landing__faq-grid details,.dispatch-pro-file-card,.dispatch-pro-validation-row,.dispatch-pro-inline-library-row,.d-workflow-action-bar,.assignment-section,.assignment-choice-card,.decision-advanced-option,.scheduling-rule-builder')].map(el=>({background:getComputedStyle(el).backgroundColor,...geometry(el)}))};
}
