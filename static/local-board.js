'use strict';
// Local analysis never waits for HTTP or for the Pandanet connection.
const LocalBoard=(()=>{
 const letters='ABCDEFGHJKLMNOPQRSTUVWXYZ',cache=new Map();
 function point(text,size){text=text.toUpperCase();if(['PASS','PA',''].includes(text))return null;const x=letters.indexOf(text[0]),y=size-Number(text.slice(1));if(x<0||x>=size||!Number.isInteger(y)||y<0||y>=size)throw Error('Ponto fora do tabuleiro.');return [x,y];}
 function neighbors(k,size){const x=k%size,y=Math.floor(k/size);return [[x-1,y],[x+1,y],[x,y-1],[x,y+1]].filter(([a,b])=>a>=0&&a<size&&b>=0&&b<size).map(([a,b])=>b*size+a);}
 function group(board,k,size){const stones=new Set(),libs=new Set(),todo=[k],color=board.get(k);while(todo.length){const p=todo.pop();if(stones.has(p))continue;stones.add(p);for(const n of neighbors(p,size)){if(!board.has(n))libs.add(n);else if(board.get(n)===color&&!stones.has(n))todo.push(n);}}return {stones,libs};}
 function handicap(count,size){if(count<2||count>9)throw Error('Handicap não suportado.');const lo=size>=13?3:2,hi=size-1-lo,mid=Math.floor(size/2),pts=[[hi,lo],[lo,hi],[hi,hi],[lo,lo]].slice(0,Math.min(count,4));if([5,7,9].includes(count))pts.push([mid,mid]);if(count>=6)pts.push([lo,mid],[hi,mid]);if(count>=8)pts.push([mid,lo],[mid,hi]);return new Map(pts.map(([x,y])=>[y*size+x,'B']));}
 function step(state,move,size,h){const color=move.color,text=move.point;if(!['B','W'].includes(color))throw Error('Cor inválida.');if(text.toLowerCase()==='handicap')return {board:handicap(Number(move.extra?.[0]??h),size),previous:null,last:null,next:'W'};const p=point(text,size),board=new Map(state.board);if(p){const key=p[1]*size+p[0];if(board.has(key))throw Error('Essa interseção já está ocupada.');board.set(key,color);for(const n of neighbors(key,size)){if(board.has(n)&&board.get(n)!==color){const g=group(board,n,size);if(!g.libs.size)for(const s of g.stones)board.delete(s);}}if(!group(board,key,size).libs.size)throw Error('Lance sem liberdades.');if(state.previous&&board.size===state.previous.size&&[...board].every(([k,c])=>state.previous.get(k)===c))throw Error('Recaptura imediata de ko.');}return {board,previous:state.board,last:p,next:color==='B'?'W':'B'};}
 function reconstruct(g,ply=g.moves.length,variation=[]){
  const h=g.handicap||0,synthetic=g.moves.some(m=>m.point.toLowerCase()==='handicap'),initialKey=JSON.stringify([g.size,h,synthetic,g.setup,g.next_color]);let entry=cache.get(g.id);
  if(!entry||entry.initialKey!==initialKey){entry={initialKey,keys:[],states:[{board:g.setup?.length?new Map(g.setup.map(([x,y,c])=>[y*g.size+x,c])):h>=2&&!synthetic?handicap(h,g.size):new Map(),previous:null,last:null,next:g.next_color||(h>=2&&!synthetic?'W':'B')}]};cache.set(g.id,entry);}
  // Preserve prefixes when live moves append; invalidate from the first correction.
  const keys=g.moves.map(m=>JSON.stringify(m));let common=0;while(common<entry.keys.length&&common<keys.length&&entry.keys[common]===keys[common])common++;entry.states.length=Math.min(entry.states.length,common+1);entry.keys=keys;
  ply=Math.max(0,Math.min(ply,g.moves.length));while(entry.states.length<=ply){const i=entry.states.length-1;entry.states.push(step(entry.states[i],g.moves[i],g.size,h));}
  let s=entry.states[ply];for(const m of variation)s=step(s,m,g.size,h);
  return {stones:[...s.board].map(([k,c])=>[k%g.size,Math.floor(k/g.size),c]),last:s.last,next_color:s.next,size:g.size,ply,warnings:[]};
 }
 return {reconstruct,clear:()=>cache.clear()};
})();
if(typeof module!=='undefined')module.exports=LocalBoard;
