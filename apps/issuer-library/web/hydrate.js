'use strict';
// /api/workspace sends each distinct handoff's sections once, under its digest (data.handoffs); every
// output names its handoff by sha256. The screens read out.sections, so this puts them back before
// the page's globals are assigned. Outputs with the same digest share one array; the screens only read it.
function hydrate(data){
  for(const out of Object.values(data.outputs||{})){
    const sections=data.handoffs?.[out.sha256];
    if(!sections)throw new Error(`The workspace did not send the content of ${out.id}`);
    out.sections=sections;
  }
  return data;
}
