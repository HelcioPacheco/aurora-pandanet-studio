'use strict';
(function(root,factory){
 const tree=factory(typeof module!=='undefined'&&module.exports?require('./analysis-view.js').AnalysisView:AnalysisView);
 if(typeof module!=='undefined'&&module.exports)module.exports=tree;else root.MoveTree=tree;
})(typeof globalThis==='object'?globalThis:this,function(analysis){
 const key=move=>move.color+':'+String(move.point).toUpperCase();
 function build(game,view){
  const nodes=[{id:0,ply:0,parent:null,move:null,children:[],routes:[],official:true}],paths=[{id:'main',moves:game.moves},...analysis.lines(game,view).map(line=>({id:line.id,moves:[...game.moves.slice(0,line.base),...line.moves]}))];
  for(const path of paths){let node=nodes[0];node.routes.push(path.id);
   for(const move of path.moves){
    let child=node.children.map(id=>nodes[id]).find(n=>key(n.move)===key(move));
    if(!child){child={id:nodes.length,ply:node.ply+1,parent:node.id,move:{...move},children:[],routes:[],official:false};nodes.push(child);node.children.push(child.id);}
    child.routes.push(path.id);if(path.id==='main')child.official=true;node=child;
   }
  }
  // Iterative layout handles long professional games without recursion limits.
  let lane=0,maxPly=0;const stack=[{id:0,lane:0}];
  while(stack.length){const entry=stack.pop(),node=nodes[entry.id];if(entry.lane===null)entry.lane=++lane;node.x=22+entry.lane*32;node.y=22+node.ply*32;maxPly=Math.max(maxPly,node.ply);
   for(let i=node.children.length-1;i>=0;i--)stack.push({id:node.children[i],lane:i===0?entry.lane:null});
  }
  return {nodes,width:44+(lane+1)*32,height:44+maxPly*32};
 }
 function position(game,view,model){
  let node=model.nodes[0];const path=[...game.moves.slice(0,view.cursor??game.moves.length),...analysis.active(view)],ancestors=[0];
  for(const move of path){const child=node.children.map(id=>model.nodes[id]).find(n=>key(n.move)===key(move));if(!child)break;node=child;ancestors.push(node.id);}
  return {node,ancestors};
 }
 function choose(game,view,model,id){
  const node=model.nodes[Number(id)];if(!node)return false;
  const preferred=view.selectedLine||'main',route=node.routes.includes(preferred)?preferred:node.routes.includes('main')?'main':node.routes[0];
  analysis.selectLine(game,view,route,false,node.ply);return true;
 }
 const escape=text=>String(text??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function markup(model,labels){
  const edges=model.nodes.slice(1).map(node=>{const parent=model.nodes[node.parent];return `<path aria-hidden="true" class="tree-edge ${node.official?'official':'variation'}" data-edge="${node.id}" d="M ${parent.x} ${parent.y+9} C ${parent.x} ${parent.y+18}, ${node.x} ${node.y-18}, ${node.x} ${node.y-9}"/>`;}).join('');
  const nodes=model.nodes.map(node=>{const color=node.move?.color||'root',description=node.move?`${node.ply} · ${color==='B'?'●':'○'} ${node.move.point}`:`0 · ${labels.first}`;return `<g class="tree-node ${color}" role="button" tabindex="-1" data-tree-node="${node.id}" aria-label="${escape(description)}" transform="translate(${node.x} ${node.y})"><title>${escape(description)}</title><circle aria-hidden="true" class="tree-hit" r="16"/><circle aria-hidden="true" class="tree-ring" r="13"/><circle aria-hidden="true" class="tree-stone" r="9"/><text aria-hidden="true" text-anchor="middle" dominant-baseline="central">${node.ply}</text></g>`;}).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${model.width}" height="${model.height}" role="group" aria-label="${escape(labels.title)}">${edges}${nodes}</svg>`;
 }
 let cache=null;
 function render(host,game,view,labels){
  const lines=analysis.lines(game,view),signature=JSON.stringify([game.id,game.moves.map(key),lines.map(line=>[line.id,line.base,line.moves.map(key)]),labels]);
  let rebuilt=false;if(!cache||cache.host!==host||cache.signature!==signature){const model=build(game,view);host.innerHTML=markup(model,labels);cache={host,signature,model,active:null};rebuilt=true;}
  const current=position(game,view,cache.model),activeKey=game.id+':'+current.node.id;
  if(rebuilt||cache.active!==activeKey){const path=new Set(current.ancestors);
   for(const el of host.querySelectorAll('[data-tree-node]')){const id=Number(el.dataset.treeNode),selected=id===current.node.id;el.classList.toggle('current',selected);el.classList.toggle('on-path',path.has(id));el.setAttribute('tabindex',selected?'0':'-1');if(selected)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');}
   for(const el of host.querySelectorAll('[data-edge]'))el.classList.toggle('on-path',path.has(Number(el.dataset.edge)));
   const {x,y}=current.node,margin=32;
   if(x<host.scrollLeft+margin||x>host.scrollLeft+host.clientWidth-margin)host.scrollLeft=Math.max(0,x-host.clientWidth/2);
   if(y<host.scrollTop+margin||y>host.scrollTop+host.clientHeight-margin)host.scrollTop=Math.max(0,y-host.clientHeight/2);
   cache.active=activeKey;
  }
 }
 function activate(host,game,view,id){return !!cache&&cache.host===host&&choose(game,view,cache.model,id);}
 return {build,position,choose,markup,render,activate};
});
