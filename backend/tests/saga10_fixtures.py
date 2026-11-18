"""Synthetic immutable catalogs, without external services."""
from copy import deepcopy
from tests.test_ultimate_case_models import config

def direct_config(**changes):
    value=config().model_dump(mode='json')
    value.update(version=2,consolidation_permitted=True,resource_categories=[],cargo={'input_mode':'direct','profile':'PALLETIZED','split_policy':'INDIVISIBLE','compatibility_policy':'CATEGORIZED'})
    value.update(changes);return value

def catalog_config():
    value=direct_config(active_dimensions=['pallets','weight_kg','volume_m3','units'],primary_dimension='pallets',split_permitted=True,homogeneous_loads_declared=True)
    value['cargo']={'input_mode':'catalog','profile':'PALLETIZED','split_policy':'DISCRETE','compatibility_policy':'UNIFORM_DECLARED','products':[],
      'logistic_units':[{'logistic_unit_id':'PALLET-STD','label':'Pallet compartido','type':'PALLET','tare_mass':{'value':'25','unit':'kg'},'empty_dimensions':{'length':'120','width':'100','height':'15','unit':'cm'}}], 'presentations':[]}
    for key,name,mass,height,gross in [('JUICE','Jugo','12','180','985'),('WATER','Agua','15','200','1225'),('SODA','Gaseosa','13.5','190','1105')]:
        value['cargo']['products'].append({'product_id':key,'name':name,'unit_label':'caja','units_per_package':12,'gross_mass':{'value':mass,'unit':'kg'}})
        value['cargo']['presentations'].append({'presentation_id':'PAL-'+key,'label':name+' palletizado','logistic_unit_id':'PALLET-STD','components':[{'product_id':key,'quantity':'80'}],
            'loaded_dimensions':{'length':'120','width':'100','height':height,'unit':'cm'},'gross_mass':{'value':gross,'unit':'kg'}})
    return deepcopy(value)

def bulk_config(density='850',unit='m3'):
    value=direct_config(active_dimensions=['weight_kg','volume_m3'],primary_dimension='volume_m3',split_permitted=True,homogeneous_loads_declared=True)
    product={'product_id':'LIQUID','name':'Líquido de prueba','unit_label':unit}
    if density is not None:product['density_kg_per_m3']=density
    value['cargo']={'input_mode':'catalog','profile':'LIQUID_BULK','split_policy':'CONTINUOUS','compatibility_policy':'UNIFORM_DECLARED','products':[product],
      'presentations':[{'presentation_id':'BULK','label':'Granel explícito','quantity_kind':'CONTINUOUS','quantity_unit':unit,'components':[{'product_id':'LIQUID','quantity':'1'}]}]}
    return value


def cargo_request(configuration=None, specifications=None, resources=None, *, options=None, goal='MINIMIZE_COST', guards=()):
    """Pinned synthetic v2 boundary. No CSV or database mutation."""
    from decimal import Decimal
    from uuid import uuid5
    from app.domain.logistics.physical import normalize_catalog, line_load
    from app.services.logistics_model_service import configuration_snapshot
    from app.engines.assignment.transport_contracts import TransportPlanInput
    from tests.test_transport_plan_core import request, order, resource
    cfg, digest = configuration_snapshot(configuration or catalog_config())
    data = request().model_dump(mode='python'); model = data['model']; context = data['context']
    for key in ('operating_role','transport_pattern','primary_dimension','active_dimensions','allowed_sources','homogeneous_loads_declared','split_permitted','currency_policy'):
        model[key]=cfg[key]
    model.update(configuration=cfg,configuration_hash=digest,contract_registry_version='SAGA10_DOMAIN_V2')
    context.update(model_hash=digest,active_dimensions=cfg['active_dimensions'],primary_dimension=cfg['primary_dimension'],operating_role=cfg['operating_role'],currency_policy=cfg['currency_policy'])
    context['case_policy']=context['node_policy']={'primary_goal':goal,'guardrails':list(guards)}
    context['read_set']=[{**x,'normalizer_version':'DATION_CARGO_INPUT_NORMALIZER_V2'} for x in context['read_set']]
    demands=[]
    if cfg['cargo']['input_mode']=='catalog':
        context['read_set'].append(dict(slot='order_lines',canonical_sha256='8'*64,contract_hash='9'*64,normalizer_version='DATION_CARGO_INPUT_NORMALIZER_V2'))
        physical=normalize_catalog(cfg['cargo'],cfg['active_dimensions'])
        specifications=specifications if specifications is not None else [('O1', [('PAL-JUICE','5'),('PAL-WATER','4'),('PAL-SODA','3')], True)]
        for oid,lines,split in specifications:
            vector={d:Decimal(0) for d in cfg['active_dimensions']};groups=set();details=[]
            for pid,quantity in lines:
                p=physical[pid];q=Decimal(quantity);load=line_load(p,q);groups.update(p.compatibility_groups)
                for d in vector:vector[d]+=getattr(load,d)
                details.append(dict(line_id=str(uuid5(model['version_id'],oid+'\x00'+pid)),presentation_id=pid,quantity=q,compatibility_groups=p.compatibility_groups))
            demands.append(order(oid,split=split,requested=vector,compatibility_groups=sorted(groups),lines=details))
    else:demands=specifications if specifications is not None else [order(pallets='3',split=cfg['split_permitted'])]
    data.update(model=model,context=context,demands=demands,resources=resources if resources is not None else [resource(cap='26',services=1,guaranteed_capacity={d:{'pallets':'26','weight_kg':'30000','volume_m3':'60','units':'30000'}[d] for d in cfg['active_dimensions']})],options=options or {})
    return TransportPlanInput.model_validate(data)
