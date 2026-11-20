// Necessary comparison of nominal rigid volumes, never a packing certificate.
// Decimal inputs are exact integer fractions; relative noise band is 1e-12.
const SCALE=1000000000000n;
export const COHERENCE_ERROR='La suma de los volúmenes declarados de las cajas supera el volumen exterior de la unidad. Revisá cantidad o medidas.';
export const COHERENCE_SCOPE='Volumen nominal de los bultos comparado con el volumen exterior. No certifica el acomodamiento físico.';
function decimal(value){
 const s=String(value??'').trim();if(!s||s.length>256||!Number.isFinite(Number(s))||Number(s)<=0)return null;
 const m=s.match(/^(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i)||s.match(/^()(?:\.(\d+))(?:e([+-]?\d+))?$/i);if(!m)return null;
 const exponent=Number(m[3]||0);if(Math.abs(exponent)>308)return null;
 const n=BigInt((m[1]||'0')+(m[2]||'')),scale=(m[2]||'').length-exponent;
 return scale>=0?{n,d:10n**BigInt(scale)}:{n:n*10n**BigInt(-scale),d:1n};
}
const multiply=(a,b)=>a&&b?{n:a.n*b.n,d:a.d*b.d}:null;
function dimensions(d){if(!d||!['cm','m'].includes(d.unit))return null;let v=multiply(multiply(decimal(d.length),decimal(d.width)),decimal(d.height));if(v&&d.unit==='cm')v={n:v.n,d:v.d*1000000n};return v;}
function number(f){const a=f.n.toString(),b=f.d.toString(),lead=s=>Number(s.slice(0,16))/10**(Math.min(s.length,16)-1);return lead(a)/lead(b)*10**(a.length-b.length);}
export function evaluateCoherence(unit,product){
 const pending={status:'pending',comparable:false,blocking:false,exterior:null,individual:null,total:null,ratio:null};
 const count=Number(product.quantity);if(!Number.isSafeInteger(count)||count<=0)return pending;
 const exterior=['BIG_BAG','OTHER'].includes(unit.type)?decimal(unit.exteriorVolume):dimensions({length:unit.length,width:unit.width,height:unit.height,unit:unit.measure});
 const individual=dimensions(product);if(!exterior||!individual)return pending;
 const total=multiply(individual,{n:BigInt(count),d:1n}),left=total.n*exterior.d,right=exterior.n*total.d,difference=left-right,absolute=difference<0n?-difference:difference;
 const ratio=number({n:left,d:right}),values={exterior:number(exterior),individual:number(individual),total:number(total),ratio};
 if(!Object.values(values).every(Number.isFinite)||values.exterior<=0)return pending;
 const comparable=product.packageType==='caja';
 const status=!comparable?'unverified':difference*SCALE>right?'invalid_rigid':absolute*SCALE<=right?'warning_equal':'informational';
 return {status,comparable,blocking:status==='invalid_rigid',...values};
}
export function coherenceCopy(result){
 return result.status==='invalid_rigid'?COHERENCE_ERROR:result.status==='warning_equal'?'Los volúmenes nominales son iguales. No se consideraron espacios libres ni geometría real.':result.status==='unverified'?'Comparación orientativa. Este tipo de bulto no admite una validación volumétrica rígida automática.':result.status==='pending'?'Pendiente: completá las medidas y la cantidad para comparar.':'La comparación de volúmenes no certifica el acomodamiento físico.';
}
