// Workspace presentation only. Engine inputs and historical run values stay canonical.
export function workspaceLocale(workspace={}){try{return new Intl.Locale((workspace.language||'es')+'-'+(workspace.country||'AR')).toString();}catch{return 'es-AR';}}
export function workspaceDate(value,workspace={},options={dateStyle:'medium',timeStyle:'short'}){
 if(!value||!Number.isFinite(new Date(value).getTime()))return 'Sin registro';
 try{return new Intl.DateTimeFormat(workspaceLocale(workspace),{...options,timeZone:workspace.timezone||'UTC'}).format(new Date(value));}
 catch{return new Intl.DateTimeFormat('es-AR',{...options,timeZone:'UTC'}).format(new Date(value));}
}
export function workspaceNumber(value,workspace={},options={}){return new Intl.NumberFormat(workspaceLocale(workspace),options).format(value);}
export function workspaceRelativeDate(value,workspace={},now=Date.now()){
 const stamp=new Date(value).getTime();if(!value||!Number.isFinite(stamp))return 'Sin registro';
 const seconds=(stamp-now)/1000,absolute=Math.abs(seconds);
 const [unit,size]=absolute<60?['second',1]:absolute<3600?['minute',60]:absolute<86400?['hour',3600]:absolute<604800?['day',86400]:['week',604800];
 return new Intl.RelativeTimeFormat(workspaceLocale(workspace),{numeric:'auto'}).format(Math.round(seconds/size),unit);
}
