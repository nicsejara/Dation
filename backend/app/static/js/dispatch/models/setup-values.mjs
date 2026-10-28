// Pure setup value conversions. No runtime, graph or permission selection.
export function draftSignature(value){
 return JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
}
export function horizonEnd(start,type){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(start)||type==='CUSTOM')return null;
 const date=new Date(start+'T12:00:00Z');if(Number.isNaN(date.valueOf()))return null;
 if(type==='WEEKLY')date.setUTCDate(date.getUTCDate()+6);
 if(type==='MONTHLY')date.setUTCMonth(date.getUTCMonth()+1,0);
 return date.toISOString().slice(0,10);
}
export function percentToRatio(value){
 if(!/^(?:100(?:\.0{1,2})?|[0-9]{1,2}(?:\.[0-9]{1,2})?)$/.test(String(value)))throw new Error('Ingresá un porcentaje de 0 a 100, con hasta dos decimales.');
 const [integer,fraction='']=String(value).split('.'),basis=Number(integer)*100+Number(fraction.padEnd(2,'0'));
 return basis===10000?'1':('0.'+String(basis).padStart(4,'0')).replace(/0+$/,'').replace(/\.$/,'');
}
export function ratioToPercent(value){return String(Math.round(Number(value)*10000)/100);}
