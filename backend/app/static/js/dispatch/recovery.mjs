// Shared user-facing recovery language. Never retries a write automatically.
export function describeFailure(error,{kind,auth=false}={}){
 kind=kind||error?.kind||(error?.status===401?(auth?'auth':'session'):error?.status===403?'permission':error?.status===422?'validation':[408,504].includes(error?.status)||error?.name==='TimeoutError'?'timeout':error instanceof TypeError?'disconnected':'unavailable');
 const patterns={
  auth:['No pudimos iniciar sesión','Revisá tu email y contraseña. Si no la recordás, solicitá un enlace para recuperarla.'],
  session:['Tu sesión venció','Ingresá nuevamente para continuar. El trabajo guardado se conserva.'],
  permission:['Tu acceso no permite esta acción','Consultá con un administrador del workspace para revisar tu rol o la disponibilidad del DDA.'],
  upload:['No se pudo guardar el archivo','Conservá el CSV y reintentá. Si la carga quedó interrumpida, revisala en Data Hub antes de descartarla.'],
  run:['La ejecución terminó con error','La evidencia anterior se conserva. Revisá los datos y volvé a configurar la decisión.'],
  timeout:['La respuesta está demorando','Reintentá consultar el estado. Una demora no confirma que una carga o ejecución haya fallado.'],
  disconnected:['No pudimos conectar con Dation','Revisá tu conexión y reintentá. Los datos ya guardados se conservan.'],
  validation:['Revisá los datos','Corregí los campos o el formato indicado antes de volver a intentar.'],
  source:['Falta la decisión de origen','Abrí Assignment y aprobá una corrida vigente para continuar con Scheduling.'],
  stale:['Esta decisión requiere actualizarse','La aprobación de origen cambió. Conservá la evidencia anterior y configurá una nueva corrida con el origen vigente.'],
  unavailable:['No se pudo completar la solicitud','Reintentá en unos instantes. Tu trabajo guardado se conserva.']};
 const [title,message]=patterns[kind]||patterns.unavailable;
 return {kind,title,message,errorDetail:typeof error?.message==='string'?error.message:null};
}
export function responseFailure(response,data,{auth=false}={}){
 const detail=typeof data?.detail==='string'?data.detail:null;
 const e=Object.assign(new Error(detail||'Revisá los datos ingresados e intentá nuevamente.'),{status:response.status});
 if(auth&&response.status===401)e.kind='auth';
 if(response.status===413)e.kind='upload';
 return e;
}
