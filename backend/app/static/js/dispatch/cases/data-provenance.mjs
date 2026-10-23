const CASE_VIEWS=new Set(['logistics-data','logistics-map','logistics-config','decision-dashboard']);

/** Read existing provenance only after it belongs to the current resource.
 * A filename, category or a cached sample from another Case is never authority. */
export function hasDemoData(state={},route={},view=''){
  if(!CASE_VIEWS.has(view))return false;
  const current=state.decisionCase;
  if(route.caseId&&route.caseId!==current?.id)return false;
  if(current?.persisted&&state.caseContext?.caseId!==current.id)return false;
  const run=state.run;
  if(route.runId&&run&&run.id!==route.runId)return false;
  if(route.runId&&run?.decision_case_id&&run.decision_case_id!==current?.id)return false;
  return ['orders','fleet'].some(kind=>{
    const dataset=state[kind],expected=current?.inputs?.[kind+'_dataset_id'];
    const runInput=route.runId&&run?.[kind+'_dataset_id'];
    return dataset?.is_sample===true&&(!expected||dataset.id===expected)&&(!runInput||dataset.id===runInput);
  });
}
