"""Bounded activity projections: identities are recorded, never inferred from owners."""
from fastapi import HTTPException
from app.platform.identity import platform_call

ACTIONS={'workspace.created':'creó el workspace','workspace.legacy_claimed':'recuperó el acceso al workspace',
 'workspace.settings_updated':'actualizó la configuración del workspace','member.invited':'invitó a una persona al workspace',
 'member.joined':'se unió al workspace','member.invitation_revoked':'revocó una invitación',
 'member.role_changed':'cambió un rol de acceso','member.disabled':'deshabilitó una membresía',
 'member.enabled':'reactivó una membresía','member.updated':'actualizó una membresía',
 'dataset.uploaded':'cargó un dataset','dataset.validated':'validó un dataset','dataset.archived':'archivó un dataset',
 'dataset.restored':'restauró un dataset','dataset.deleted':'eliminó un dataset',
 'decision_case.created':'creó un Decision Case','decision_case.archived':'archivó el caso',
 'decision_case.restored':'restauró el caso','decision_case.renamed':'cambió el nombre del caso',
 'decision.assigned':'actualizó los responsables de','decision.approved':'aprobó',
 'run.queued':'solicitó ejecutar','run.started':'inició la ejecución de','run.completed':'completó',
 'run.failed':'registró un error en','decision.submitted':'dejó para revisión','export.generated':'generó una exportación de'}
NODES={'logistics_assignment':'Assignment','logistics_scheduling':'Scheduling','logistics_final_assignment':'Final Assignment'}

def project(event):
 actor=(event.get('actor') or {}).get('name') or ('El sistema' if event.get('metadata',{}).get('source')=='system' else 'Autor no registrado')
 action=ACTIONS.get(event['event_type'],'registró una acción')
 node=NODES.get(event.get('node_id'))
 if event['event_type'].startswith('run.') or event['event_type'] in {'decision.approved','decision.assigned','decision.submitted','export.generated'}:
  action+=' '+(node or 'la decisión')
 if event['event_type']=='decision.submitted':action='dejó '+(node or 'la decisión')+' para revisión'
 if event['event_type']=='dataset.validated' and event.get('metadata',{}).get('valid') is False:action='detectó problemas al validar un dataset'
 return {**event,'label':actor+' '+action}

async def snapshot(ctx,case_id=None,limit=5,before_time=None,before_id=None):
 data=await platform_call('platform_activity',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,
  'target_case_id':str(case_id) if case_id else None,'page_limit':limit,
  'before_time':before_time.isoformat() if before_time else None,'before_id':str(before_id) if before_id else None})
 return {'available':True,'items':[project(e) for e in data['items']],'next_cursor':data['next_cursor']}

async def home_activity(ctx):
 try:return await snapshot(ctx)
 except HTTPException as error:
  if error.status_code!=503:raise
  return {'available':False,'items':[],'error':'No se pudo cargar la actividad reciente.'}
