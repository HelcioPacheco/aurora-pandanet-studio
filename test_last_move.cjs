const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('static/app.js','utf8'),calls=[];
function tile(){return {dataset:{game:'1'},classList:{toggle(){}},querySelector:s=>s==='canvas'?{}:{textContent:''},replaceWith(next){container.children[0]=next;}};}
const container={children:[],insertBefore(n){this.children=[n];}},g={id:1,board:{size:19,stones:[[3,3,'B']],last:[3,3]},black_player:{},white_player:{}};
const scope={shared:{boardSkin:'normal',selected:1},state:{demo:true},output:false,BoardPainter:{paint(...args){calls.push(args[3]);}},tile:()=>'',document:{createElement(){return {set innerHTML(v){this.content={firstElementChild:tile()};}}}}};
vm.createContext(scope);vm.runInContext(source.slice(source.indexOf('const tileKeys='),source.indexOf('function selectGame('))+'\nglobalThis.draw=updateTiles;',scope);
scope.draw(container,[g]);assert.equal(calls.at(-1).last,true,'old saved layouts default to enabled');
scope.draw(container,[g]);assert.equal(calls.length,1,'unchanged boards keep their cached canvas');
scope.shared.markLastMove=false;scope.draw(container,[g]);assert.equal(calls.at(-1).last,false,'toggle invalidates miniature cache');
scope.output=true;scope.shared.markLastMove=true;scope.draw(container,[g]);assert.equal(calls.at(-1).last,true);assert.equal(calls.at(-1).mini,false,'OBS receives same preference at full resolution');
g.board={...g.board,last:null};scope.draw(container,[g]);assert.equal(calls.length,4,'pass updates the tile');
console.log('Last-move preference: default enabled, cached redraw, toggle, OBS and pass update passed.');
