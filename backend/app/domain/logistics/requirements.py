"""Input requirements and semantic read identities from published snapshots."""
from app.domain.logistics.data_contracts import compile_contract, NORMALIZER_VERSION
from app.results.canonical import canonical_bytes, content_sha256

def hash_value(value): return content_sha256(canonical_bytes(value))

def input_requirements(definition, model, entries, policy):
    indexed={e['slot_key']:e for e in entries};missing=[]
    economic=policy['primary_goal'] in ('MINIMIZE_COST','BALANCED') or any(p['kind']=='COST' and float(p['weight'])>0 for p in policy.get('preferences',[]))
    for slot in definition.required_inputs:
        item=indexed.get(slot)
        if not item:
            missing.append({'code':'MISSING_INPUT','slot':slot,'label':'Demanda' if slot=='transport_demand' else 'Recursos'});continue
        contract=compile_contract(model,slot)
        if item.get('contract_hash')!=contract.contract_hash or item.get('normalizer_version')!=NORMALIZER_VERSION or item.get('model_version_id',model['id'])!=model['id'] or item.get('record_count',0)<=0:
            missing.append({'code':'INCOMPATIBLE_INPUT','slot':slot,'label':'Input incompatible con la Model Version'});continue
        summary=item.get('summary') or {}
        if summary.get('unknown_availability_count',0):missing.append({'code':'UNKNOWN_AVAILABILITY','slot':slot,'label':'Disponibilidad requerida desconocida'})
        if economic and summary.get('unknown_cost_count',0):missing.append({'code':'UNKNOWN_COST','slot':slot,'label':'Costos requeridos por el objetivo desconocidos'})
    return missing

def read_identity(definition, context, entries, nodes, node_policy=None):
    indexed={e['slot_key']:e for e in entries};result={}
    for key in definition.read_set:
        if key in ('transport_demand','transport_resources','scheduling_enrichment'):
            item=indexed.get(key);result[key]=None if item is None else {k:item[k] for k in ('canonical_sha256','contract_hash','normalizer_version')}
        elif key=='model':result[key]=context['logistics_model_version_id']
        elif key=='horizon':result[key]=[context['planning_start'],context['planning_end']]
        elif key=='case_policy':result[key]=context['case_policy_hash']
        elif key=='node_policy':result[key]=node_policy or context['case_policy_hash']
        elif key.startswith('approved:'):
            upstream=nodes.get(key.split(':',1)[1]) or {};result[key]=upstream.get('approved_run_id') if upstream.get('node_state')=='APPROVED' else None
        else:raise ValueError('Unrecognized read set')
    return result
