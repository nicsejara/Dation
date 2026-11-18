"""Saga 10 immutable catalog, scoped to one published Model configuration.

No database access, global mutable catalog, engine activation or implicit SKU.
"""
from typing import Literal
from pydantic import Field, StrictBool, model_validator
from .base import ContractModel, Identifier, Positive, NonNegative, Count


class Mass(ContractModel):
    value: NonNegative
    unit: Literal['kg', 't'] = 'kg'


class Volume(ContractModel):
    value: Positive
    unit: Literal['m3', 'l'] = 'm3'


class Dimensions(ContractModel):
    length: Positive
    width: Positive
    height: Positive
    unit: Literal['m', 'cm'] = 'm'


class Product(ContractModel):
    product_id: Identifier
    name: str = Field(min_length=1, max_length=120)
    code: Identifier | None = None
    category: str | None = Field(default=None, max_length=120)
    unit_label: str = Field(default='unidad', min_length=1, max_length=40)
    units_per_package: Count = Field(default=1, ge=1, le=1000000)
    gross_mass: Mass | None = None
    net_mass: Mass | None = None
    dimensions: Dimensions | None = None  # informational; never used as loaded volume
    density_kg_per_m3: Positive | None = None
    compatibility_groups: tuple[Identifier, ...] = Field(default=(), max_length=20)

    @model_validator(mode='after')
    def physical_mass(self):
        def kg(m):return m.value * (1000 if m.unit == 't' else 1)
        if not self.name.strip() or not self.unit_label.strip():raise ValueError('Nombre y unidad del producto requeridos.')
        if any(m is not None and m.value == 0 for m in (self.gross_mass, self.net_mass)):
            raise ValueError('El peso del producto debe ser positivo.')
        if self.gross_mass and self.net_mass and kg(self.gross_mass) < kg(self.net_mass):
            raise ValueError('El peso bruto no puede ser menor al neto.')
        if len(set(self.compatibility_groups)) != len(self.compatibility_groups):raise ValueError('No repitas categorías de carga.')
        return self


class LogisticUnit(ContractModel):
    logistic_unit_id: Identifier
    label: str = Field(min_length=1, max_length=120)
    type: Literal['PALLET', 'BOX', 'CRATE', 'BIG_BAG', 'OTHER']
    empty_dimensions: Dimensions | None = None
    tare_mass: Mass = Field(default_factory=lambda: Mass(value='0'))
    structural_limit_kg: Positive | None = None


class PresentationComponent(ContractModel):
    product_id: Identifier
    quantity: Positive


class LoadPresentation(ContractModel):
    presentation_id: Identifier
    label: str = Field(min_length=1, max_length=120)
    logistic_unit_id: Identifier | None = None
    quantity_kind: Literal['DISCRETE', 'CONTINUOUS'] = 'DISCRETE'
    quantity_unit: Literal['presentation', 'kg', 't', 'm3', 'l'] = 'presentation'
    components: tuple[PresentationComponent, ...] = Field(min_length=1, max_length=30)
    loaded_dimensions: Dimensions | None = None
    gross_mass: Mass | None = None
    external_volume: Volume | None = None
    density_kg_per_m3: Positive | None = None
    extra_tare_mass: Mass = Field(default_factory=lambda: Mass(value='0'))
    # These facts do not assert stacking/packing feasibility.
    stackable_metadata: StrictBool | None = None
    orientation_metadata: str | None = Field(default=None, max_length=120)

    @model_validator(mode='after')
    def bounded_composition(self):
        if not self.label.strip():raise ValueError('La presentación necesita un nombre.')
        if len({c.product_id for c in self.components}) != len(self.components):raise ValueError('Un componente por producto; sumá las cantidades explícitamente.')
        if self.gross_mass and not self.gross_mass.value:raise ValueError('El peso bruto debe ser positivo.')
        if self.quantity_kind == 'DISCRETE':
            if self.quantity_unit != 'presentation':raise ValueError('Las unidades discretas se cuentan por presentación completa.')
            if any(c.quantity != c.quantity.to_integral_value() for c in self.components):raise ValueError('Una presentación prearmada contiene unidades enteras de producto.')
        elif self.quantity_unit == 'presentation' or self.logistic_unit_id or len(self.components) != 1:
            raise ValueError('El granel continuo usa una medida física, un material y ninguna unidad logística anidada.')
        elif self.components[0].quantity!=1:raise ValueError('El granel continuo declara un material por unidad física; no contiene bultos anidados.')
        return self


class CargoConfiguration(ContractModel):
    profile: Literal['PALLETIZED', 'PACKAGED', 'DRY_BULK', 'LIQUID_BULK', 'SPECIALIZED', 'MIXED'] = 'PALLETIZED'
    input_mode: Literal['direct', 'catalog'] = 'direct'
    split_policy: Literal['INDIVISIBLE', 'DISCRETE', 'CONTINUOUS'] = 'INDIVISIBLE'
    compatibility_policy: Literal['UNIFORM_DECLARED', 'CATEGORIZED'] = 'CATEGORIZED'
    co_load_pairs: tuple[tuple[Identifier, Identifier], ...] = Field(default=(), max_length=100)
    products: tuple[Product, ...] = Field(default=(), max_length=100)
    logistic_units: tuple[LogisticUnit, ...] = Field(default=(), max_length=50)
    presentations: tuple[LoadPresentation, ...] = Field(default=(), max_length=200)

    def can_co_load(self, left, right):
        if self.compatibility_policy == 'UNIFORM_DECLARED':return True
        # Conservative: different groups require an explicit unordered pair.
        allowed={frozenset(p) for p in self.co_load_pairs}
        return bool(left and right) and all(a == b or frozenset((a,b)) in allowed for a in left for b in right)

    @model_validator(mode='after')
    def references_and_policies(self):
        for items,key in ((self.products,'product_id'), (self.logistic_units,'logistic_unit_id'), (self.presentations,'presentation_id')):
            ids=[getattr(x,key) for x in items]
            if len(ids)!=len(set(ids)):raise ValueError('Los identificadores del catálogo deben ser únicos: '+key)
        names=[p.name.strip().casefold() for p in self.products];codes=[p.code.casefold() for p in self.products if p.code]
        if len(names)!=len(set(names)) or len(codes)!=len(set(codes)):raise ValueError('No repitas nombres o códigos de producto.')
        pairs=[frozenset(p) for p in self.co_load_pairs]
        if len(pairs)!=len(set(pairs)):raise ValueError('No repitas pares simétricos de compatibilidad.')
        products={p.product_id:p for p in self.products};units={u.logistic_unit_id:u for u in self.logistic_units}
        if self.input_mode == 'catalog' and (not products or not self.presentations):raise ValueError('Agregá al menos un producto y una presentación.')
        if self.input_mode == 'direct' and (products or units or self.presentations):raise ValueError('Los datos directos no mezclan un catálogo oculto; quitá o guardá aparte sus borradores.')
        for presentation in self.presentations:
            if presentation.logistic_unit_id and presentation.logistic_unit_id not in units:raise ValueError('La presentación refiere una unidad logística inexistente.')
            if any(c.product_id not in products for c in presentation.components):raise ValueError('La presentación refiere un producto inexistente.')
            if presentation.quantity_kind=='CONTINUOUS' and any(products[c.product_id].units_per_package!=1 for c in presentation.components):raise ValueError('El granel continuo no usa unidades por bulto.')
            if self.split_policy == 'DISCRETE' and presentation.quantity_kind != 'DISCRETE':raise ValueError('El fraccionamiento discreto no admite granel continuo.')
            groups=[products[c.product_id].compatibility_groups for c in presentation.components]
            if self.compatibility_policy == 'CATEGORIZED' and any(not g for g in groups):raise ValueError('Declarar categorías de compatibilidad para cada producto utilizado.')
            for left in groups:
                for right in groups:
                    if not self.can_co_load(left,right):raise ValueError('La presentación mixta contiene productos no autorizados para compartir carga.')
        return self
