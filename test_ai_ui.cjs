const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),A=require('./static/ai-core.js'),L=require('./static/local-board.js');
const nodes=new Map();function node(id){if(!nodes.has(id))nodes.set(id,{classList:{toggle(){}},setAttribute(){},parts:new Map(),querySelector(selector){if(!this.parts.has(selector))this.parts.set(selector,{style:{}});return this.parts.get(selector);},style:{}});return nodes.get(id);}
const game={id:1,size:19,komi:6.5,moves:[{color:'B',point:'D16'},{color:'W',point:'Q4'}]};
const requests=[],workers=[];class Worker{constructor(){workers.push(this);}postMessage(req){requests.push(req);}terminate(){this.stopped=true;}reply(req,result){this.onmessage({data:{id:req.id,ok:true,result}});}}
function environment(output=false){return {AiCore:A,LocalBoard:L,AnalysisView:{active:()=>[]},shared:{aiSettings:{enabled:true,showSuggestion:true},mode:'focus',selected:1,aiLive:{}},state:{watched:[game]},output,Worker,I18n:{t:k=>k},$:node,current:()=>game,view:()=>contextView,share(){},renderBoard(){},channel:{postMessage(){}},document:{querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(){}},setTimeout,clearTimeout,Map,Promise,Error,console};}
let contextView={cursor:null,variation:[]};const scope=environment();vm.createContext(scope);vm.runInContext(fs.readFileSync('./static/ai-ui.js','utf8')+';globalThis.api= AuroraAI;',scope);
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 const w=workers[0];assert.equal(requests[0].type,'init');w.reply(requests.shift(),{backend:'WebGPU'});await tick();
 const old=requests.shift();assert.equal(old.type,'analyze');contextView={cursor:1,variation:[]};scope.api.refresh();
 w.reply(old,{key:old.position.key,best:72,blackWinrate:.55,blackScore:1,visits:4});await tick();
 assert.equal(node('mainEvaluation').querySelector('.evaluation-black').textContent,'● —');
 assert.equal(scope.api.suggestion(),null,'completed analysis of old position must not appear on current position');
 await new Promise(r=>setTimeout(r,130));const fresh=requests.shift();assert.equal(fresh.position.moves.length,1,'new focused position has priority');
 w.reply(fresh,{key:fresh.position.key,best:300,blackWinrate:.6,blackScore:2,visits:4});await tick();assert.equal(scope.api.suggestion().x,15);assert.equal(node('mainEvaluation').querySelector('.evaluation-black').textContent,'● 60.0%');assert.equal(node('mainEvaluation').querySelector('.evaluation-score').textContent,'● +2.0');
 node('aiEnabled').onchange({target:{checked:false}});assert(w.stopped);assert.equal(scope.api.suggestion(),null);
 node('aiToggle').onclick();assert.equal(scope.shared.aiSettings.showSuggestion,true,'AI button after disabling must show the suggestion');node('aiEnabled').onchange({target:{checked:false}});
 const before=workers.length,obs=environment(true);vm.createContext(obs);vm.runInContext(fs.readFileSync('./static/ai-ui.js','utf8'),obs);assert.equal(workers.length,before,'OBS must not create its own engine');
 console.log('AI UI: position changes reject stale suggestions, focused queue priority, shutdown and OBS sharing passed.');
})().catch(e=>{console.error(e);process.exitCode=1});
