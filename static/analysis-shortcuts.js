'use strict';
const AnalysisShortcuts=(()=>{
 function command(event,{output=false,focus=true,hasGame=true,dialog=false,editing=false}={}){
  if(output||!focus||!hasGame||dialog||editing||event.isComposing||event.ctrlKey||event.metaKey||event.altKey)return null;
  const step=event.shiftKey?10:1;
  return {ArrowLeft:{kind:'move',delta:-step},ArrowRight:{kind:'move',delta:step},ArrowUp:{kind:'variant',delta:-1},ArrowDown:{kind:'variant',delta:1},Home:{kind:'first'},End:{kind:'last'},PageUp:{kind:'move',delta:-10},PageDown:{kind:'move',delta:10}}[event.key]||null;
 }
 return {command};
})();
if(typeof module!=='undefined')module.exports=AnalysisShortcuts;
