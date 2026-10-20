"""Product metadata and destination rules shared with the browser, not business state."""
import json
from pathlib import Path

REGISTRY=json.loads((Path(__file__).resolve().parents[1]/'static/contracts/foundation-v2.json').read_text())

def objective_presentation(value):
    identifier=REGISTRY['objectiveAliases'].get(value,value)
    return {'id':identifier,'label':REGISTRY['objectives'].get(identifier,identifier)} if identifier else None

def resolve_node_destination(node_id,node):
    if not REGISTRY['decisions'].get(node_id,{}).get('implemented') or node.get('status') in {'coming_soon','locked','needs_data'}:return None
    approved=node.get('approved_run_id') or (node.get('approved_run') or {}).get('id') or (node.get('run_id') if node.get('status')=='approved' else None)
    latest=node.get('latest_run_id') or (node.get('latest_run') or {}).get('id') or node.get('run_id')
    current=node.get('status') in {'approved','review','running','error'} and node.get('approval_current',bool(approved))
    matches={'approved':current and bool(approved),'candidate':node.get('status') in {'review','running','stale','error'} and bool(latest),'available':node.get('status')=='available'}
    rule=next((rule for rule in REGISTRY['destinationRules'] if matches[rule['when']]),None)
    return {'view':rule['view'],'node_id':node_id,'run_id':approved if rule['run']=='approved' else latest if rule['run']=='latest' else None} if rule else None


def case_context(value):
    identifier=value.get('id') or value.get('case_id')
    return {'caseId':identifier,'friendlyId':'DC-'+str(identifier)[:8].upper() if identifier else None,
        'label':value.get('label') or None,'dda':value.get('dda') or value.get('domain') or 'logistics',
        'status':value.get('status') or 'active','currentNode':value.get('current_step') or value.get('node_id'),
        'progress':value.get('progress')}
