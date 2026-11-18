"""Explicit v2 compiler. v1 descriptor and bytes remain on the original path."""
import csv,io
from uuid import UUID
from app.models.ultimate_foundation import parse_configuration
from app.results.canonical import canonical_bytes,canonical_tree,content_sha256
from .data_contracts import DataContract,SemanticField,_compile_contract_v1,REGISTRY_VERSION,entities_for
from .physical import normalize_catalog

REGISTRY_V2='SAGA10_DOMAIN_V2'
NORMALIZER_V2='DATION_CARGO_INPUT_NORMALIZER_V2'


def legacy_version(version,config):
    value=config.model_dump(mode='json',exclude={'cargo','consolidation_permitted','resource_categories'});value['version']=1
    return {**version,'config_jsonb':value,'contract_registry_version':REGISTRY_VERSION}


def compile_v2(version,entity,registry=None):
    if entity not in entities_for(version) or registry not in (None,REGISTRY_V2) or version.get('contract_registry_version',REGISTRY_V2)!=REGISTRY_V2:
        raise ValueError('Entidad o registry incompatible con el modelo v2.')
    config=parse_configuration(version['config_jsonb']);catalog=normalize_catalog(config.cargo,config.active_dimensions)
    if entity=='order_lines':
        fields=[]
        for key,type_,example,unit,validation in [('order_id','IDENTIFIER','ORD-001',None,{'max_length':128}),
          ('presentation_id','IDENTIFIER',next(iter(catalog)),None,{'max_length':128}),
          ('quantity','DECIMAL','1','presentation.quantity_unit',{'positive':True,'scale':3,'integer_when':'DISCRETE','increment_from':'catalog_snapshot'})]:
            fields.append(SemanticField(semantic_key=key,semantic_entity=entity,type=type_,unit=unit,required_for=('INPUT_SCHEMA',),validation=validation,engine_role='LINE_ALLOCATION',public_header=key,examples=(example,)))
        base=_compile_contract_v1(legacy_version(version,config),'transport_demand')
    else:
        base=_compile_contract_v1(legacy_version(version,config),entity);fields=list(base.fields)
        if entity=='transport_demand' and config.cargo.input_mode=='catalog':
            fields=[f for f in fields if not f.semantic_key.startswith('demand_') and f.semantic_key!='compatibility_groups']
        if entity=='transport_resources' and config.resource_categories:
            fields.append(SemanticField(semantic_key='resource_category',semantic_entity=entity,type='ENUM',unit=None,required_for=('RESOURCE_ELIGIBILITY',),
                validation={'values':list(config.resource_categories)},engine_role='RESOURCE_ELIGIBILITY',public_header='resource_category',examples=(config.resource_categories[0],)))
    catalog_wire=canonical_tree(catalog)
    rules={**dict(base.rules),'model':canonical_tree(config),'input_mode':config.cargo.input_mode,'required_entities':list(entities_for(version)),
        'catalog_snapshot':catalog_wire,'catalog_hash':content_sha256(canonical_bytes(catalog_wire)),
        'line_overrides':'FORBIDDEN','duplicate_lines':'REJECT_ORDER_PRESENTATION','physical_precision':'EXPLICIT_COEFFICIENTS_AND_ALLOCATION_INCREMENT',
        'split_intersection':'MODEL_AND_ORDER','quantity_source':'ORDER_LINES_ONLY' if config.cargo.input_mode=='catalog' else 'DIRECT_ONLY',
        'geometry_scope':'SCALAR_CAPACITY_NOT_3D_PACKING','solver_limits':{'orders':500,'lines':500,'resources':50}}
    body=dict(contract_id=entity+'_v2',schema_version=entity+'_v2',registry_version=REGISTRY_V2,model_version_id=str(UUID(str(version['id']))),
        configuration_hash=version['config_hash'],semantic_entity=entity,fields=[f.model_dump(mode='json') for f in fields],rules=rules,normalizer_version=NORMALIZER_V2)
    return DataContract(**body,contract_hash=content_sha256(canonical_bytes(body)))


def template_v2(contract):
    if contract.semantic_entity=='transport_resources':
        # Same descriptor fields, source conditions and five-row logic as v1.
        from .data_contracts import template_csv,REGISTRY_VERSION
        proxy=contract.model_copy(update={'registry_version':REGISTRY_VERSION})
        return template_csv(proxy)
    out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');writer.writerow([f.public_header for f in contract.fields])
    presentations=list(contract.rules['catalog_snapshot'])
    for i in range(5):
        values={f.public_header:f.examples[0] for f in contract.fields};values['order_id']='ORD-'+str(i+1).zfill(3)
        if contract.semantic_entity=='order_lines':values['presentation_id']=presentations[i%len(presentations)]
        writer.writerow([values[f.public_header] for f in contract.fields])
    return out.getvalue().encode('utf-8')
