"""T4 exact, versioned input descriptors. No engine, fuzzy mapping or graph."""
import csv
import io
from typing import Literal
from uuid import UUID

from pydantic import Field
from app.domain.logistics.base import ContractModel, SHA256
from app.domain.logistics.units import QUANTITY_SCALES
from app.models.ultimate_foundation import LogisticsModelConfigurationV1
from app.results.canonical import canonical_bytes, content_sha256

REGISTRY_VERSION='ULTIMATE_DOMAIN_V1'
NORMALIZER_VERSION='DATION_INPUT_NORMALIZER_V1'
ENTITIES=('transport_demand','transport_resources')
MAX_BYTES=10*1024*1024
MAX_ROWS=10000


class SemanticField(ContractModel):
    semantic_key: str
    semantic_entity: Literal['transport_demand','transport_resources']
    type: Literal['IDENTIFIER','DECIMAL','INTEGER','DATE','BOOLEAN','ENUM','ID_LIST','LANES']
    unit: str | None
    required_for: tuple[str,...]
    used_by: tuple[str,...] = ('logistics_assignment','logistics_scheduling')
    validation: dict
    engine_role: str
    public_header: str
    examples: tuple[str,...]
    nullable: bool = False
    applies_when: dict = Field(default_factory=dict)


class DataContract(ContractModel):
    contract_id: str
    schema_version: str
    registry_version: str
    model_version_id: UUID
    configuration_hash: SHA256
    semantic_entity: Literal['transport_demand','transport_resources']
    fields: tuple[SemanticField,...]
    rules: dict
    normalizer_version: str = NORMALIZER_VERSION
    contract_hash: SHA256


def compile_contract(model_version,semantic_entity,registry_version=REGISTRY_VERSION):
    """The argument is a persisted published Version, never a browser schema."""
    if semantic_entity not in ENTITIES or registry_version!=REGISTRY_VERSION:raise ValueError('Unknown semantic entity/registry')
    if model_version.get('contract_registry_version',registry_version)!=registry_version:raise ValueError('Published Model uses an unsupported registry')
    config=LogisticsModelConfigurationV1.model_validate(model_version['config_jsonb'])
    model_id=UUID(str(model_version['id']));fields=[]
    def add(key,type,example,*,unit=None,nullable=False,when=None,required=('INPUT_SCHEMA',),role='INPUT',**validation):
        fields.append(SemanticField(semantic_key=key,semantic_entity=semantic_entity,type=type,unit=unit,
            required_for=required,validation=validation,engine_role=role,public_header=key,examples=(example,),nullable=nullable,applies_when=when or {}))
    if semantic_entity=='transport_demand':
        for key,example in [('order_id','ORD-001'),('origin_id','ORIGIN-01'),('destination_id','DEST-01')]:add(key,'IDENTIFIER',example,max_length=128)
        add('distance_km','DECIMAL','500',unit='km',positive=True,scale=3)
        add('ready_date','DATE','2026-11-02',format='YYYY-MM-DD');add('delivery_due_date','DATE','2026-11-06',format='YYYY-MM-DD')
        add('priority','ENUM','MEDIUM',values=['HIGH','MEDIUM','LOW']);add('split_allowed','BOOLEAN','true' if config.split_permitted else 'false',values=['true','false'])
        for dim in config.active_dimensions:add('demand_'+dim,'DECIMAL','10',unit=dim,minimum=0,scale=QUANTITY_SCALES[dim])
    else:
        add('resource_id','IDENTIFIER','RES-001',max_length=128)
        add('source','ENUM',config.allowed_sources[0],values=list(config.allowed_sources))
        add('lanes','LANES','[["ORIGIN-01","DEST-01"]]',format='JSON array of [origin_id,destination_id] pairs',max_items=100)
        for dim in config.active_dimensions:
            add('guaranteed_'+dim,'DECIMAL','20',unit=dim,positive=True,scale=QUANTITY_SCALES[dim])
            add('maximum_'+dim,'DECIMAL','',unit=dim,nullable=True,positive=True,scale=QUANTITY_SCALES[dim])
        if 'OWN' in config.allowed_sources:
            add('units_available','INTEGER','1',unit='units',nullable=True,when={'source':'OWN'},required=('OWN_FEASIBILITY',),minimum=0)
            add('base_origin_id','IDENTIFIER','ORIGIN-01',when={'source':'OWN'},max_length=128)
            add('operating_cost_per_km','DECIMAL','1',unit=config.currency_policy.currency+'/km',nullable=True,when={'source':'OWN'},required=('ECONOMIC_GOAL',),minimum=0,scale=6)
        if 'EXTERNAL' in config.allowed_sources:
            add('services_available','INTEGER','1',unit='horizon_services',nullable=True,when={'source':'EXTERNAL'},required=('EXTERNAL_FEASIBILITY',),minimum=0)
            add('availability_source','ENUM','CONFIRMED',when={'source':'EXTERNAL'},values=['CONFIRMED','ASSUMED','UNKNOWN'])
            add('cost_model','ENUM',config.external_cost_models[0],when={'source':'EXTERNAL'},values=list(config.external_cost_models))
            if 'PER_TRIP' in config.external_cost_models:add('trip_rate','DECIMAL','100',unit=config.currency_policy.currency+'/trip',nullable=True,when={'source':'EXTERNAL','cost_model':'PER_TRIP'},required=('ECONOMIC_GOAL',),minimum=0,scale=6)
            if 'PER_KM' in config.external_cost_models:
                add('per_km_rate','DECIMAL','1',unit=config.currency_policy.currency+'/km',nullable=True,when={'source':'EXTERNAL','cost_model':'PER_KM'},required=('ECONOMIC_GOAL',),minimum=0,scale=6)
                add('billing_basis','ENUM',config.per_km_billing_bases[0],when={'source':'EXTERNAL','cost_model':'PER_KM'},values=list(config.per_km_billing_bases))
    add('compatibility_groups','ID_LIST','DRY',nullable=config.homogeneous_loads_declared,separator='|',max_items=100)
    rules={'extra_columns':'REJECT','header_matching':'EXACT','delimiter':',','encoding':'UTF-8','value_whitespace':'TRIM_NFC',
        'max_raw_bytes':MAX_BYTES,'max_normalized_bytes':MAX_BYTES,'max_rows':MAX_ROWS,'empty_rows':'REJECT',
        'model':config.model_dump(mode='json'),'unknown_cost':'PRESERVE_NULL','unknown_availability':'PRESERVE_UNKNOWN',
        'assumed_external_default':{'when':'ASSUMED explicitly declared and services_available empty','value':1,'source':'DATION_DEFAULT'}}
    body=dict(contract_id=semantic_entity+'_v1',schema_version=semantic_entity+'_v1',registry_version=registry_version,
        model_version_id=str(model_id),configuration_hash=model_version['config_hash'],semantic_entity=semantic_entity,
        fields=[f.model_dump(mode='json') for f in fields],rules=rules,normalizer_version=NORMALIZER_VERSION)
    return DataContract(**body,contract_hash=content_sha256(canonical_bytes(body)))


def template_csv(contract):
    """Five operational examples, generated from the descriptor's own fields."""
    out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');writer.writerow([f.public_header for f in contract.fields])
    model=contract.rules['model']
    for index in range(5):
        source=model['allowed_sources'][index%len(model['allowed_sources'])]
        cost=model['external_cost_models'][index%len(model['external_cost_models'])] if model['external_cost_models'] else None
        values={f.public_header:f.examples[0] for f in contract.fields}
        values['source']=source;values['cost_model']=cost
        key='order_id' if contract.semantic_entity=='transport_demand' else 'resource_id';values[key]=('ORD-' if key=='order_id' else 'RES-')+str(index+1).zfill(3)
        writer.writerow([values[f.public_header] if all(values.get(k)==v for k,v in f.applies_when.items()) else '' for f in contract.fields])
    return out.getvalue().encode('utf-8')
