'use strict';
// State can change many times between frames; only the final position is painted.
class FrameQueue{
 constructor(request=callback=>requestAnimationFrame(callback)){this.request=request;this.pending=null;this.job=null;}
 enqueue(job){this.job=job;if(this.pending!==null)return;this.pending=this.request(()=>{this.pending=null;const next=this.job;this.job=null;next();});}
}
if(typeof module!=='undefined')module.exports=FrameQueue;
