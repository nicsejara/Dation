import {FOUNDATION} from './foundation.mjs';
export const getDatasetDisplayName=row=>row.label||row.canonical_filename||row.original_filename||'Dataset';
export const getDatasetTypePresentation=row=>FOUNDATION.datasetTypes[row.dataset_type]||row.dataset_type||'Sin registro';
export const getValidationPresentation=row=>({label:{validated:'Validado',issues:'Con observaciones',unknown:'Sin registro'}[row.validation]||'Sin registro',tone:{validated:'success',issues:'warning'}[row.validation]||'neutral'});
export const getLifecyclePresentation=row=>({label:row.deletion_pending?'Eliminación pendiente':row.archived_at?'Archivado':'Activo',tone:row.deletion_pending?'warning':'neutral'});
export const getUsagePresentation=row=>`${row.case_count||0} Decision ${row.case_count===1?'Case':'Cases'}`;
export const datasetNumber=value=>value==null?'—':new Intl.NumberFormat('es').format(value);
export const datasetBytes=value=>value==null?'Sin registro':value<1024?value+' B':value<1048576?(value/1024).toFixed(1)+' KB':(value/1048576).toFixed(1)+' MB';
