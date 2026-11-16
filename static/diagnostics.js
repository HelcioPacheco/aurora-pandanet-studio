'use strict';
if(new URLSearchParams(location.search).has('diagnostics')){
 const panel=document.createElement('aside');panel.style.cssText='margin:20px;padding:16px;border:1px solid #789;background:var(--panel);color:var(--text);position:relative;z-index:10';
 panel.innerHTML='<h2>Diagnóstico local</h2><p>Teste de navegação, incluindo espera pelos quadros. A posição original é restaurada no final.</p><button id="runNavigationTest">Medir 60 mudanças de posição</button><pre id="navigationTestResult" style="white-space:pre-wrap"></pre>';
 document.body.append(panel);
 const events=[],longTasks=[];let recording=false;
 try{new PerformanceObserver(list=>{if(recording)for(const e of list.getEntries())events.push({name:e.name,duration:e.duration,inputDelay:e.processingStart-e.startTime,handler:e.processingEnd-e.processingStart});}).observe({type:'event',buffered:true,durationThreshold:16});}catch{}
 try{new PerformanceObserver(list=>{if(recording)for(const e of list.getEntries())longTasks.push(e.duration);}).observe({type:'longtask',buffered:true});}catch{}
 const frame=()=>new Promise(resolve=>requestAnimationFrame(resolve));
 const stats=values=>{const v=[...values].sort((a,b)=>a-b);return {samples:v.length,medianMs:+v[Math.floor(v.length*.5)].toFixed(2),p95Ms:+v[Math.min(v.length-1,Math.floor(v.length*.95))].toFixed(2),maxMs:+v.at(-1).toFixed(2)};};
 document.getElementById('runNavigationTest').onclick=async()=>{
  const g=current();if(!g)return;const button=document.getElementById('runNavigationTest'),saved=JSON.parse(JSON.stringify(view(g)));button.disabled=true;events.length=0;longTasks.length=0;recording=true;
  const handlers=[],frames=[],moves=g.moves.length;let requests=0;const fetchOriginal=window.fetch;window.fetch=(...args)=>{requests++;return fetchOriginal(...args);};
  try{
   for(let i=0;i<60;i++){
    await frame();const start=performance.now();navigate(0,Math.max(0,moves-(i%Math.min(moves+1,30))));handlers.push(performance.now()-start);await frame();await frame();frames.push(performance.now()-start);
   }
   const summary={environment:navigator.userAgent,eventTimingSupported:PerformanceObserver.supportedEntryTypes?.includes('event')||false,version:document.querySelector('footer')?.textContent,renderer:document.querySelector('#mainBoard canvas')?'canvas':'svg',handlers:stats(handlers),throughNextPaintOpportunity:stats(frames),requests,domNodes:document.querySelectorAll('*').length,svgUses:document.querySelectorAll('use').length,longTasksMs:[...longTasks],eventTimings:[...events],storageBytes:new Blob([localStorage.getItem('aurora-layout')||'']).size};
   document.getElementById('navigationTestResult').textContent=JSON.stringify(summary,null,2);
  }catch(e){document.getElementById('navigationTestResult').textContent=e.stack;}
  finally{recording=false;window.fetch=fetchOriginal;Object.assign(view(g),saved);share();renderBoard();button.disabled=false;}
 };
}
