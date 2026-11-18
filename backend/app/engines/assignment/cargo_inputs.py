"""Validate pinned v2 line inputs without invoking a solver or any service."""
from decimal import Decimal
from uuid import uuid5
from app.domain.logistics.cargo_execution import CatalogDemand,CargoOrderLine
from app.domain.logistics.physical import normalize_catalog,line_load
from app.results.canonical import canonical_tree,canonical_bytes
from app.results.contracts import RuntimeIdentity
from app.models.ultimate_foundation import LogisticsModelSnapshotV2

IDENTITY=RuntimeIdentity(engine_name='transport_plan',engine_version='3.0.0',runtime_profile='transport_plan_cargo_v2',result_schema='transport_plan_v1',result_schema_version=1)


def validate_cargo_input(request):
    cfg=request.model.configuration;catalog=normalize_catalog(cfg.cargo,cfg.active_dimensions)
    count=0
    for order in request.demands:
        if getattr(order.requested,cfg.primary_dimension)<=0:raise ValueError('V2 requiere una dimensión principal positiva común a toda la carga.')
        if order.split_allowed and not cfg.split_permitted:raise ValueError('El pedido no puede ampliar el permiso de fraccionamiento del modelo.')
        if cfg.cargo.input_mode=='catalog':
            if not isinstance(order,CatalogDemand):raise ValueError('La orden catálogo necesita sus líneas fijadas.')
            count+=len(order.lines);totals={d:Decimal(0) for d in cfg.active_dimensions};groups=set()
            for line in order.lines:
                presentation=catalog.get(line.presentation_id)
                if presentation is None:raise ValueError('Presentación ajena al catálogo.')
                if line.line_id!=str(uuid5(request.model.version_id,order.order_id+'\x00'+line.presentation_id)):raise ValueError('La línea no coincide con el Model Version/orden/presentación.')
                if line.compatibility_groups!=presentation.compatibility_groups:raise ValueError('Las categorías de la línea difieren del catálogo.')
                load=line_load(presentation,line.quantity);groups.update(presentation.compatibility_groups)
                for d in cfg.active_dimensions:totals[d]+=getattr(load,d)
            if any(getattr(order.requested,d)!=totals[d] for d in cfg.active_dimensions) or order.compatibility_groups!=tuple(sorted(groups)):
                raise ValueError('La demanda agregada difiere de sus líneas físicas.')
        else:
            if isinstance(order,CatalogDemand):raise ValueError('Datos directos no mezclan líneas catálogo.')
            if not cfg.cargo.can_co_load(order.compatibility_groups,order.compatibility_groups):raise ValueError('Las categorías de la carga directa requieren autorización explícita de co-carga.')
            for d in ('pallets','units'):
                amount=getattr(order.requested,d)
                if amount is not None and amount!=amount.to_integral_value():raise ValueError('V2 no divide objetos físicos en fracciones.')
    if count>500:raise ValueError('V2 admite hasta 500 líneas por corrida.')
    if cfg.resource_categories:
        if any(getattr(r,'resource_category',None) not in cfg.resource_categories for r in request.resources):raise ValueError('Categoría de recurso no admitida o ausente.')
    return True


def demands_from_records(model,records):
    """Shared server/worker reconstruction, always verified again in the DTO."""
    if not isinstance(model,LogisticsModelSnapshotV2):model=LogisticsModelSnapshotV2.model_validate(model)
    if model.configuration.cargo.input_mode!='catalog':return records['transport_demand']
    from app.domain.logistics.data_contracts import compile_contract
    from app.domain.logistics.normalizers_v2 import combine_catalog
    version={'id':str(model.version_id),'config_jsonb':canonical_tree(model.configuration),'config_hash':model.configuration_hash,'contract_registry_version':model.contract_registry_version}
    contract=compile_contract(version,'transport_demand');combined=combine_catalog(records,contract,solver_limits=True)
    return tuple(CatalogDemand(**row['demand'].model_dump(),lines=tuple(CargoOrderLine(line_id=l['line_id'],presentation_id=l['presentation_id'],quantity=l['quantity'],compatibility_groups=l['physical'].compatibility_groups) for l in row['lines'])) for row in combined)


def require_v2(request):
    from .transport_contracts import TransportPlanInput
    request=TransportPlanInput.model_validate(request)
    if not isinstance(request.model,LogisticsModelSnapshotV2):raise ValueError('El perfil cargo v2 exige una configuración v2 íntegra y fijada.')
    return request


def run_cargo_core(request):
    from decimal import localcontext
    from .transport_plan import _run
    request=require_v2(request)
    with localcontext() as context:
        context.prec=60
        return _run(request)


def run_cargo_policy(request,*,alternative_budget=3):
    from .transport_policy_result import _run_policy
    return _run_policy(require_v2(request),alternative_budget=alternative_budget)
