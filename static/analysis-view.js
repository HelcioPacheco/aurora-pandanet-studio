'use strict';
// Local analysis lines share recorded prefixes; game moves are never edited here.
const AnalysisView=(()=>{
 const same=(a,b)=>!!a&&!!b&&a.color===b.color&&String(a.point).toUpperCase()===String(b.point).toUpperCase();
 const prefix=(a,b)=>a.length<=b.length&&a.every((m,i)=>same(m,b[i]));
 const anchor=(g,base)=>JSON.stringify(g.moves.slice(0,base).map(m=>[m.color,String(m.point).toUpperCase()]));
 const clone=moves=>moves.map(m=>({...m}));
 function count(v){return Math.max(0,Math.min(v.variation?.length||0,v.variationCursor??v.variation?.length??0));}
 function active(v){return (v.variation||[]).slice(0,count(v));}
 function remember(g,v,fork=false){
  v.savedLines??=[];if(!v.variation?.length)return null;
  const base=v.cursor??g.moves.length,moves=v.variation,key=anchor(g,base);
  let line=v.savedLines.find(l=>l.base===base&&l.anchor===key&&l.moves.length===moves.length&&prefix(l.moves,moves));
  if(!line&&!fork)line=v.savedLines.find(l=>l.id===v.selectedLine&&l.base===base&&l.anchor===key&&prefix(l.moves,moves));
  if(!line){v.lineSerial=(v.lineSerial||0)+1;line={id:String(v.lineSerial),base,anchor:key,moves:[],breaks:[]};v.savedLines.push(line);}
  line.moves=clone(moves);line.breaks=[...(v.variationBreaks||[0])];v.selectedLine=line.id;return line;
 }
 function lines(g,v){
  if(!v.savedLines){v.savedLines=[];if(v.variation?.length)remember(g,v);}
  return v.savedLines.filter(l=>l.base<=g.moves.length&&l.anchor===anchor(g,l.base));
 }
 function selected(g,v){return lines(g,v).find(l=>l.id===v.selectedLine)||null;}
 function timeline(g,v){const line=selected(g,v),base=v.cursor??g.moves.length;return {ply:base+count(v),max:line?line.base+line.moves.length:v.variation?.length?base+v.variation.length:g.moves.length,base};}
 function path(g,v){return [...g.moves.slice(0,v.cursor??g.moves.length),...active(v)];}
 function apply(g,v,line,target){
  v.selectedLine=line?.id??null;
  if(line&&target>=line.base){v.cursor=line.base;v.variation=clone(line.moves);v.variationCursor=Math.min(line.moves.length,target-line.base);v.variationBreaks=[...line.breaks];}
  else{v.cursor=Math.min(target,g.moves.length);v.variation=[];v.variationCursor=0;v.variationBreaks=[];}
 }
 function navigate(g,v,delta,absolute=null){
  if(v.variation?.length&&!selected(g,v))remember(g,v);
  const t=timeline(g,v),target=Math.max(0,Math.min(t.max,absolute??t.ply+delta));apply(g,v,selected(g,v),target);return v;
 }
 function selectLine(g,v,id,enter=false,target=null){
  if(v.variation?.length&&!selected(g,v))remember(g,v);
  const ply=timeline(g,v).ply,line=lines(g,v).find(l=>l.id===String(id))||null,max=line?line.base+line.moves.length:g.moves.length;
  apply(g,v,line,Math.min(max,target??Math.max(ply,enter&&line?line.base+1:0)));return v;
 }
 function main(g,v,live=false){remember(g,v);const ply=v.cursor??g.moves.length;apply(g,v,null,Math.min(ply,g.moves.length));if(live)v.cursor=null;return v;}
 function paths(g,v){return [{id:'main',moves:g.moves},...lines(g,v).map(l=>({id:l.id,moves:[...g.moves.slice(0,l.base),...l.moves]}))];}
 function continuations(g,v,current=path(g,v)){
  const choices=new Map(),preferred=v.selectedLine||'main';
  for(const line of paths(g,v))if(prefix(current,line.moves)&&line.moves.length>current.length){
   const move=line.moves[current.length],key=move.color+String(move.point).toUpperCase(),previous=choices.get(key);
   if(!previous||line.id===preferred)choices.set(key,{...line,move});
  }
  return [...choices.values()];
 }
 function alternatives(g,v){
  const current=path(g,v),ply=current.length;
  let parent=current.slice(0,-1),choices=ply?continuations(g,v,parent):[];
  if(choices.length>1)return {choices,ply,move:current.at(-1)};
  parent=current;choices=continuations(g,v,parent);
  return {choices,ply:ply+1,move:choices.find(c=>c.id===(v.selectedLine||'main'))?.move||choices[0]?.move};
 }
 function cycle(g,v,delta){const options=alternatives(g,v);if(options.choices.length<2)return false;const index=Math.max(0,options.choices.findIndex(c=>same(c.move,options.move))),choice=options.choices[(index+delta+options.choices.length)%options.choices.length];selectLine(g,v,choice.id,false,options.ply);return true;}
 function play(g,v,point,engine){
  const base=v.cursor??g.moves.length,current=path(g,v),position=engine.reconstruct(g,base,active(v));
  const existing=continuations(g,v,current).find(c=>c.move.color===position.next_color&&String(c.move.point).toUpperCase()===String(point).toUpperCase());
  if(existing){
   const line=lines(g,v).find(l=>l.id===existing.id),target=current.length+1;
   const board=line&&target>=line.base?engine.reconstruct(g,line.base,line.moves.slice(0,target-line.base)):engine.reconstruct(g,target,[]);
   selectLine(g,v,existing.id,false,target);return {board,official:existing.id==='main',reused:true};
  }
  const prefixMoves=active(v),fork=prefixMoves.length<(v.variation?.length||0),breaks=(v.variationBreaks||[0]).filter(i=>i<prefixMoves.length);if(fork||!breaks.length)breaks.push(prefixMoves.length);
  const variation=[...prefixMoves,{color:position.next_color,point}],board=engine.reconstruct(g,base,variation);
  // Preserve the old continuation, and commit only after the new move is legal.
  if(v.variation?.length&&!selected(g,v))remember(g,v);
  v.cursor=base;v.variation=variation;v.variationCursor=variation.length;v.variationBreaks=breaks;
  remember(g,v,fork);return {board,official:false};
 }
 function undo(v){v.variation=active(v).slice(0,-1);v.variationCursor=v.variation.length;v.variationBreaks=(v.variationBreaks||[0]).filter(i=>i<v.variation.length);const line=v.savedLines?.find(l=>l.id===v.selectedLine);if(line){line.moves=clone(v.variation);line.breaks=[...v.variationBreaks];if(!line.moves.length){v.savedLines=v.savedLines.filter(l=>l!==line);v.selectedLine=null;}}}
 return {count,active,timeline,navigate,play,undo,lines,selectLine,main,alternatives,cycle};
})();
const MoveNumbers=(()=>{
 const modes=new Set(['none','1','5','10','25','50','all']),letters='ABCDEFGHJKLMNOPQRSTUVWXYZ';
 function normalize(mode){return modes.has(String(mode))?String(mode):'1';}
 function forPosition(g,v,board,mode='1',marks=[]){
  mode=normalize(mode);if(mode==='none')return [];
  const variation=AnalysisView.active(v),segmentStart=Math.max(0,...(v.variationBreaks||[0]).filter(i=>i<variation.length)),moves=v.variation?.length?variation.slice(segmentStart):g.moves.slice(0,v.cursor??g.moves.length),seen=new Map(),occupied=new Map(board.stones.map(([x,y,c])=>[x+','+y,c]));let number=0;
  for(const move of moves){const point=String(move.point||'').toUpperCase();if(point==='HANDICAP')continue;number++;if(['PASS','PA',''].includes(point))continue;const x=letters.indexOf(point[0]),y=board.size-Number(point.slice(1));if(x>=0&&x<board.size&&y>=0&&y<board.size)seen.set(x+','+y,{x,y,color:move.color,number});}
  const first=mode==='all'?1:Math.max(1,number-Number(mode)+1),labels=new Set(marks.filter(m=>['label','number'].includes(m.type)).map(m=>m.x+','+m.y));
  return [...seen.entries()].filter(([key,m])=>occupied.get(key)===m.color&&m.number>=first&&!labels.has(key)).map(([,m])=>({...m,text:String(m.number)}));
 }
 return {normalize,forPosition};
})();
if(typeof module!=='undefined')module.exports={AnalysisView,MoveNumbers};
