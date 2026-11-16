'use strict';
const AuroraAI=(()=>{
 let worker=null,ready=false,loading=false,busy=false,failed=false,generation=0,sequence=0;
 let queued=new Map(),positions=new Map(),focused=null;
 const cache=new Map(),errors=new Map(),pending=new Map();
 const config=()=>AiCore.settings(shared.aiSettings);
 const tr=(key,fallback)=>{const value=I18n.t(key);return value===key?fallback:value;};
 function status(phase,message,backend){shared.aiStatus={phase,message,backend:backend||shared.aiStatus?.backend||''};publish();}
 function publish(){if(!output){share();}widgets();renderBoard();}
 function stop(){generation++;ready=false;loading=false;busy=false;queued.clear();if(worker)worker.terminate();worker=null;for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('IA interrompida.'));}pending.clear();}
 function request(type,data={}){return new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(Error('A IA demorou a responder. Desative e ative novamente.'));},type==='init'?120000:60000);pending.set(id,{resolve,reject,timer});worker.postMessage({id,type,...data});});}
 async function start(){
  if(output||ready||loading||failed)return;loading=true;const token=++generation;status('loading',tr('aiLoading','Carregando KataGo b18…'));
  try{worker=new Worker('/ai-worker.js');
  worker.onmessage=e=>{const d=e.data;if(d.stage){status('loading',tr('aiLoading','Carregando KataGo b18…'));return;}if(d.log)return;const p=pending.get(d.id);if(!p)return;clearTimeout(p.timer);pending.delete(d.id);d.ok?p.resolve(d.result):p.reject(Error(d.error));};
  worker.onerror=e=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('worker: '+(e.message||'Falha no motor da IA.')));}pending.clear();};
  const info=await request('init');if(token!==generation)return;loading=false;ready=true;status('ready',tr('aiReady','IA pronta')+' · b18 · '+info.backend,info.backend);refresh();}
  catch(error){if(token!==generation)return;stop();failed=true;status('error',error.message);}
 }
 function describe(g,v){return AiCore.position(g,v?{...v,aiVariation:AnalysisView.active(v)}:null,config(),LocalBoard.reconstruct);}
 function refresh(){
  if(output){widgets();return;}
  const s=config();if(!s.enabled){widgets();return;}
  const tasks=new Map(),live={},nextPositions=new Map();focused=null;
  function add(p,priority,visits,ms){const old=tasks.get(p.key);if(!old||priority>old.priority)tasks.set(p.key,{position:p,priority,visits,ms,threads:1});}
  const level=AiCore.levels[s.level];
  for(const g of state.watched){try{const p=describe(g,null);nextPositions.set(String(g.id),p);add(p,g.id===Number(shared.selected)?5:1,level.background,500);const hit=cache.get(p.key);if(hit)live[g.id]=hit.result;else if(errors.has(p.key))live[g.id]={error:errors.get(p.key)};}catch(error){live[g.id]={error:error.message};}}
  if(shared.mode==='focus'&&current())try{focused=describe(current(),view(current()));add(focused,10,s.showSuggestion?level.visits:level.background,s.showSuggestion?level.ms:500);}catch{}
  positions=nextPositions;queued=tasks;
  const focusHit=focused&&cache.get(focused.key);
  const nextFocus=focusHit?{key:focused.key,result:focusHit.result}:focused&&errors.has(focused.key)?{key:focused.key,result:{error:errors.get(focused.key)}}:null;
  const changed=JSON.stringify(shared.aiLive)!==JSON.stringify(live)||JSON.stringify(shared.aiFocus)!==JSON.stringify(nextFocus);
  shared.aiLive=live;shared.aiFocus=nextFocus;
  if(changed)share();widgets();if(!ready){start();return;}drain();
 }
 async function drain(){
  if(busy||!ready||!config().enabled)return;busy=true;const token=generation;
  try{while(token===generation&&config().enabled){
   const task=[...queued.values()].filter(t=>!errors.has(t.position.key)&&(!cache.has(t.position.key)||cache.get(t.position.key).budget<t.visits)).sort((a,b)=>b.priority-a.priority)[0];
   if(!task)break;
   try{const result=await request('analyze',task);if(token!==generation)return;cache.set(task.position.key,{result,budget:task.visits});if(cache.size>128)cache.delete(cache.keys().next().value);}
   catch(error){if(token!==generation)return;errors.set(task.position.key,error.message);if(/demorou|worker|abort|memory/i.test(error.message)){stop();failed=true;status('error',error.message);return;}}
   refresh();renderBoard();await new Promise(resolve=>setTimeout(resolve,100));
  }}finally{if(token===generation)busy=false;}
 }
 function configure(patch){failed=false;const previous=config();shared.aiSettings=AiCore.settings({...previous,...patch});const s=config();if(!s.enabled){stop();status('off',tr('aiOff','IA desativada'));}else{errors.clear();refresh();}publish();}
 function currentEvaluation(){if(!current())return null;try{const p=describe(current(),view(current()));return shared.aiFocus?.key===p.key?shared.aiFocus.result:shared.aiLive?.[current().id]?.key===p.key?shared.aiLive[current().id]:null;}catch{return null;}}
 function suggestion(){const s=config();if(!s.enabled||!s.showSuggestion||output&&!s.obsSuggestion)return null;const r=currentEvaluation();if(!r||r.error||r.best<0||r.best>=361)return null;return {type:'ai',x:r.best%19,y:Math.floor(r.best/19),color:'#2981b7'};}
 function bar(node,result){
  const s=config();node.hidden=output&&!s.obsBars;const fraction=s.enabled?AiCore.fraction(result,s.metric):null;
  node.classList.toggle('ai-pending',fraction===null);node.setAttribute('role','img');
  const text=!s.enabled?tr('aiOff','IA desativada'):result?.error||(AiCore.valid(result)?AiCore.label(result,s.metric):tr('aiWaiting','Aguardando avaliação'));
  const detail=s.enabled&&result&&!result.error?' · '+result.visits+' '+tr('aiVisits','visitas')+' · komi '+result.komi+(result.assumedKomi?' ('+tr('aiDefault','padrão')+')':''):'';
  const values=AiCore.values(s.enabled?result:null,I18n.locale||'en');
  node.querySelector('.evaluation-black').textContent=values.black;node.querySelector('.evaluation-white').textContent=values.white;node.querySelector('.evaluation-score').textContent=values.score;
  node.querySelector('.evaluation-score').title=tr('aiScore','Vantagem em pontos');
  node.title=text+detail;node.setAttribute('aria-label',text+detail);node.querySelector('i').style.width=(fraction===null?0:100*fraction)+'%';
 }
 function widgets(){
  const s=config(),r=currentEvaluation();
  if($('mainEvaluation'))bar($('mainEvaluation'),r);
  document.querySelectorAll('[data-game]').forEach(tile=>{const node=tile.querySelector('.evaluation-bar');if(node){let result=shared.aiLive?.[tile.dataset.game]||null;const g=state.watched.find(g=>String(g.id)===tile.dataset.game);try{if(result&&!result.error&&result.key!==describe(g,null).key)result=null;}catch{result=null;}bar(node,result);}});
  $('aiToggle').classList.toggle('active',s.enabled&&s.showSuggestion);$('aiToggle').setAttribute('aria-pressed',String(s.enabled&&s.showSuggestion));
  $('aiMove').textContent=s.enabled&&s.showSuggestion&&r&&!r.error?AiCore.point(r.best):'';
  const phase=shared.aiStatus?.phase;$('aiStatus').textContent=phase==='ready'?tr('aiReady','IA pronta')+' · b18 · '+shared.aiStatus.backend:phase==='loading'?tr('aiLoading','Carregando KataGo b18…'):phase==='error'?shared.aiStatus.message:tr('aiOff','IA desativada');
  $('aiEnabled').checked=s.enabled;$('aiLevel').value=s.level;$('aiMetric').value=s.metric;$('aiObsBars').checked=s.obsBars;$('aiObsSuggestion').checked=s.obsSuggestion;$('aiRules').value=s.rules;
  if(document.activeElement!==$('aiKomi'))$('aiKomi').value=s.defaultKomi;
  if(document.activeElement!==$('aiHandicapKomi'))$('aiHandicapKomi').value=s.handicapKomi;
 }
 function initialize(){
  shared.aiSettings=config();shared.aiLive={};shared.aiFocus=null;
  $('aiToggle').onclick=()=>configure({showSuggestion:!config().enabled||!config().showSuggestion,enabled:true});
  $('aiSettingsBtn').onclick=()=>{$('aiDialog').showModal();widgets();};
  const handlers={aiEnabled:['enabled','checked'],aiLevel:['level','value'],aiMetric:['metric','value'],aiObsBars:['obsBars','checked'],aiObsSuggestion:['obsSuggestion','checked'],aiRules:['rules','value'],aiKomi:['defaultKomi','value'],aiHandicapKomi:['handicapKomi','value']};
  for(const [id,[field,prop]] of Object.entries(handlers))$(id).onchange=e=>configure({[field]:e.target[prop]});
  window.addEventListener('pagehide',()=>{if(!output)stop();});
  document.addEventListener('aurora-language',widgets);if(output&&channel)channel.postMessage({auroraAIRequest:true});if(!output&&config().enabled)start();widgets();
 }
 return {initialize,refresh,widgets,suggestion};
})();
AuroraAI.initialize();
