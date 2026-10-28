"""Frozen real T7/T9 bundles for T10 consumer tests (no solver in a reader)."""
import copy
import json
from pathlib import Path
from app.results.canonical import artifact_bytes, canonical_tree
from app.platform.context import RequestContext

FIXTURE=json.loads((Path(__file__).parent/'fixtures/ultimate/consumers.json').read_text())
ALTERNATIVES=json.loads((Path(__file__).parent/'fixtures/ultimate/consumer_alternatives.json').read_text())

def fixtures():
    datasets={};blobs={}
    for key,item in copy.deepcopy({**FIXTURE,'alternatives':ALTERNATIVES}).items():
        package=item['package'];rid=package['decision']['run_id'];fp=package['fingerprints']['result_fingerprint'];rows=[];offsets={}
        for ref in package['artifact_manifest']['artifacts']:
            body=item['artifacts'][ref['artifact_id']];blob=artifact_bytes(body);blobs[ref['artifact_id']]=blob
            row={**ref,'id':ref['artifact_id'],'publication_state':'READY','result_fingerprint':fp,'storage_bucket':'dda-inputs'};row.pop('artifact_id')
            row['storage_path']=f"{row['workspace_id']}/runs/{rid}/{row['kind'].lower()}/{row['part_key']}/{row['content_sha256']}.json"
            values=body['rows'];dataset=body['dataset_id'];offset=offsets.get(dataset,0);offsets[dataset]=offset+len(values)
            row['producer_metadata']={'retrieval_index':{'version':1,'row_offset':offset,'row_count':len(values)}}
            row['lookup_keys']=['/'.join([r['entity_type'],r['entity_id']]) for r in values if isinstance(r,dict) and 'entity_type' in r]
            rows.append(row)
        datasets[rid]={'run':{'id':rid,'result_json':package,'approved_at':None},'artifacts':rows,'overlay':{
            'run_id':rid,'result_fingerprint':fp,'approval_allowed':True,'approval_blockers':[],'freshness':'CURRENT'}}
    ctx=RequestContext('10000000-0000-4000-8000-000000000001',FIXTURE['d1']['package']['context']['workspace_id'],'admin')
    return ctx,datasets,blobs
