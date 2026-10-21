import {describeFailure,responseFailure} from '../dispatch/recovery.mjs';
import {mountReceivedInvitations} from './invitations.mjs';
const root=document.querySelector('#auth-root');
const path=location.pathname;
function returnPath(){
 try{const url=new URL(new URLSearchParams(location.search).get('next')||'/app',location.origin);if(url.origin===location.origin&&(url.pathname==='/app'||url.pathname.startsWith('/app/')||url.pathname==='/upload'))return url.pathname+url.search;}catch{}
 return '/app';
}
const destination=returnPath();
const setupPath='/workspace-setup'+(destination==='/app'?'':'?next='+encodeURIComponent(destination));
const reset=path==='/recover'&&new URLSearchParams(location.search).get('step')==='password';
const mode=path==='/register'?'register':path==='/workspace-setup'?'workspace':path==='/recover'?(reset?'password':'recover'):'login';
const titles={login:'Ingresá a tu workspace',register:'Creá tu cuenta',recover:'Recuperá tu acceso',password:'Elegí una nueva contraseña',workspace:'Creá tu workspace'};
const descriptions={login:'Tus datos, decisiones y evidencia en un solo lugar.',register:'Empezá con un workspace para tu equipo.',recover:'Te enviaremos un enlace para cambiar tu contraseña.',password:'Usá al menos 10 caracteres.',workspace:'Configurá el espacio donde trabajará tu equipo.'};
function field(name,label,type='text',autocomplete='',value=''){
 const box=document.createElement('div');box.className='d-field';
 const title=document.createElement('label');title.className='d-label';title.htmlFor=name;title.textContent=label;
 const input=document.createElement('input');Object.assign(input,{id:name,name,type,required:true,autocomplete,value});input.className='d-input';input.maxLength=type==='password'?128:254;
 if(type==='password'&&mode!=='login')input.minLength=10;
 box.append(title,input);return box;
}
const h=document.createElement('h1');h.textContent=titles[mode];const intro=document.createElement('p');intro.textContent=descriptions[mode];
const form=document.createElement('form');form.autocomplete='on';
if(mode==='register'){form.append(field('first_name','Nombre','text','given-name'),field('last_name','Apellido','text','family-name'));}
if(['login','register','recover'].includes(mode))form.append(field('email','Email','email','email'));
if(['login','register','password'].includes(mode))form.append(field('password','Contraseña','password',mode==='login'?'current-password':'new-password'));
if(['register','password'].includes(mode))form.append(field('confirm_password','Confirmar contraseña','password','new-password'));
if(mode==='workspace'){
 form.append(field('name','Nombre de la empresa o workspace','text','organization'),field('country','País (código de dos letras)','text','country','AR'),field('timezone','Zona horaria','text','',Intl.DateTimeFormat().resolvedOptions().timeZone||'America/Argentina/Buenos_Aires'),field('currency','Moneda (código de tres letras)','text','','ARS'));
 form.elements.country.pattern='[A-Z]{2}';form.elements.currency.pattern='[A-Z]{3}';
}
const error=document.createElement('p');error.role='alert';error.id='auth-error';error.tabIndex=-1;
const status=document.createElement('p');status.role='status';status.setAttribute('aria-live','polite');
const submit=document.createElement('button');submit.type='submit';submit.className='d-button d-button--primary';submit.textContent={login:'Ingresar',register:'Crear cuenta',recover:'Enviar enlace',password:'Guardar contraseña',workspace:'Crear workspace'}[mode];
form.append(error,status,submit);
const links=document.createElement('nav');links.className='d-auth__links';links.setAttribute('aria-label','Opciones de acceso');
for(const [text,url] of mode==='login'?[['¿Olvidaste tu contraseña?','/recover'],['Crear cuenta','/register']]:[['Volver al ingreso','/login']]){const a=document.createElement('a');a.textContent=text;a.href=url;links.append(a);}
root.replaceChildren(h,intro,form,links);root.setAttribute('aria-busy','false');
if(mode==='workspace'){
 const incoming=document.createElement('section');incoming.className='team-incoming';incoming.hidden=true;form.before(incoming);
 const invites=mountReceivedInvitations(incoming,{onCount:count=>{if(count){form.hidden=true;intro.textContent='Tenés una invitación para sumarte a un equipo.';}}});
 window.addEventListener('pagehide',()=>invites.dispose(),{once:true});
}
if(new URLSearchParams(location.search).get('reason')==='session')status.textContent='Tu sesión venció. Volvé a ingresar; el trabajo guardado se conserva.';
if(mode==='login'&&new URLSearchParams(location.search).get('recovery')==='sent')status.textContent='Si la cuenta existe, recibirás un enlace para cambiar tu contraseña. Revisá tu correo y seguí las instrucciones.';
if(mode==='login'&&new URLSearchParams(location.search).get('password')==='updated')status.textContent='Tu contraseña fue actualizada. Ingresá con tu nueva contraseña.';
if(new URLSearchParams(location.search).has('error'))error.textContent='El enlace venció o se abrió en otro navegador. Solicitá uno nuevo desde este dispositivo.';
async function call(url,body={}){
 const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let data;try{data=await response.json();}catch{throw Object.assign(new Error('El servicio de acceso no está disponible. Reintentá en unos instantes.'),{status:response.status});}if(!response.ok)throw responseFailure(response,data,{auth:mode==='login'});return data;
}
form.addEventListener('submit',async event=>{
 event.preventDefault();if(!form.reportValidity())return;
 const body=Object.fromEntries(new FormData(form));error.textContent='';status.textContent='';submit.disabled=true;submit.setAttribute('aria-busy','true');
 try{
  if('confirm_password'in body&&body.password!==body.confirm_password)throw new Error('Las contraseñas no coinciden.');
  const data=await call('/auth/'+(mode==='workspace'?'workspace':mode),body);
  if(mode==='recover'){location.replace('/login?recovery=sent');return;}
  if(mode==='password'){location.replace('/login?password=updated');return;}
  if(['login','workspace'].includes(mode)){location.replace(destination);return;}
  status.textContent=data.message;
  if(mode==='register'){
   try{const session=await call('/auth/session');if(session.access_token){location.replace(session.membership?destination:setupPath);return;}}catch{}
  }
 }catch(exc){const state=describeFailure(exc,{auth:mode==='login'});error.textContent=['auth','disconnected','timeout','permission'].includes(state.kind)?state.message:exc.message;error.focus();}finally{submit.disabled=false;submit.removeAttribute('aria-busy');}
});
if((mode==='login'&&!new URLSearchParams(location.search).has('recovery')&&!new URLSearchParams(location.search).has('password'))||mode==='workspace'){
 try{
  const session=await call('/auth/session');
  if(mode==='login')location.replace(session.membership?destination:setupPath);
  else if(session.membership)location.replace(destination);
 }catch(exc){if(mode==='workspace'){if(exc.status===401)location.replace('/login');else{error.textContent=exc.message;submit.disabled=true;}}else if(exc.status!==401)error.textContent=exc.message;}
}
