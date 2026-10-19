// Workspace presentation only. Engine inputs and historical run values stay canonical.
export function workspaceLocale(workspace={}){try{return new Intl.Locale((workspace.language||'es')+'-'+(workspace.country||'AR')).toString();}catch{return 'es-AR';}}
export function workspaceDate(value,workspace={},options={dateStyle:'medium',timeStyle:'short'}){
 if(!value||!Number.isFinite(new Date(value).getTime()))return 'Sin registro';
 try{return new Intl.DateTimeFormat(workspaceLocale(workspace),{...options,timeZone:workspace.timezone||'UTC'}).format(new Date(value));}
 catch{return new Intl.DateTimeFormat('es-AR',{...options,timeZone:'UTC'}).format(new Date(value));}
}
export function workspaceNumber(value,workspace={},options={}){return new Intl.NumberFormat(workspaceLocale(workspace),options).format(value);}
