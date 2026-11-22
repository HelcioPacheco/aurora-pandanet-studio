const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),StateOrder=require('./static/state-order.js');
const initial={server_id:'server-A',session_id:'login-A',revision:10,room_id:51,joining_room:null,watched:[]};
const ctx=vm.createContext({state:initial,StateOrder,lastMoves:new Map(),boardCache:new Map(),LocalBoard:{clear(){}},shared:{session:'login-A',numberMode:'1',markLastMove:false,aiSettings:{enabled:true,level:'light'},aiLive:{old:{key:'old'}},aiFocus:{key:'old'}},MoveNumbers:{normalize:x=>x},performance:{now:()=>0},output:false,share(){},drag:false,render(){}});
const source=fs.readFileSync('./static/app.js','utf8');vm.runInContext(source.slice(source.indexOf('function acceptState('),source.indexOf('let polling=false;')),ctx);
const apply=next=>{ctx.packet=next;vm.runInContext('acceptState(packet)',ctx);return ctx.state;};
const main={...initial,revision:14,room_id:0,available:[{id:70}],league_id:null};assert.equal(apply(main).room_id,0);
// Delayed HTTP, stale SSE and even a packet from an earlier login must not roll back.
for(const old of [{...initial,revision:11},{...initial,revision:13},{...initial,revision:12,session_id:'older-login'}]){assert.equal(apply(old).room_id,0);assert.equal(ctx.state.revision,14);assert.equal(ctx.state.available[0].id,70);}
assert.equal(StateOrder.room({...initial,joining_room:0}),0);assert.equal(StateOrder.room({...initial,joining_room:null}),51);
assert.equal(StateOrder.accept(main,{...main,revision:14}),false);
assert.equal(apply({...main,revision:15}).room_id,0);
// A genuinely restarted server is allowed to start counting from zero.
assert.equal(apply({...initial,server_id:'server-B',session_id:'new-login',revision:1,room_id:0}).revision,1);
assert.equal(ctx.shared.markLastMove,false);assert.equal(ctx.shared.aiSettings.enabled,true);assert.equal(ctx.shared.aiSettings.level,'light');assert.equal(Object.keys(ctx.shared.aiLive).length,0);assert.equal(ctx.shared.aiFocus,null);
console.log('State ordering passed: real acceptState rejects late snapshots; room zero, earlier logins and server restart are handled.');
