// Exercise the actual browser helpers without loading the application or connecting.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/static/app.js','utf8');
const helpers=source.slice(source.indexOf('function letterAt('),source.indexOf('function pin(g)'));
vm.runInThisContext(helpers);
assert.equal(letterAt(0),'A');assert.equal(letterAt(25),'Z');assert.equal(letterAt(26),'AA');assert.equal(letterAt(701),'ZZ');
let marks=renumberMarks([{type:'label',x:0},{type:'number',x:1},{type:'label',x:2},{type:'number',x:3},{type:'label',x:4}]);
assert.deepEqual(marks.map(m=>m.text),['A','1','B','2','C']);
marks=renumberMarks(marks.filter(m=>m.x!==2&&m.x!==1));assert.deepEqual(marks.map(m=>m.text),['A','1','B']);
assert.equal(renumberMarks([...marks,{type:'label',x:5}]).at(-1).text,'C');
const board={size:5,stones:[[0,0,'B'],[1,0,'B'],[0,1,'W']]};
const group=groupLiberties(board,0,0);assert.equal(group.stones.size,2);assert.deepEqual(group.points.sort(),[[1,1],[2,0]]);
assert.equal(groupLiberties(board,4,4),null);
const overlay=displayMarks(board,[{type:'liberties',x:1,y:0,color:'#123'}]);assert.equal(overlay[0].text,'2');assert.equal(overlay.filter(m=>m.type==='circle').length,2);
assert.equal(groupLiberties({size:3,stones:[[0,0,'B'],[1,0,'B'],[0,1,'B'],[1,1,'B']]},0,0).points.length,4);
console.log('Annotation tests passed: sequences, deletion, groups, edges and unique liberties.');
