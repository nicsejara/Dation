"""T10 projections/joins of immutable published facts, never a second producer."""
import csv
import io
import json
from fastapi import HTTPException
from app.results import contracts as c
from app.results.canonical import canonical_tree, canonical_bytes
from app.services import result_package_service as packages, result_artifact_service as artifacts
from app.platform.exports import text as export_text


def binding(package):
    return canonical_tree(c.ResultBinding(run_id=package.decision.run_id,
        result_fingerprint=package.fingerprints.result_fingerprint))


async def delivery(package, data, dataset_id):
    descriptor = next((d for d in package.details if d.dataset_id == dataset_id), None)
    if descriptor is None:
        raise HTTPException(404, 'Dataset not found')
    return await artifacts.dataset(descriptor.data, data['artifacts'])


async def primary_visual(ctx, run_id, fingerprint):
    package, data = await packages.snapshot(ctx, run_id, fingerprint)
    projection = package.primary_visual.projection
    if isinstance(projection, c.ReferenceDataset):
        projection = (await artifacts.dataset(projection, data['artifacts']))[0]
    return {'provenance': binding(package), 'projection': canonical_tree(projection)}


async def visual_entity(ctx, run_id, fingerprint, graph_node_id):
    package,data=await packages.snapshot(ctx,run_id,fingerprint)
    index=next((p for p in package.evidence.parts if p.dataset_id=='sankey-entity-index'),None)
    if index is None:raise HTTPException(404,'Visual entity index not available')
    for offset in range(0,index.row_count,100):
        for row in await artifacts.dataset(index,data['artifacts'],offset=offset,limit=100):
            if row['facts'].get('graph_node_id')==graph_node_id:
                return {'provenance':binding(package),'selection':{'graph_node_id':graph_node_id,
                    'entity_type':row['entity_type'],'entity_id':row['entity_id'],**row['facts']}}
    raise HTTPException(404,'Visual entity not found')


async def transport_publication(ctx, package, data):
    """D2 inherits exact parent facts. No latest-Run or Case lookup."""
    source = package.source_transport_plan
    if source is not None:
        parent, parent_data = await packages.snapshot(ctx, source.run_id, source.result_fingerprint)
        if parent.result_schema != 'transport_plan_v1' or parent.context.workspace_id != package.context.workspace_id or parent.context.case_id != package.context.case_id:
            raise HTTPException(409, 'UPSTREAM_BINDING_ERROR')
    else:
        parent, parent_data = package, data
    return parent,parent_data


async def _trip(ctx, package, data, trip_id):
    parent,parent_data=await transport_publication(ctx,package,data)
    # Existing immutable indexes cover evidence identities, not raw Trip rows.
    # Read bounded chunks server-side; return only the selected certified row.
    descriptor = next(d for d in parent.details if d.dataset_id == 'plan')
    for offset in range(0, descriptor.data.row_count, 100):
        for row in await artifacts.dataset(descriptor.data, parent_data['artifacts'], offset=offset, limit=100):
            if row['trip_id'] == trip_id:
                return {'provenance': binding(parent), 'trip': row}
    raise HTTPException(409, 'PUBLISHED_TRIP_MISSING')


async def entity(ctx, run_id, fingerprint, entity_type, entity_id):
    package, data = await packages.snapshot(ctx, run_id, fingerprint)
    selected = await packages.entity(ctx, run_id, fingerprint, entity_type, entity_id)
    emitted = canonical_tree(await artifacts.dataset(package.evidence.reason_emissions, data['artifacts'], entity=(entity_type, entity_id)))
    reasons = [r for r in emitted if r['emission_id'] in selected['entity']['reason_refs']]
    result = {**selected, 'reasons': reasons}
    if entity_type == 'TRIP':
        result['transport'] = await _trip(ctx, package, data, entity_id)
        if package.result_schema == 'day_scheduling_v1':
            rows = await delivery(package, data, 'schedule')
            result['schedule'] = next((r for r in rows if r.get('trip_id') == entity_id), None)
            if result['schedule'] is None:
                raise HTTPException(409, 'PUBLISHED_SCHEDULE_MISSING')
    if len(canonical_bytes(result)) > c.SELECTED_ENTITY_MAX_BYTES:
        raise HTTPException(413, 'SELECTED_ENTITY_BUDGET_EXCEEDED')
    return result


async def resource_capacities(ctx, run_id, fingerprint):
    """Capacity facts are already certified by T7; do not consult raw inputs."""
    package, data = await packages.snapshot(ctx, run_id, fingerprint)
    if package.result_schema != 'transport_plan_v1':
        raise HTTPException(409, 'UNSUPPORTED_RESULT_SCHEMA')
    proof = next(p for p in package.evidence.parts if p.dataset_id == 'engine-evidence')
    rows = await artifacts.dataset(proof, data['artifacts'])
    capacities = {}
    for shard in rows:
        for constraint in shard['constraints']:
            if constraint['code'] == 'CANDIDATE_ELIGIBILITY':
                facts = constraint['facts']
                resource_id = facts['resource_id']
                value = {dim: facts['guaranteed_' + dim] for dim in package.context.active_dimensions}
                if resource_id in capacities and capacities[resource_id] != value:
                    raise HTTPException(409, 'PUBLISHED_CAPACITY_INCONSISTENT')
                capacities[resource_id] = value
    return {'provenance': binding(package), 'capacities': capacities}


async def analysis_status(ctx, run_id, fingerprint):
    package, data = await packages.snapshot(ctx, run_id, fingerprint)
    part = next((p for p in package.evidence.parts if p.dataset_id == 'analysis-status'), None)
    if part is None:
        return {'provenance': binding(package), 'status': package.alternatives_state}
    rows = await artifacts.dataset(part, data['artifacts'])
    return {'provenance': binding(package), 'status': rows[0]['facts']['alternatives_status']}


async def export(ctx, run_id, fingerprint, format):
    package, data = await packages.snapshot(ctx, run_id, fingerprint)
    provenance = binding(package)
    if format == 'json':
        # Every authorized manifest entry must resolve, including evidence,
        # alternatives and AI base. Never label a partial envelope complete.
        resolved = {}
        for ref in package.artifact_manifest.artifacts:
            row = next(r for r in data['artifacts'] if r['id'] == str(ref.artifact_id))
            resolved[str(ref.artifact_id)] = json.loads(await artifacts.read(row))
        payload = {'schema_version': 'complete_decision_export_v1', 'complete': True,
            'provenance': provenance, 'package': canonical_tree(package), 'artifacts': resolved}
        if package.source_transport_plan is not None:
            parent,parent_data=await transport_publication(ctx,package,data)
            parent_artifacts={row['id']:json.loads(await artifacts.read(row)) for row in parent_data['artifacts']}
            payload['upstream']={'provenance':binding(parent),'package':canonical_tree(parent),'artifacts':parent_artifacts}
        return 'Decision_Summary.json', canonical_bytes(payload), 'application/json'
    descriptor = package.exports.csv
    if not descriptor.available or descriptor.rows is None:
        raise HTTPException(409, 'EXPORT_NOT_AVAILABLE')
    rows = await artifacts.dataset(descriptor.rows, data['artifacts'])
    if package.result_schema=='transport_plan_v1':
        trips={trip['trip_id']:trip for trip in await delivery(package,data,'plan')}
        projected=[]
        for row in rows:
            trip=trips.get(row['trip_id'])
            if trip is None:raise HTTPException(409,'PUBLISHED_TRIP_MISSING')
            # The export projection remains the only row/allocation/cost driver.
            # Join display columns already certified on that exact published
            # Trip. Never rebuild rows or apportion its cost over allocations.
            fields={**{'guaranteed_capacity_'+dim:trip['guaranteed_capacity'][dim] for dim in package.context.active_dimensions},
                **{'utilization_'+dim:trip['utilization'][dim] for dim in package.context.active_dimensions},
                'cost_model':trip['estimated_cost']['cost_model'] if trip['estimated_cost'] else None,'reason_codes':trip['reason_codes']}
            projected.append({**row,**fields})
        rows=projected
    rows=[{**row,**provenance} for row in rows]
    # Schema's wire fields, exactly once per certified projection row. Nested
    # typed values are serialized, never flattened through business formulas.
    headers = list(rows[0]) if rows else []
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\r\n')
    writer.writerow(headers)
    def cell(value):
        if isinstance(value,(dict,list,tuple)):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
        formatted=export_text(value)
        # Match Dation's spreadsheet formula protection for text; signed integer
        # schedule margins remain exact numeric facts rather than formula text.
        return "'"+formatted if isinstance(value,str) and formatted[:1] in {'=','+','@','-'} else formatted
    for row in rows:
        writer.writerow([cell(row[key]) for key in headers])
    filename = 'Transport_Plan.csv' if package.result_schema == 'transport_plan_v1' else 'Day_Schedule.csv'
    return filename, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8'
