"""Generate the persisted run's artifact; preserve established CSV columns and quoting."""
import json

VEHICLES={'Truck_S':'Camión pequeño','Truck_M':'Camión mediano','Truck_L':'Camión grande','Third_Party_L':'Camión grande tercerizado'}
def vehicle(value):return VEHICLES.get(value,str(value or '').replace('_',' '))
def coalesce(*values):return next((v for v in values if v is not None),None)
def text(value):
 if value is None:return ''
 if isinstance(value,bool):return str(value).lower()
 if isinstance(value,float) and value.is_integer():return str(int(value))
 return str(value)
def csv(rows):
 def cell(value):
  value=text(value)
  if value[:1] in {'=','+','@','-'}:value="'"+value
  return '"'+value.replace('"','""')+'"'
 return ('\ufeff'+'\r\n'.join(';'.join(cell(v) for v in row) for row in rows)).encode('utf-8')
def generate(run,format):
 result=run.get('result_json')
 if run.get('status')!='completed' or not isinstance(result,dict):raise ValueError('La corrida no contiene un resultado exportable.')
 schema=result.get('schema_version')
 if result.get('result_schema') or (schema is not None and schema not in {'assignment_v1','scheduling_v1','dispatch_v1','dispatch_v2'}):
  raise ValueError('UNSUPPORTED_RESULT_SCHEMA: usá la exportación versionada con Run y fingerprint para packages publicados.')
 if format=='json':
  name='planificacion-'+run['id']+'.json' if schema=='scheduling_v1' else 'dation-'+run['id'][:8]+'.json'
  return name,json.dumps(result,ensure_ascii=False,indent=2).encode('utf-8'),'application/json'
 if not schema:raise ValueError('La corrida no contiene un resultado exportable.')
 trips=(result.get('scenarios',{}).get('selected') or {}).get('trips') or [];rows=[]
 if schema=='assignment_v1':
  name='assignment-recomendada.csv';headers=['Viaje','Vehicle ID','Tipo de vehículo','Propiedad','Proveedor','Site base','Origen','Destino','Orden','Producto','Unidades asignadas','Kg asignados','Carga total viaje (kg)','Capacidad viaje (kg)','Utilización viaje','Costo estimado viaje','CO2 estimado viaje']
  for t in trips:
   for l in t.get('loads') or []:rows.append([t.get('trip_id'),t.get('vehicle_id') or t.get('fleet_pool_id') or '',vehicle(t.get('vehicle_type')),'Propio' if t.get('ownership')=='own' else 'Tercerizado',t.get('provider_name') or '',t.get('base_site') or t.get('base_location') or '',t.get('origin'),t.get('destination'),l.get('order_id'),l.get('product') or '',l.get('units'),l.get('kg'),t.get('load_kg'),t.get('capacity_kg'),t.get('utilization'),coalesce(t.get('estimated_cost'),t.get('cost')),coalesce(t.get('estimated_co2_kg'),t.get('co2_kg'))])
 elif schema=='scheduling_v1':
  name='planificacion-recomendada.csv';headers=['Viaje','Vehicle ID','Tipo de vehículo','Origen','Destino','Ready date','Salida','Llegada','Recurso disponible','Días de tránsito','Días de ciclo','Espera (días)','Fecha objetivo','Orden','Producto','Unidades','Kg']
  for t in trips:
   for l in t.get('loads') or []:rows.append([t.get('trip_id'),t.get('vehicle_id'),vehicle(t.get('vehicle_type')),t.get('origin'),t.get('destination'),t.get('ready_date'),t.get('dispatch_date'),t.get('arrival_date'),t.get('resource_available_again'),t.get('transit_days'),t.get('cycle_days'),t.get('wait_days'),t.get('delivery_due_date') or '',l.get('order_id'),l.get('product') or '',l.get('units'),l.get('kg')])
 else:
  name='distribucion-recomendada.csv';headers=['Viaje','Salida','Llegada','Recurso disponible','Días de ciclo','Origen','Destino','Recurso','Camión','Propiedad','Orden','Producto','Unidades','Kg','Costo del viaje','CO2 del viaje']
  for t in trips:
   for i,l in enumerate(t.get('loads') or []):rows.append([t.get('trip_id'),t.get('dispatch_date') or '',t.get('arrival_date') or '',t.get('resource_available_again') or '',t.get('cycle_days') or '',t.get('origin'),t.get('destination'),t.get('fleet_pool_id') or t.get('vehicle_id') or t.get('vehicle_type') or '',vehicle(t.get('vehicle_type')),'Propio' if t.get('ownership')=='own' else 'Tercerizado',l.get('order_id'),l.get('product') or '',l.get('units'),l.get('kg'),coalesce(t.get('cost'),t.get('estimated_cost')) if i==0 else '',coalesce(t.get('co2_kg'),t.get('estimated_co2_kg')) if i==0 else ''])
 if not rows:raise ValueError('La decisión no contiene filas para exportar.')
 return name,csv([headers,*rows]),'text/csv; charset=utf-8'
