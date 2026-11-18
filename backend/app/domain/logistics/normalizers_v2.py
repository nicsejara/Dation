"""Exact CSV v2 and cross-file checks, always against a published catalog.

No ERP inference, cross-tenant lookup, optional quantity overrides or floats.
"""
import csv,io,json,re,unicodedata
from datetime import date
from decimal import Decimal,localcontext
from uuid import UUID,uuid5
from pydantic import TypeAdapter
from .base import Identifier,decimal_value,Priority
from .contracts import Demand
from .physical import PhysicalPresentation,line_load
from .units import scaled_integer
from .data_contracts import MAX_BYTES,MAX_ROWS,NORMALIZER_VERSION,REGISTRY_VERSION
from .data_contracts_v2 import NORMALIZER_V2
from .normalizers import InputValidationError,_normalize_v1
from app.results.canonical import canonical_bytes,canonical_tree,content_sha256

ID=TypeAdapter(Identifier)


def error(code,message,row=1,column=None):
    raise InputValidationError({'valid':False,'errors':[{'code':code,'row':row,'column':column,'message':message,'hint':'Usá las plantillas de esta publicación y corregí la referencia o cantidad indicada.'}],
        'warnings':[],'counts':{'errors':1,'warnings':0}})


def read_csv(contents,contract):
    if not contents or len(contents)>MAX_BYTES:error('SIZE_LIMIT','El CSV debe contener datos y no superar 10 MB.')
    try:
        text=contents.decode('utf-8-sig')
        if '\x00' in text:raise ValueError()
        reader=csv.reader(io.StringIO(text,newline=''),delimiter=',',strict=True)
        headers=next(reader)
    except (UnicodeError,csv.Error,ValueError,StopIteration):error('CSV_SYNTAX','Falta un encabezado CSV UTF-8 válido.')
    expected=[f.public_header for f in contract.fields]
    if len(headers)!=len(set(headers)):error('DUPLICATE_HEADER','Columnas duplicadas.')
    if set(headers)!=set(expected):error('EXACT_HEADER','Las columnas deben coincidir exactamente con el template; no mezcles cantidades directas con líneas.')
    records=[]
    try:
        for i,values in enumerate(reader,2):
            if i>MAX_ROWS+1:error('ROW_LIMIT','Hasta 10.000 filas de CSV; el límite del solver se verifica separadamente.')
            if len(values)!=len(headers):error('ROW_WIDTH','La fila no coincide con el encabezado.',i)
            records.append({k:unicodedata.normalize('NFC',v.strip()) for k,v in zip(headers,values)})
    except csv.Error:error('CSV_SYNTAX','El CSV contiene comillas o campos inválidos.')
    if not records:error('EMPTY_DATA','Agregá al menos una fila operativa.')
    return records


def package(contents,contract,records,summary,*,warnings=(),assumptions=()):
    normalized={'schema_version':'normalized_logistics_input_v1','semantic_entity':contract.semantic_entity,'model_version_id':str(contract.model_version_id),
        'contract_id':contract.contract_id,'contract_hash':contract.contract_hash,'normalizer_version':NORMALIZER_V2,'currency_policy':dict(contract.rules['model']['currency_policy']),
        'records':canonical_tree(records),'assumptions':canonical_tree(assumptions),'catalog_hash':contract.rules['catalog_hash']}
    data=canonical_bytes(normalized)
    if len(data)>MAX_BYTES:error('NORMALIZED_SIZE_LIMIT','El snapshot normalizado supera 10 MB.')
    report={'valid':True,'schema':contract.schema_version,'contract_hash':contract.contract_hash,'errors':[],'warnings':list(warnings),'counts':{'errors':0,'warnings':len(warnings)},
        'rows':len(records),'columns':len(contract.fields),'preview':canonical_tree(records[:10]),'summary':canonical_tree(summary)}
    return {'bytes':data,'raw_sha256':content_sha256(contents),'canonical_sha256':content_sha256(data),'record_count':len(records),'normalized_size':len(data),'report':report}


def normalize_v2(contents,contract):
    if contract.normalizer_version!=NORMALIZER_V2:error('UNSUPPORTED_VERSION','Versión del normalizador no soportada.')
    config=contract.rules['model'];entity=contract.semantic_entity
    if entity=='transport_resources' or config['cargo']['input_mode']=='direct':
        proxy=contract.model_copy(update={'registry_version':REGISTRY_VERSION,'normalizer_version':NORMALIZER_VERSION})
        result=_normalize_v1(contents,proxy);body=json.loads(result['bytes']);records=body['records']
        if entity=='transport_resources' and config['resource_categories']:
            categories={row['resource_id']:row['resource_category'] for row in read_csv(contents,contract)}
            for record in records:record['resource_category']=categories[record['resource_id']]
        if entity=='transport_demand':
            for row in records:
                for dimension in ('pallets','units'):
                    amount=row['requested'].get(dimension)
                    if amount is not None and Decimal(amount)!=Decimal(amount).to_integral_value():error('DISCRETE_QUANTITY','Pallets y unidades físicas requieren enteros.',column='demand_'+dimension)
        return package(contents,contract,records,result['report']['summary'],warnings=result['report']['warnings'],assumptions=body['assumptions'])
    rows=read_csv(contents,contract);records=[];seen=set();catalog={k:PhysicalPresentation.model_validate(v) for k,v in contract.rules['catalog_snapshot'].items()}
    for i,row in enumerate(rows,2):
        try:
            oid=ID.validate_python(row['order_id'])
            if entity=='order_lines':
                pid=ID.validate_python(row['presentation_id']);key=(oid,pid)
                if pid not in catalog:error('UNKNOWN_PRESENTATION','La presentación no pertenece al catálogo publicado de este Model.',i,'presentation_id')
                quantity=decimal_value(row['quantity']);line_load(catalog[pid],quantity)
                record={'line_id':str(uuid5(UUID(str(contract.model_version_id)),oid+'\x00'+pid)),'order_id':oid,'presentation_id':pid,'quantity':quantity}
            else:
                key=oid
                if row['split_allowed'] not in ('true','false'):raise ValueError('Usá true o false en fraccionamiento.')
                split=row['split_allowed']=='true'
                if split and not config['split_permitted']:raise ValueError('La orden no puede habilitar fraccionamiento prohibido por el modelo.')
                distance=decimal_value(row['distance_km']);scaled_integer(distance,3)
                if distance<=0:raise ValueError('La distancia debe ser positiva.')
                if not all(re.fullmatch(r'\d{4}-\d{2}-\d{2}',row[k]) for k in ('ready_date','delivery_due_date')):raise ValueError('Fechas AAAA-MM-DD sin hora.')
                ready=date.fromisoformat(row['ready_date']);due=date.fromisoformat(row['delivery_due_date'])
                if due<ready:raise ValueError('La fecha límite precede la disponibilidad.')
                record={'order_id':oid,'origin_id':ID.validate_python(row['origin_id']),'destination_id':ID.validate_python(row['destination_id']),
                    'distance_km':distance,'ready_date':ready,'delivery_due_date':due,'priority':Priority(row['priority']),'split_allowed':split}
            if key in seen:error('DUPLICATE_LINE' if entity=='order_lines' else 'DUPLICATE_ID','No repitas una orden/presentación ni el ID de una orden.',i)
            seen.add(key);records.append(canonical_tree(record))
        except InputValidationError:raise
        except (ValueError,TypeError,KeyError,ArithmeticError) as exc:error('INVALID_VALUE',str(exc),i)
    records.sort(key=lambda r:(r['order_id'],r.get('presentation_id','')))
    summary={'semantic_entity':entity,'record_count':len(records),'cross_validation_pending':True,'unknown_cost_count':0,'unknown_availability_count':0}
    return package(contents,contract,records,summary)


def combine_catalog(records,contract,*,solver_limits=False):
    """Validate all references against this immutable model/contract snapshot.

    Pair Orders+OrderLines is atomic. Fleet-only/empty Pack is still a valid
    incomplete Case, just as v1; it never makes D1 ready.
    """
    orders=records.get('transport_demand');lines=records.get('order_lines')
    if orders is None and lines is None:return ()
    if orders is None or lines is None:error('INCOMPLETE_ORDER_LINES','Publicá Órdenes y Líneas de órdenes juntas, o continuá sin ambas.')
    if solver_limits and (len(orders)>500 or len(lines)>500):error('SOLVER_ROW_LIMIT','El piloto v2 admite hasta 500 órdenes y 500 líneas por corrida; el CSV puede validarse por separado.')
    catalog={k:PhysicalPresentation.model_validate(v) for k,v in contract.rules['catalog_snapshot'].items()}
    by_id={r['order_id']:r for r in orders};grouped={key:[] for key in by_id};seen=set()
    if len(by_id)!=len(orders):error('DUPLICATE_ID','Identificador de orden duplicado.')
    for line in lines:
        oid=line['order_id'];pid=line['presentation_id'];key=(oid,pid)
        if oid not in by_id:error('ORPHAN_LINE','La línea refiere una orden ausente: '+oid)
        if pid not in catalog:error('UNKNOWN_PRESENTATION','La presentación no pertenece a este snapshot.')
        if key in seen:error('DUPLICATE_LINE','Línea semántica duplicada.')
        seen.add(key);presentation=catalog[pid];quantity=decimal_value(line['quantity']);load=line_load(presentation,quantity)
        expected_id=str(uuid5(UUID(str(contract.model_version_id)),oid+'\x00'+pid))
        if line['line_id']!=expected_id:error('LINE_IDENTITY','La identidad de la línea no coincide con la publicación.')
        grouped[oid].append({'line_id':expected_id,'presentation_id':pid,'quantity':quantity,'load':load,'physical':presentation})
    result=[]
    for oid,order in sorted(by_id.items()):
        items=grouped[oid]
        if not items:error('ORDER_WITHOUT_LINES','Cada orden necesita al menos una línea: '+oid)
        if 'requested' in order or any(k.startswith('demand_') for k in order):error('AMBIGUOUS_QUANTITY','No mezcles cantidades agregadas directas y líneas derivadas.')
        with localcontext() as ctx:
            ctx.prec=60
            requested={d:sum(getattr(item['load'],d) for item in items) for d in contract.rules['model']['active_dimensions']}
        groups=tuple(sorted({g for item in items for g in item['physical'].compatibility_groups}))
        try:demand=Demand(**order,requested=requested,compatibility_groups=groups)
        except ValueError as exc:error('DOMAIN_CONTRACT',str(exc))
        result.append({'demand':demand,'lines':tuple(items)})
    return tuple(result)
