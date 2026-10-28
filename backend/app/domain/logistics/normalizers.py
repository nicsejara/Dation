"""T4 deterministic exact-schema CSV -> T1 DTO snapshots, without solver/IA."""
import csv
from datetime import date
from decimal import Decimal,localcontext
import io
import json
import re
import unicodedata

from pydantic import TypeAdapter,ValidationError
from app.domain.logistics.base import Identifier,Count,decimal_value
from app.domain.logistics.contracts import Demand,TransportResource
from app.domain.logistics.units import scaled_integer
from app.results.canonical import canonical_bytes,canonical_tree,content_sha256
from .data_contracts import DataContract,MAX_BYTES,MAX_ROWS,NORMALIZER_VERSION,REGISTRY_VERSION

ID=TypeAdapter(Identifier);COUNT=TypeAdapter(Count)


class InputValidationError(ValueError):
    def __init__(self,report):super().__init__('Revisá el formato y los campos indicados.');self.report=report


def normalize_input(contents,contract):
    contract=DataContract.model_validate(contract);errors=[];warnings=[];records=[];assumptions=[];seen=set()
    def problem(code,row,column,message,**extra):return dict(code=code,row=row,column=column,message=message,hint='Usá el template de esta Model Version y revisá la regla del campo.',**extra)
    def fail(code,message,column=None):raise InputValidationError({'valid':False,'errors':[problem(code,1,column,message)],'warnings':[],'counts':{'errors':1,'warnings':0}})
    if contract.normalizer_version!=NORMALIZER_VERSION or contract.registry_version!=REGISTRY_VERSION:fail('UNSUPPORTED_VERSION','El contrato requiere una versión de normalizer/registry no disponible.')
    if not contents or len(contents)>MAX_BYTES:fail('SIZE_LIMIT','El CSV debe contener datos y no superar 10 MB.')
    try:text=contents.decode('utf-8-sig')
    except UnicodeError:fail('ENCODING','Guardá el CSV con codificación UTF-8.')
    if '\x00' in text:fail('ENCODING','El archivo contiene bytes no permitidos.')
    reader=csv.reader(io.StringIO(text,newline=''),delimiter=',',strict=True)
    try:headers=next(reader)
    except (StopIteration,csv.Error):fail('HEADER','Falta el encabezado CSV.')
    if len(set(headers))!=len(headers):fail('DUPLICATE_HEADER','Hay columnas repetidas.')
    expected={f.public_header for f in contract.fields}
    extra=set(headers)-expected
    if extra:fail('EXTRA_COLUMN','Hay columnas ajenas al contrato. No se guardó el archivo.',sorted(extra)[0][:120])
    missing=expected-set(headers)
    if missing:fail('MISSING_COLUMN','Faltan columnas del template; las celdas no aplicables pueden quedar vacías.',sorted(missing)[0])
    config=contract.rules['model'];fields={f.public_header:f for f in contract.fields}
    def parse(field,value):
        if field.type=='IDENTIFIER':return ID.validate_python(value)
        if field.type=='INTEGER':
            if not re.fullmatch(r'(?:0|[1-9][0-9]*)',value):raise ValueError('Ingresá un entero no negativo.')
            return COUNT.validate_python(int(value))
        if field.type=='DECIMAL':
            v=decimal_value(value);scaled_integer(v,field.validation['scale'])
            if v<0 or field.validation.get('positive') and v==0:raise ValueError('La cantidad/capacidad debe ser positiva; los costos no negativos.')
            return v
        if field.type=='DATE':
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Usá fecha AAAA-MM-DD, sin hora.')
            return date.fromisoformat(value)
        if field.type=='BOOLEAN':
            if value not in ('true','false'):raise ValueError('Usá true o false.')
            return value=='true'
        if field.type=='ENUM':
            if value not in field.validation['values']:raise ValueError('Elegí un valor declarado por el contrato.')
            return value
        if field.type=='ID_LIST':
            items=value.split('|')
            if len(items)>100 or len(set(items))!=len(items):raise ValueError('Grupos únicos; máximo 100.')
            return tuple(sorted(ID.validate_python(x) for x in items))
        if field.type=='LANES':
            items=json.loads(value)
            if not isinstance(items,list) or not 1<=len(items)<=100:raise ValueError('Informá entre 1 y 100 rutas explícitas.')
            lanes=[]
            for item in items:
                if not isinstance(item,list) or len(item)!=2:raise ValueError('Cada ruta es [origen,destino].')
                lanes.append(tuple(ID.validate_python(x) for x in item))
            if len(set(lanes))!=len(lanes):raise ValueError('No repitas rutas.')
            return tuple(sorted(lanes))
        raise ValueError('Tipo de campo desconocido.')
    try:
        for index,values in enumerate(reader,2):
            if index>MAX_ROWS+1:fail('ROW_LIMIT','El CSV admite hasta 10.000 filas operativas.')
            before=len(errors)
            if len(values)!=len(headers):errors.append(problem('ROW_WIDTH',index,None,'La fila no coincide con las columnas del template.'));continue
            raw={k:unicodedata.normalize('NFC',v.strip()) for k,v in zip(headers,values)};row={}
            for key,field in fields.items():
                value=raw[key];applies=all(raw.get(k)==v for k,v in field.applies_when.items())
                if not applies:
                    if value:errors.append(problem('SOURCE_CONDITIONAL',index,key,'Este campo no aplica a la fuente o tarifa de la fila.'))
                    row[key]=None;continue
                if not value:
                    if not field.nullable:errors.append(problem('REQUIRED_VALUE',index,key,'Completá el campo requerido para esta fila.'))
                    row[key]=None;continue
                try:row[key]=parse(field,value)
                except (ValueError,ValidationError,TypeError,OverflowError,RecursionError):errors.append(problem('INVALID_VALUE',index,key,'El valor no cumple el tipo, enum, unidad o precisión del contrato.'))
            if len(errors)!=before:
                if len(errors)>=100:break
                continue
            entity_id=row['order_id' if contract.semantic_entity=='transport_demand' else 'resource_id']
            if entity_id in seen:errors.append(problem('DUPLICATE_ID',index,'order_id' if contract.semantic_entity=='transport_demand' else 'resource_id','El ID debe ser único.'));continue
            seen.add(entity_id)
            try:
                if contract.semantic_entity=='transport_demand':
                    if row['split_allowed'] and not config['split_permitted']:raise ValueError('El Model no permite split.')
                    dto=Demand(**{k:row[k] for k in ['order_id','origin_id','destination_id','distance_km','ready_date','delivery_due_date','priority','split_allowed']},requested={dim:row['demand_'+dim] for dim in config['active_dimensions']},compatibility_groups=row['compatibility_groups'] or ())
                else:
                    own=row['source']=='OWN';amount=row.get('services_available');source=row.get('availability_source')
                    if not own and source=='ASSUMED':
                        defaulted=amount is None
                        if defaulted:amount=1
                        assumptions.append({'code':'ASSUMED_EXTERNAL_AVAILABILITY','entity_id':entity_id,'value':amount,'unit':'horizon_services','source':'DATION_DEFAULT' if defaulted else 'DERIVED'})
                        warnings.append(problem('ASSUMED_EXTERNAL_AVAILABILITY',index,'services_available','Disponibilidad ASSUMED: '+str(amount)+'. No se considera confirmada.'))
                    guaranteed={dim:row['guaranteed_'+dim] for dim in config['active_dimensions']};maximum={dim:row['maximum_'+dim] for dim in config['active_dimensions']}
                    rate=row.get('operating_cost_per_km') if own else row.get('trip_rate' if row['cost_model']=='PER_TRIP' else 'per_km_rate')
                    if rate is None:warnings.append(problem('UNKNOWN_COST',index,'operating_cost_per_km' if own else 'trip_rate' if row['cost_model']=='PER_TRIP' else 'per_km_rate','Costo desconocido: se conserva null. No habilita por sí solo un objetivo económico.'))
                    if (row.get('units_available') if own else amount) is None:warnings.append(problem('UNKNOWN_AVAILABILITY',index,'units_available' if own else 'services_available','Disponibilidad desconocida; no representa capacidad ilimitada.'))
                    dto=TransportResource(resource_id=entity_id,source=row['source'],guaranteed_capacity=guaranteed,maximum_capacity=maximum if any(v is not None for v in maximum.values()) else None,lanes=row['lanes'],compatibility_groups=row['compatibility_groups'] or (),units_available=row.get('units_available') if own else None,base_origin_id=row.get('base_origin_id') if own else None,operating_cost_per_km=rate if own else None,services_available=None if own else amount,availability_source=None if own else source,external_cost=None if own else {'cost_model':row['cost_model'],'rate':rate,'billing_basis':row.get('billing_basis')})
                records.append(canonical_tree(dto))
            except (ValueError,ValidationError,TypeError):errors.append(problem('DOMAIN_CONTRACT',index,None,'Revisá fechas ready/due, split, garantizada/máxima y coherencia de disponibilidad/source.'))
    except csv.Error:fail('CSV_SYNTAX','El CSV tiene comillas o delimitadores inválidos.')
    if not records and not errors:errors.append(problem('EMPTY_DATA',2,None,'Agregá al menos una fila operativa.'))
    report={'valid':not errors,'schema':contract.schema_version,'contract_hash':contract.contract_hash,'errors':errors[:100],'warnings':warnings[:100],'counts':{'errors':len(errors),'warnings':len(warnings)},'rows':len(records),'columns':len(headers)}
    if errors:raise InputValidationError(report)
    key='order_id' if contract.semantic_entity=='transport_demand' else 'resource_id';records.sort(key=lambda r:r[key]);assumptions.sort(key=lambda a:a['entity_id'])
    normalized={'schema_version':'normalized_logistics_input_v1','semantic_entity':contract.semantic_entity,'model_version_id':str(contract.model_version_id),'contract_id':contract.contract_id,'contract_hash':contract.contract_hash,'normalizer_version':NORMALIZER_VERSION,'currency_policy':dict(config['currency_policy']),'records':records,'assumptions':assumptions}
    data=canonical_bytes(normalized)
    if len(data)>MAX_BYTES:fail('NORMALIZED_SIZE_LIMIT','El snapshot normalizado supera 10 MB. Dividí el archivo antes de publicar.')
    summary={'semantic_entity':contract.semantic_entity,'record_count':len(records),'assumptions':assumptions[:20],'assumptions_total':len(assumptions),'assumptions_truncated':len(assumptions)>20,'assumed_external_count':len(assumptions),'unknown_availability_count':sum(1 for w in warnings if w['code']=='UNKNOWN_AVAILABILITY'),'unknown_cost_count':sum(1 for w in warnings if w['code']=='UNKNOWN_COST')}
    if contract.semantic_entity=='transport_demand':
        with localcontext() as context:
            context.prec=60;summary['quantity_totals']=canonical_tree({dim:sum((Decimal(r['requested'][dim]) for r in records),Decimal(0)) for dim in config['active_dimensions']})
    else:summary['source_counts']={s:sum(r['source']==s for r in records) for s in config['allowed_sources']}
    report.update(preview=records[:10],summary=summary)
    return {'bytes':data,'raw_sha256':content_sha256(contents),'canonical_sha256':content_sha256(data),'record_count':len(records),'normalized_size':len(data),'report':report}
