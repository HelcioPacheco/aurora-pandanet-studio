const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const canvases=[];
function canvas(){
 const c={width:0,height:0,dataset:{},setAttribute(){}};
 const ops=[];
 c.ctx=new Proxy({ops},{get(target,key){
  if(key in target)return target[key];
  if(key==='createRadialGradient')return(...args)=>{ops.push([key,...args]);return {addColorStop(){}};};
  return(...args)=>ops.push([key,...args]);
 },set(target,key,value){ops.push(['set',key,value]);target[key]=value;return true;}});
 c.getContext=()=>c.ctx;canvases.push(c);return c;
}
const scope={document:{createElement:canvas},window:{devicePixelRatio:1}};
vm.createContext(scope);vm.runInContext(fs.readFileSync('static/board-painter.js','utf8')+'\nglobalThis.painter=BoardPainter;',scope);
const board={size:9,stones:[[2,2,'B'],[3,3,'W']],last:[2,2],ply:2};
const before=JSON.stringify(board),main=canvas();
const notes=[{type:'label',x:2,y:2,text:'A',color:'#ff0000'},{type:'arrow',x:1,y:1,to:[5,5],color:'#00ff00'}];
scope.painter.paint(main,board,notes,{skin:'normal'});
const layer=main.ctx.ops.find(op=>op[0]==='drawImage')[1];
const normalBackground=layer.ctx.ops.find(op=>op[0]==='drawImage')[1];
canvases.forEach(c=>c.ctx.ops.length=0);
scope.painter.paint(main,board,[],{skin:'mono',numbers:[{x:3,y:3,color:'W',text:'2'}]});
assert.equal(main.dataset.skin,'mono');
const monoBackground=layer.ctx.ops.find(op=>op[0]==='drawImage')[1];
assert.notEqual(monoBackground,normalBackground,'skin changes invalidate the cached board layer');
for(const c of canvases)for(const op of c.ctx.ops){
 assert.notEqual(op[0],'createRadialGradient','monochrome stones have no gradients');
 if(op[0]==='set'&&['fillStyle','strokeStyle'].includes(op[1]))assert.ok(['#000','#fff'].includes(op[2]),'monochrome paint uses only black or white');
}
canvases.forEach(c=>c.ctx.ops.length=0);
scope.painter.paint(main,board,notes,{skin:'mono'});
const annotationColors=main.ctx.ops.filter(op=>op[0]==='set'&&['fillStyle','strokeStyle'].includes(op[1])).map(op=>op[2]);
assert.ok(annotationColors.includes('#ff0000'),'labels keep their selected color on a monochrome board');
assert.ok(annotationColors.includes('#00ff00'),'arrows keep their selected color on a monochrome board');
assert.equal(layer.ctx.ops.length,0,'colored annotations do not repaint the monochrome base');
canvases.forEach(c=>c.ctx.ops.length=0);
scope.painter.paint(main,board,[],{skin:'normal'});
assert.equal(main.dataset.skin,'normal');
assert.equal(layer.ctx.ops.find(op=>op[0]==='drawImage')[1],normalBackground,'returning to normal restores its background');
assert.equal(JSON.stringify(board),before,'appearance changes do not change the game');
console.log('Board skins switch cached layers, preserve the game and preserve colored annotations on monochrome boards.');
