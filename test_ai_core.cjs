const assert=require('node:assert/strict'),A=require('./static/ai-core.js'),L=require('./static/local-board.js');
const g={id:'ai-test',size:19,moves:[{color:'B',point:'D16'},{color:'W',point:'Q4'}],komi:0,rules:'Japanese'};
const before=JSON.stringify(g),p=A.position(g,null,{},L.reconstruct);
assert.equal(p.komi,0);assert.equal(p.assumedKomi,false);assert.deepEqual(p.moves,[{loc:60,col:1},{loc:300,col:2}]);assert.equal(p.expected[60],1);assert.equal(p.toPlay,1);assert.equal(JSON.stringify(g),before);
const v=A.position(g,{cursor:1,aiVariation:[{color:'W',point:'C3'}]}, {},L.reconstruct);
assert.equal(v.moves[1].loc,306);assert.notEqual(v.key,p.key);assert.equal(v.expected[300],0);
assert.notEqual(A.position({...g,komi:6.5},null,{},L.reconstruct).key,p.key);
assert.notEqual(A.position(g,null,{rules:'chinese'},L.reconstruct).key,p.key);
const h={id:'handicap',size:19,handicap:2,moves:[{color:'B',point:'Handicap',extra:['2']},{color:'W',point:'R4'}]};
const hp=A.position(h,null,{},L.reconstruct);assert.equal(hp.setup.length,2);assert.equal(hp.moves.length,1);assert.equal(hp.firstPlayer,2);assert.equal(hp.komi,.5);
const sp=A.position({id:'setup',size:19,setup:[[3,3,'B'],[15,15,'W']],next_color:'W',moves:[{color:'W',point:'PASS'}]},null,{},L.reconstruct);
assert.equal(sp.setup.length,2);assert.equal(sp.moves[0].loc,-1);assert.equal(sp.toPlay,1);
assert.throws(()=>A.position({...g,size:9},null,{},L.reconstruct),/19/);
assert.throws(()=>A.ruleName('unknown'),/Regras/);
assert.equal(A.fraction({error:'bad'},'winrate'),null);assert.equal(A.fraction(null,'score'),null);
assert.equal(A.fraction({blackWinrate:.25,blackScore:0},'winrate'),.25);assert.equal(A.fraction({blackScore:0,blackWinrate:.5},'score'),.5);
assert.equal(A.point(72),'Q16');assert.equal(A.point(-1),'PASS');
console.log('AI: history, variations, setup, handicap, passes, rules, komi and position keys passed.');

assert.deepEqual(A.values(null),{black:'● —',white:'○ —',score:'—'});
assert.deepEqual(A.values({blackWinrate:.684,blackScore:-2.3},'pt-BR'),{black:'● 68,4%',white:'○ 31,6%',score:'○ +2,3'});
for(const r of [{blackWinrate:NaN,blackScore:0},{blackWinrate:.5},{blackWinrate:2,blackScore:1},{error:'unavailable'}]){assert.equal(A.fraction(r,'winrate'),null);assert.equal(A.values(r).score,'—');}
