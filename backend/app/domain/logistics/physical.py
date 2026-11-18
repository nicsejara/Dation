"""Deterministic Decimal physical normalization with explicit provenance.

Loaded exterior volume is a scalar envelope, never a 3D packing certificate.
"""
from decimal import Decimal, localcontext, ROUND_HALF_UP
from math import gcd, lcm
from .base import ContractModel, Identifier, Positive
from .cargo import CargoConfiguration,LoadPresentation
from .units import QuantityVector, QUANTITY_SCALES, scaled_integer


class PhysicalPresentation(ContractModel):
    presentation_id: Identifier
    quantity_kind: str
    quantity_unit: str
    coefficients: QuantityVector
    allocation_increment: Positive
    compatibility_groups: tuple[str,...]
    composition: tuple[dict,...]
    provenance: dict


def kg(m):return m.value * (1000 if m.unit == 't' else 1)
def m3(v):return v.value / (1000 if v.unit == 'l' else 1)
def volume(d):return d.length*d.width*d.height / (1000000 if d.unit == 'cm' else 1)


def rounded(value,dimension):
    result=value.quantize(Decimal(1).scaleb(-QUANTITY_SCALES[dimension]),rounding=ROUND_HALF_UP)
    scaled_integer(result,QUANTITY_SCALES[dimension])
    if value>0 and result==0:raise ValueError('La propiedad física queda por debajo de la precisión soportada: '+dimension)
    return result


def normalize_presentation(cargo,presentation,dimensions):
    cargo=CargoConfiguration.model_validate(cargo);presentation=LoadPresentation.model_validate(presentation)
    if not any(p==presentation for p in cargo.presentations):raise ValueError('La presentación no pertenece al catálogo validado.')
    return _normalize_validated(cargo,presentation,dimensions)


def _normalize_validated(cargo,presentation,dimensions):
    with localcontext() as ctx:
        ctx.prec=60
        products={p.product_id:p for p in cargo.products};units={u.logistic_unit_id:u for u in cargo.logistic_units}
        unit=units.get(presentation.logistic_unit_id);parts=[];groups=set();sources={}
        mass=kg(presentation.gross_mass) if presentation.gross_mass else None
        ext=m3(presentation.external_volume) if presentation.external_volume else None
        density=presentation.density_kg_per_m3
        contained=Decimal(0);component_mass=Decimal(0);mass_known=True
        for component in presentation.components:
            product=products[component.product_id];groups.update(product.compatibility_groups)
            contained+=component.quantity*product.units_per_package
            if product.gross_mass:component_mass+=component.quantity*kg(product.gross_mass)
            else:mass_known=False
            parts.append({'product_id':product.product_id,'quantity':component.quantity,'units_per_package':product.units_per_package,'product_units':component.quantity*product.units_per_package})
        if presentation.loaded_dimensions:
            derived=volume(presentation.loaded_dimensions)
            if ext is not None and rounded(ext,'volume_m3')!=rounded(derived,'volume_m3'):raise ValueError('El volumen declarado contradice las dimensiones exteriores cargadas.')
            ext=derived;sources['volume_m3']='LOADED_EXTERIOR_DIMENSIONS'
        elif ext is not None:sources['volume_m3']='DECLARED_EXTERIOR_VOLUME'
        if presentation.quantity_kind == 'CONTINUOUS':
            product=products[presentation.components[0].product_id]
            if presentation.density_kg_per_m3 and product.density_kg_per_m3 and presentation.density_kg_per_m3!=product.density_kg_per_m3:raise ValueError('Densidades declaradas contradictorias.')
            density=density or product.density_kg_per_m3
            base_mass={'kg':Decimal(1),'t':Decimal(1000)}.get(presentation.quantity_unit)
            base_volume={'m3':Decimal(1),'l':Decimal('.001')}.get(presentation.quantity_unit)
            if base_mass is not None:
                if mass is not None and mass!=base_mass:raise ValueError('El peso por unidad contradice la unidad física de la presentación.')
                mass=base_mass;sources['weight_kg']='EXPLICIT_QUANTITY_UNIT'
            if base_volume is not None:
                if ext is not None and ext!=base_volume:raise ValueError('El volumen por unidad contradice la unidad física de la presentación.')
                ext=base_volume;sources['volume_m3']='EXPLICIT_QUANTITY_UNIT'
            contained=None
        elif mass_known:
            derived=component_mass+(kg(unit.tare_mass) if unit else 0)+kg(presentation.extra_tare_mass)
            if mass is not None and rounded(mass,'weight_kg')!=rounded(derived,'weight_kg'):raise ValueError('El peso bruto declarado contradice componentes y tara.')
            mass=derived;sources['weight_kg']='COMPONENT_GROSS_PLUS_EXPLICIT_TARE'
        if mass is not None and 'weight_kg' not in sources:sources['weight_kg']='DECLARED_GROSS_MASS'
        if density is not None:
            if mass is not None and ext is not None and rounded(mass,'weight_kg')!=rounded(ext*density,'weight_kg'):raise ValueError('Peso, volumen y densidad declarados son contradictorios.')
            if mass is None and ext is not None:mass=ext*density;sources['weight_kg']='EXPLICIT_DENSITY_TIMES_VOLUME'
            if ext is None and mass is not None:ext=mass/density;sources['volume_m3']='MASS_OVER_EXPLICIT_DENSITY'
        tare=(kg(unit.tare_mass) if unit else Decimal(0))+kg(presentation.extra_tare_mass)
        if mass is not None and mass<tare:raise ValueError('La tara supera el peso bruto.')
        if unit and unit.structural_limit_kg is not None and mass is None:raise ValueError('El límite estructural exige conocer el peso bruto cargado.')
        if unit and unit.structural_limit_kg is not None and mass is not None and mass>unit.structural_limit_kg:raise ValueError('El peso bruto supera el límite estructural declarado de la unidad logística.')
        values={'weight_kg':mass,'volume_m3':ext,'pallets':Decimal(1) if unit and unit.type=='PALLET' else Decimal(0),'units':contained}
        for d in dimensions:
            if values[d] is None:raise ValueError('Falta una propiedad física explícita para '+str(d)+'; no se infiere densidad ni volumen cargado.')
        # Only active coefficients enter the engine vector; full sources remain pinned.
        coefficients={d:rounded(values[d],d) for d in dimensions}
        if not any(coefficients.values()):raise ValueError('La presentación no contiene cantidades positivas en las dimensiones activas.')
        # The finest 0.001-unit step that conserves every canonical dimension
        # exactly. Do not round each split independently and lose cargo.
        step=1
        for d,v in coefficients.items():step=lcm(step,1000//gcd(scaled_integer(v,QUANTITY_SCALES[d]),1000))
        increment=Decimal(1) if presentation.quantity_kind=='DISCRETE' else Decimal(step)/1000
        return PhysicalPresentation(presentation_id=presentation.presentation_id,quantity_kind=presentation.quantity_kind,quantity_unit=presentation.quantity_unit,
            coefficients=coefficients,allocation_increment=increment,compatibility_groups=tuple(sorted(groups)),composition=tuple(parts),
            provenance={'rounding':'ROUND_HALF_UP','scales':{d:QUANTITY_SCALES[d] for d in dimensions},'sources':sources,'declared_weight_kg':kg(presentation.gross_mass) if presentation.gross_mass else None,'declared_volume_m3':m3(presentation.external_volume) if presentation.external_volume else None,'explicit_density_kg_per_m3':density,'tare_weight_kg':tare,'geometry':'SCALAR_EXTERIOR_ONLY_NOT_PACKING'})


def normalize_catalog(cargo,dimensions):
    cargo=CargoConfiguration.model_validate(cargo)
    return {p.presentation_id:_normalize_validated(cargo,p,dimensions) for p in cargo.presentations}


def line_load(presentation,quantity):
    with localcontext() as ctx:
        ctx.prec=60
        if quantity<=0 or presentation.quantity_kind=='DISCRETE' and quantity!=quantity.to_integral_value():raise ValueError('Cantidad positiva; las presentaciones discretas requieren enteros.')
        # Continuous allocation quantum is explicit and bounded at 0.001 units.
        scaled_integer(quantity,0 if presentation.quantity_kind=='DISCRETE' else 3)
        if quantity % presentation.allocation_increment:raise ValueError('La cantidad debe ser múltiplo del incremento físico '+str(presentation.allocation_increment)+'.')
        return QuantityVector(**{d:rounded(v*quantity,d) for d,v in presentation.coefficients.model_dump().items() if v is not None})
