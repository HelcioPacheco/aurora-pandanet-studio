const assert=require('node:assert/strict'),engine=require('./static/local-board.js'),{AnalysisView:A}=require('./static/analysis-view.js'),shortcuts=require('./static/analysis-shortcuts.js');
const g={id:50,size:9,moves:[{color:'B',point:'D4'},{color:'W',point:'F6'},{color:'B',point:'E5'},{color:'W',point:'C7'}]},initial=JSON.stringify(g),v={cursor:1,variation:[],notes:{}};
A.play(g,v,'C3',engine);A.play(g,v,'F3',engine);const first=v.selectedLine;assert.equal(A.lines(g,v).length,1);
A.navigate(g,v,-1);A.play(g,v,'G3',engine);const second=v.selectedLine;assert.notEqual(second,first);assert.equal(A.lines(g,v).length,2);assert.deepEqual(A.lines(g,v).find(l=>l.id===first).moves.map(m=>m.point),['C3','F3']);
// A click on an existing sibling follows its saved continuation without creating a line.
A.navigate(g,v,-1);assert.equal(A.play(g,v,'F3',engine).reused,true);assert.equal(v.selectedLine,first);assert.equal(A.lines(g,v).length,2);
A.navigate(g,v,0,1);assert.equal(A.count(v),0);A.navigate(g,v,-1);assert.equal(A.timeline(g,v).ply,0);A.navigate(g,v,1);assert.equal(A.count(v),0);A.navigate(g,v,1);assert.equal(A.active(v)[0].point,'C3');
// Returning to the recorded game, live view and serialization preserve every line.
A.main(g,v);A.navigate(g,v,0,1);const reused=A.play(g,v,'c3',engine);assert.equal(reused.reused,true);assert.equal(A.lines(g,v).length,2);A.main(g,v,true);assert.equal(v.cursor,null);assert.equal(A.lines(g,v).length,2);
let restored=JSON.parse(JSON.stringify(v));A.selectLine(g,restored,second,true);assert.equal(A.active(restored).at(-1).point,'G3');A.navigate(g,restored,0,0);assert.equal(A.timeline(g,restored).max,3);A.navigate(g,restored,0,3);assert.equal(A.active(restored).at(-1).point,'G3');
// Moving between siblings keeps the same depth; clicking the existing main move re-enters it.
assert.equal(A.cycle(g,restored,-1),true);assert.equal(A.active(restored).at(-1).point,'F3');A.navigate(g,restored,0,1);A.play(g,restored,'F6',engine);assert.equal(restored.selectedLine,null);assert.equal(restored.cursor,2);assert.equal(A.lines(g,restored).length,2);
// Clicking a shared recorded prefix while a later variation is selected must not jump ahead.
A.selectLine(g,restored,first);A.navigate(g,restored,0,0);const atOne=A.play(g,restored,'D4',engine);assert.equal(atOne.board.ply,1);assert.equal(atOne.board.stones.length,1);assert.equal(A.timeline(g,restored).ply,1);
const snapshot=JSON.stringify(restored);assert.throws(()=>A.play(g,restored,'D4',engine));assert.equal(JSON.stringify(restored),snapshot);assert.equal(JSON.stringify(g),initial);
// Incoming official moves do not move a pinned review cursor or erase saved variations.
const live=JSON.parse(JSON.stringify(g));live.moves.push({color:'B',point:'A1'});assert.equal(A.lines(live,restored).length,2);assert.equal(A.timeline(live,restored).ply,1);
const other={cursor:null,variation:[]};assert.equal(A.lines(live,other).length,0);
assert.equal(shortcuts.command({key:'ArrowLeft'}).delta,-1);assert.equal(shortcuts.command({key:'ArrowRight',shiftKey:true}).delta,10);assert.equal(shortcuts.command({key:'ArrowUp'}).kind,'variant');assert.equal(shortcuts.command({key:'Home'}).kind,'first');assert.equal(shortcuts.command({key:'End'}).kind,'last');assert.equal(shortcuts.command({key:'PageDown'}).delta,10);
for(const options of [{output:true},{focus:false},{hasGame:false},{dialog:true},{editing:true}])assert.equal(shortcuts.command({key:'ArrowRight'},options),null);
for(const key of ['ctrlKey','metaKey','altKey','isComposing'])assert.equal(shortcuts.command({key:'ArrowLeft',[key]:true}),null);
console.log('Navigation passed: preserved and nested lines, sibling selection, existing move reuse, keyboard guards, live updates, serialization and original game integrity.');
