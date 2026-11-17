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
