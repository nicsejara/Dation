// Shared R6 defaults, independent of DOM and Case state.
export const defaultConfiguration=currency=>({version:1,operating_role:'SHIPPER',transport_pattern:'DIRECT',allowed_sources:['OWN','EXTERNAL'],
 active_dimensions:['pallets'],primary_dimension:'pallets',split_permitted:false,homogeneous_loads_declared:false,
 currency_policy:{currency:currency||'ARS',minor_units:2,rounding:'ROUND_HALF_UP'},own_cost_model:'OWN_OPERATING_CYCLE',external_cost_models:['PER_TRIP','PER_KM'],per_km_billing_bases:['ONE_WAY','ROUND_TRIP']});

export const defaultConfigurationV2=currency=>({...defaultConfiguration(currency),version:2,consolidation_permitted:true,resource_categories:[],cargo:{profile:'PALLETIZED',input_mode:'direct',split_policy:'INDIVISIBLE',compatibility_policy:'CATEGORIZED',co_load_pairs:[],products:[],logistic_units:[],presentations:[]}});
