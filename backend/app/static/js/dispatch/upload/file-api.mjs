import {api} from '../shared.mjs';
function send(action,kind,file,{base='/api',signal}={}){
 const form=new FormData();form.append('file',file);
 return api(`${base}/datasets/${action}?dataset_type=${kind}`,{method:'POST',body:form,signal});
}
export const validateCsvFile=(kind,file,options)=>send('validate',kind,file,options);
export const storeCsvFile=(kind,file,options)=>send('upload',kind,file,options);
