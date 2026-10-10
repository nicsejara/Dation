export class RunPolling{
  constructor({later=(fn,ms)=>setTimeout(fn,ms),cancel=id=>clearTimeout(id),now=()=>Date.now()}={}){this.later=later;this.cancel=cancel;this.now=now;this.lease=null;}
  stop(){const lease=this.lease;this.lease=null;if(lease){lease.controller.abort();if(lease.timer!=null)this.cancel(lease.timer);}}
  start({runId,read,onRun,onError,interval=1500,delay=0,graceUntil=0}){
    this.stop();const lease={runId,read,onRun,onError,interval,graceUntil,controller:new AbortController(),promise:null,timer:null};this.lease=lease;
    if(delay)lease.timer=this.later(()=>this.refresh(),delay);else this.refresh();return ()=>{if(this.lease===lease)this.stop();};
  }
  refresh(){
    const lease=this.lease;if(!lease)return Promise.resolve();if(lease.promise)return lease.promise;
    if(lease.timer!=null){this.cancel(lease.timer);lease.timer=null;}
    lease.promise=(async()=>{
      try{
        const run=await lease.read(lease.runId,lease.controller.signal);if(this.lease!==lease)return;
        const terminal=['completed','error'].includes(run.status);if(terminal)this.stop();
        await lease.onRun(run);
      }catch(error){
        if(this.lease!==lease)return;
        if(error.status===404&&this.now()<lease.graceUntil)return;
        this.stop();await lease.onError(error);
      }finally{lease.promise=null;if(this.lease===lease)lease.timer=this.later(()=>this.refresh(),lease.interval);}
    })();return lease.promise;
  }
}
export const runPolling=new RunPolling();
