const assert=require('node:assert/strict'),engine=require('./static/local-board.js'),{AnalysisView:A}=require('./static/analysis-view.js'),Tree=require('./static/move-tree.js');
const g={id:7,size:9,moves:[{color:'B',point:'D4'},{color:'W',point:'F6'},{color:'B',point:'E5'},{color:'W',point:'C7'}]},original=JSON.stringify(g),v={cursor:1,variation:[],notes:{}};
A.play(g,v,'C3',engine);A.play(g,v,'F3',engine);const first=v.selectedLine;A.navigate(g,v,-1);A.play(g,v,'G3',engine);const second=v.selectedLine;
let tree=Tree.build(g,v);assert.equal(tree.nodes.length,8); // root + 4 original + 3 unique variant nodes
const c3=tree.nodes.filter(n=>n.move?.point==='C3');assert.equal(c3.length,1);assert.equal(c3[0].children.length,2);
const f3=tree.nodes.find(n=>n.move?.point==='F3'),g3=tree.nodes.find(n=>n.move?.point==='G3');assert.equal(f3.parent,g3.parent);assert.notEqual(f3.x,g3.x);assert.equal(f3.y,g3.y);
assert.equal(Tree.position(g,v,tree).node.id,g3.id);const count=A.lines(g,v).length;
for(let i=0;i<4;i++){assert.equal(Tree.choose(g,v,tree,f3.id),true);assert.equal(v.selectedLine,first);assert.equal(A.count(v),2);assert.equal(Tree.choose(g,v,tree,g3.id),true);assert.equal(v.selectedLine,second);}
assert.equal(A.lines(g,v).length,count);
Tree.choose(g,v,tree,c3[0].id);assert.equal(v.selectedLine,second);assert.equal(A.count(v),1); // preserve the continuation on a shared prefix
const main=tree.nodes.find(n=>n.move?.point==='F6');Tree.choose(g,v,tree,main.id);assert.equal(v.selectedLine,null);assert.equal(v.cursor,2);
Tree.choose(g,v,tree,0);assert.equal(A.timeline(g,v).ply,0);assert.equal(Tree.choose(g,v,tree,999),false);
assert.equal(JSON.stringify(g),original);const html=Tree.markup(tree,{title:'Lances & variantes',first:'Início'});assert.ok(html.includes('role="button"'));assert.ok(html.includes('Lances &amp; variantes'));
const empty=Tree.build({...g,moves:[]},{cursor:null,variation:[]});assert.equal(empty.nodes.length,1);
const long={id:8,moves:Array.from({length:3000},(_,i)=>({color:i%2?'W':'B',point:'Pass'}))};const big=Tree.build(long,{cursor:null,variation:[]});assert.equal(big.nodes.length,3001);assert.equal(Tree.position(long,{cursor:null,variation:[]},big).node.ply,3000);
const extended={...g,moves:[...g.moves,{color:'B',point:'A1'}]};assert.equal(Tree.build(extended,v).nodes.length,9);
console.log('Move tree passed: shared prefixes, sibling branches, node selection without duplicates, original line, root, live extension, escaping and 3000-move history.');
