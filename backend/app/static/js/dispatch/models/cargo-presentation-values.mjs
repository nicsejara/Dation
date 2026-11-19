// Display formatting only. Domain coefficients remain Decimal/backend owned.
const format=new Intl.NumberFormat('es-AR',{minimumFractionDigits:2,maximumFractionDigits:5});
export const volumeNumber=value=>format.format(value);
export const volumeText=value=>value===null||value===undefined?'Sin declarar':volumeNumber(value)+' m³';
// Changing the input unit must not reinterpret the same length. Shift decimal
// strings exactly; never serialize a rounded binary floating-point conversion.
export function dimensionInUnit(value,from,to){
 if(value===''||from===to)return value;
 const m=String(value).match(/^(-?)(\d*)(?:\.(\d*))?(?:e([+-]?\d+))?$/i);if(!m||!(m[2]||m[3]))return value;
 const exp=Number(m[4]||0);if(!Number.isSafeInteger(exp)||Math.abs(exp)>1000)return value;
 const shift=from==='cm'&&to==='m'?2:from==='m'&&to==='cm'?-2:0;if(!shift)return value;
 let digits=(m[2]||'0')+(m[3]||''),scale=(m[3]||'').length-exp+shift,whole,fraction='';
 if(scale<=0)whole=digits+'0'.repeat(-scale);else{digits=digits.padStart(scale+1,'0');whole=digits.slice(0,-scale);fraction=digits.slice(-scale).replace(/0+$/,'');}
 whole=whole.replace(/^0+(?=\d)/,'');return m[1]+whole+(fraction?'.'+fraction:'');
}
