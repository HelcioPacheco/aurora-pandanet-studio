'use strict';
// One engine, one serial queue: Asyncify must never have overlapping calls.
importScripts('/vendor/katago/katago.js');
let M=null,size=19,ptr={},chain=Promise.resolve();
const MAX=4096;
async function modelBytes(){
 const url='/vendor/katago/b18-s9996604416.bin.gz';let cache;
 try{cache=await caches.open('aurora-katago-b18-v1');const hit=await cache.match(url);if(hit)return new Uint8Array(await hit.arrayBuffer());}catch{}
 const response=await fetch(url);if(!response.ok)throw Error('Não foi possível carregar a rede b18.');
 if(cache)try{await cache.put(url,response.clone());}catch{}
 return new Uint8Array(await response.arrayBuffer());
}
function error(){return M.ccall('kgeError','string',[],[]);}
async function initialize(options={}){
 if(!self.crossOriginIsolated)throw Error('O navegador não habilitou o isolamento necessário à IA. Atualize a página.');
 postMessage({stage:'loading',message:'Carregando KataGo b18…'});
 const bytes=await modelBytes();postMessage({stage:'loading',message:'Rede b18 carregada. Preparando memória…'});
 M=await createAuroraKata({locateFile:p=>'/vendor/katago/'+p,mainScriptUrlOrBlob:new URL('/vendor/katago/katago.js',self.location.href).href,print:()=>{},printErr:line=>postMessage({log:String(line).slice(0,400)})});
 postMessage({stage:'loading',message:'Memória pronta. Abrindo a rede b18…'});M.FS.writeFile('/b18.bin.gz',bytes,{canOwn:true});
 if(options.forceCpu)M.ccall('kgeSetForceCpu','number',['number'],[1]);
 const ok=await M.ccall('kgeLoad','number',['string','number'],['/b18.bin.gz',19],{async:true});if(!ok)throw Error(error());
 for(const [key,length] of Object.entries({locs:MAX,colors:MAX,setupLocs:625,setupColors:625,board:625,policy:626,value:5,best:1,wr:1,score:1,pv:32,pvLen:1,visits:1,reused:1}))ptr[key]=M._malloc(length*4);
 return {backend:M.ccall('kgeBackendIsGpu','number',[],[])?'WebGPU':'CPU',model:'b18',version:M.ccall('kgeModelVersion','number',[],[])};
}
function write(p,values){M.HEAP32.set(values,p>>2);}
async function analyze(req){
 if(!M)throw Error('IA não iniciada.');
 const p=req.position;if(p.size!==size)throw Error('Nesta versão, a IA analisa tabuleiros 19 × 19.');
 if(p.moves.length>MAX)throw Error('Histórico de análise muito longo.');
 M.ccall('kgeStopSearch','number',[],[]);
 write(ptr.locs,p.moves.map(m=>m.loc));write(ptr.colors,p.moves.map(m=>m.col));
 write(ptr.setupLocs,p.setup.map(m=>m.loc));write(ptr.setupColors,p.setup.map(m=>m.col));
 let ok=M.ccall('kgeSetPositionConfig','number',['string','number','number','number','number'],[p.rules,ptr.setupLocs,ptr.setupColors,p.setup.length,p.firstPlayer]);if(!ok)throw Error(error());
 const start=performance.now();
 ok=await M.ccall('kgeEvalSeqKata','number',Array(9).fill('number'),[ptr.locs,ptr.colors,p.moves.length,p.toPlay,p.komi,ptr.board,ptr.policy,ptr.value,0],{async:true});if(!ok)throw Error(error());
 const actual=Array.from(M.HEAP32.subarray(ptr.board>>2,(ptr.board>>2)+size*size));
 if(actual.some((v,i)=>v!==p.expected[i]))throw Error('A posição da IA divergiu do tabuleiro. Avaliação descartada.');
 const values=Array.from(M.HEAPF32.subarray(ptr.value>>2,(ptr.value>>2)+5));
 const policy=Array.from(M.HEAPF32.subarray(ptr.policy>>2,(ptr.policy>>2)+size*size+1));
 let best=policy.indexOf(Math.max(...policy));if(best===size*size)best=-1;
 let result={blackWinrate:values[1]+values[2]/2,blackScore:-values[4],best,visits:1};
 if(req.visits>1){
  ok=await M.ccall('kgeSearchKata','number',Array(16).fill('number'),[ptr.locs,ptr.colors,p.moves.length,p.toPlay,p.komi,req.visits,req.ms,req.threads||1,ptr.best,ptr.wr,ptr.score,ptr.pv,32,ptr.pvLen,ptr.visits,ptr.reused],{async:true});
  if(!ok)throw Error(error());
  const wr=M.HEAPF32[ptr.wr>>2],score=M.HEAPF32[ptr.score>>2];
  result={best:M.HEAP32[ptr.best>>2],blackWinrate:p.toPlay===1?wr:1-wr,blackScore:p.toPlay===1?score:-score,visits:M.HEAP32[ptr.visits>>2]};
 }
 if(!Number.isFinite(result.blackWinrate)||!Number.isFinite(result.blackScore))throw Error('A IA retornou uma avaliação inválida.');
 return {...result,ms:Math.round(performance.now()-start),key:p.key,komi:p.komi,rules:p.rules,assumedKomi:p.assumedKomi};
}
self.onmessage=e=>{const req=e.data;chain=chain.then(async()=>{
 try{const result=req.type==='init'?await initialize(req):await analyze(req);postMessage({id:req.id,ok:true,result});}
 catch(err){postMessage({id:req.id,ok:false,error:String(err.message||err)});}
});};
