"""Workspace administration, independent of commercial entitlements and engines."""
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from app.auth import require_upload_access
from app.platform.identity import platform_call

router=APIRouter(prefix='/settings')
COUNTRIES='AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split()
CURRENCIES={'ARS':'Peso argentino','BRL':'Real brasileño','CLP':'Peso chileno','COP':'Peso colombiano','EUR':'Euro','MXN':'Peso mexicano','PEN':'Sol peruano','USD':'Dólar estadounidense','UYU':'Peso uruguayo'}
OPTIONS={'countries':COUNTRIES,'languages':{'es':'Español','en':'English','pt':'Português'},'currencies':CURRENCIES,
 'weight_units':{'kg':'Kilogramos (kg)','t':'Toneladas (t)'},'distance_units':{'km':'Kilómetros (km)','mi':'Millas (mi)'},
 'logistics_units':{'units':'Unidades','pallets':'Pallets','cases':'Cajas'},
 'timezones':sorted(zone for zone in available_timezones() if not zone.startswith(('posix/','right/')) and zone!='localtime')}

@router.get('')
async def settings(ctx=Depends(require_upload_access)):
 data=await platform_call('platform_workspace_settings',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id})
 return {**data,'options':OPTIONS}

class Version(BaseModel):
 model_config=ConfigDict(extra='forbid')
 expected_updated_at:AwareDatetime

class General(Version):
 section:Literal['general']
 name:str=Field(min_length=2,max_length=120)
 country:str=Field(min_length=2,max_length=2)
 language:Literal['es','en','pt']
 timezone:str=Field(min_length=1,max_length=80)
 @field_validator('name')
 @classmethod
 def name_valid(cls,value):
  if len(value.strip())<2:raise ValueError('Completá el nombre del workspace.')
  return value.strip()
 @field_validator('country')
 @classmethod
 def country_valid(cls,value):
  if value not in COUNTRIES:raise ValueError('Elegí un país válido.')
  return value
 @field_validator('timezone')
 @classmethod
 def zone_valid(cls,value):
  try:ZoneInfo(value)
  except (ZoneInfoNotFoundError,ValueError):raise ValueError('Elegí una zona horaria válida.') from None
  if value not in OPTIONS['timezones']:raise ValueError('Elegí una zona horaria disponible.')
  return value

class Operation(Version):
 section:Literal['operation']
 currency:Literal['ARS','BRL','CLP','COP','EUR','MXN','PEN','USD','UYU']
 weight_unit:Literal['kg','t']
 distance_unit:Literal['km','mi']
 logistics_unit:Literal['units','pallets','cases']

@router.patch('')
async def update_settings(payload:Annotated[General|Operation,Field(discriminator='section')],ctx=Depends(require_upload_access)):
 return await platform_call('platform_update_workspace',{'target_workspace_id':ctx.workspace_id,'actor_user_id':ctx.user_id,
  'expected_updated_at':payload.expected_updated_at.isoformat(),'section_name':payload.section,
  'changes':payload.model_dump(exclude={'section','expected_updated_at'})})
