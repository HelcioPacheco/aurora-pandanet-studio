'use strict';
const APP_VERSION='0.4.7';
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function applyTheme(theme){document.documentElement.dataset.theme=['light','light-blue'].includes(theme)?theme:'dark';if($('themeSelect'))$('themeSelect').value=document.documentElement.dataset.theme;}
applyTheme(localStorage.getItem('aurora-theme')||'dark');
const output=new URLSearchParams(location.search).has('output');if(output)document.body.classList.add('output');
let state={watched:[],available:[],rooms:[],connection:'disconnected'},shared={aiSettings:{},aiLive:{},aiFocus:null,aiStatus:null,selected:null,mode:'focus',numberMode:'1',boardSkin:'normal',games:{}},tool='move',color='#dc493d',boardCache=new Map(),frameToken=0,drag=null,lastMoves=new Map(),uid=0;
const rendered={available:'',rail:'',mosaic:'',players:'',board:''};let clockAnchor=performance.now();
try{Object.assign(shared,JSON.parse(localStorage.getItem('aurora-layout')||'{}'));}catch{}
const channel=typeof BroadcastChannel!=='undefined'?new BroadcastChannel('aurora-studio'):null;
let shareFrame=null,persistTimer=null;
function persistLayout(){clearTimeout(persistTimer);persistTimer=null;try{localStorage.setItem('aurora-layout',JSON.stringify((({aiLive,aiFocus,aiStatus,...saved})=>saved)(shared)));}catch(error){toast('Não foi possível salvar a disposição neste navegador.');}}
function share(){
 // Persistence is deliberately off the input/render path; broadcast at most once per frame.
 clearTimeout(persistTimer);persistTimer=setTimeout(persistLayout,300);
 if(channel&&shareFrame===null)shareFrame=setTimeout(()=>{shareFrame=null;channel.postMessage(shared);},40);
}
const outputFrames=new FrameQueue();
function syncLayout(value){if(output){shared=value;outputFrames.enqueue(render);}}
if(channel)channel.onmessage=e=>{if(e.data?.auroraAIRequest&&!output){channel.postMessage(shared);return;}if(!e.data?.auroraAIRequest)syncLayout(e.data);};
window.addEventListener('storage',e=>{if(!channel&&e.key==='aurora-layout'&&e.newValue)syncLayout(JSON.parse(e.newValue));if(e.key==='aurora-theme')applyTheme(e.newValue);});
window.addEventListener('pagehide',()=>{if(!output)persistLayout();});
async function api(path,data={}){const response=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-Aurora':'studio'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Não foi possível concluir.');return result;}
let analysisBusy=false,feedbackStarted=null;
function startFeedback(){feedbackStarted=performance.now();}
function finishFeedback(){if(feedbackStarted===null)return;const start=feedbackStarted;feedbackStarted=null;requestAnimationFrame(()=>requestAnimationFrame(()=>{$('mainBoard').dataset.feedbackMs=(performance.now()-start).toFixed(1);}));}
let toastTimer;function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
async function action(name,data={}){try{await api(name,data);}catch(e){toast(e.message);}}
function current(){return state.watched.find(g=>g.id===Number(shared.selected));}
function view(g){return shared.games[g.id]??=( {cursor:null,variation:[],notes:{}} );}
function signature(g){const v=view(g);return `${v.cursor??g.moves.length}:${AnalysisView.active(v).map(m=>m.color+m.point).join(',')}`;}
function annotations(g){return view(g).notes[signature(g)]||[];}
function saveNotes(g,notes){view(g).notes[signature(g)]=renumberMarks(notes);share();renderBoard();}

function letterAt(index){let text='';for(let n=index+1;n>0;n=Math.floor((n-1)/26))text=String.fromCharCode(65+(n-1)%26)+text;return text;}
function renumberMarks(notes){let letters=0,numbers=0;return notes.map(m=>m.type==='label'?{...m,text:letterAt(letters++)}:m.type==='number'?{...m,text:String(++numbers)}:m);}
function groupLiberties(board,x,y){
 const stones=new Map(board.stones.map(s=>[s[0]+','+s[1],s[2]])),color=stones.get(x+','+y);
 if(!color)return null;
 const seen=new Set(),liberties=new Map(),stack=[[x,y]];
 while(stack.length){const [a,b]=stack.pop(),key=a+','+b;if(seen.has(key))continue;seen.add(key);
  for(const [c,d] of [[a-1,b],[a+1,b],[a,b-1],[a,b+1]]){if(c<0||d<0||c>=board.size||d>=board.size)continue;const k=c+','+d,value=stones.get(k);if(!value)liberties.set(k,[c,d]);else if(value===color&&!seen.has(k))stack.push([c,d]);}
 }
 return {stones:seen,points:[...liberties.values()]};
}
function displayMarks(board,notes){return notes.flatMap(m=>{if(m.type!=='liberties')return [m];const group=groupLiberties(board,m.x,m.y);return group?[{...m,type:'number',text:String(group.points.length)},...group.points.map(([x,y])=>({type:'circle',x,y,color:m.color}))]:[];});}
function pin(g){const v=view(g);if(v.cursor===null)v.cursor=g.moves.length;}
function flagHTML(p){return /^[A-Z]{2}$/.test(p.country_code||'')?`<img class="country-flag" src="/flags/${p.country_code.toLowerCase()}.svg" alt="${esc(p.country)}" title="${esc(p.country)}">`:'';}
function avatar(p){return `<img class="avatar" src="${esc(p.photo?'/api/photo?url='+encodeURIComponent(p.photo):'/silhouette.svg')}" alt="${p.photo?'Foto de '+esc(p.name):'Sem foto'}" onerror="this.onerror=null;this.src='/silhouette.svg'">`;}
function formatTime(clock,g){if(!clock)return state.demo?'—':'--:--';let remaining=clock.estimated_seconds??clock.seconds;if(clock.estimated&&!clock.stale&&state.connection==='connected')remaining-=Math.max(0,(performance.now()-(g?g._clockAt:clockAnchor))/1000);const seconds=Math.max(0,Math.ceil(remaining));return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;}
function playerHTML(g,c){const p=g[c==='B'?'black_player':'white_player'];const clock=g.clocks?.[c];return `<div class="player" data-profile="${c}" tabindex="${output?-1:0}" role="${output?'group':'button'}" aria-label="Perfil de ${esc(p.name)}">${avatar(p)}${flagHTML(p)}<div class="player-text"><div class="player-name"><i class="stone ${c}"></i>${esc(p.name)}</div><div class="player-details">${esc(p.rank.replace(/\*$/,''))}${p.country?' · '+esc(p.country):''} <span class="muted">/ ${esc(p.account)}</span></div></div><div class="clock ${clock?.estimated?'running':''}"><span class="clock-value">${formatTime(clock,g)}</span><small>${state.demo||g.recorded?'GRAVAÇÃO':clock?.stale?'SEM SINCRONIA':clock?.stones>=0?esc(clock.stones)+' PEDRAS':c==='B'?'PRETAS':'BRANCAS'}</small></div></div>`;}
const boardFrames=new FrameQueue();
function updateMainBoard(g,board,marks){const host=$('mainBoard');if(g.board_error||!board){host.textContent=g.board_error||'Aguardando a posição…';return;}let canvas=host.querySelector('canvas');if(!canvas){canvas=document.createElement('canvas');canvas.className='goban';canvas.setAttribute('role','img');host.replaceChildren(canvas);}const notes=displayMarks(board,marks),numbers=MoveNumbers.forPosition(g,view(g),board,shared.numberMode,notes);const aiMark=typeof AuroraAI!=='undefined'?AuroraAI.suggestion():null;BoardPainter.paint(canvas,board,aiMark?[...notes,aiMark]:notes,{numbers,skin:shared.boardSkin});}
function tile(g,mosaic=false){const selected=g.id===Number(shared.selected),v=view(g),status=state.demo||g.recorded?'GRAVAÇÃO':g.status==='finished'?g.result||'FINALIZADO':g.stale?'ATUALIZANDO':'AO VIVO';return `<article class="game-tile ${selected?'selected':''}" data-game="${g.id}" tabindex="0" role="button" aria-label="Destacar ${esc(g.black_player.name)} contra ${esc(g.white_player.name)}"><div class="tile-top"><span>${esc(status)}</span><span>#${g.id}</span></div><div class="evaluation-bar ai-pending"><span class="evaluation-values" aria-hidden="true"><b class="evaluation-black">● —</b><span class="evaluation-score">—</span><b class="evaluation-white">○ —</b></span><i></i></div><div class="tile-board"><canvas class="goban" role="img" aria-label="Tabuleiro da partida"></canvas></div><div class="tile-players"><span><i class="stone B"></i>${esc(g.black_player.name)} <small class="muted">${esc(g.black_player.rank.replace(/\*$/,''))}</small></span><span><i class="stone W"></i>${esc(g.white_player.name)} <small class="muted">${esc(g.white_player.rank.replace(/\*$/,''))}</small></span></div>${!output?`<button class="remove-game" data-remove="${g.id}" title="Remover da transmissão" aria-label="Remover partida ${g.id}">×</button>`:''}</article>`;}
const tileKeys=new WeakMap();
function updateTiles(container,games){
 const wanted=new Set(games.map(g=>String(g.id)));
 for(const child of [...container.children])if(!wanted.has(child.dataset.game))child.remove();
 games.forEach((g,index)=>{
  const key=JSON.stringify([shared.boardSkin,g.id,state.demo,g.board,g.board_error,g.status,g.stale,g.result,g.black_player,g.white_player]);
  let child=[...container.children].find(el=>el.dataset.game===String(g.id));
  if(!child||tileKeys.get(child)!==key){
   const template=document.createElement('template');template.innerHTML=tile(g);const next=template.content.firstElementChild;
   if(g.board)BoardPainter.paint(next.querySelector('canvas'),g.board,[],{mini:!output,last:false,skin:shared.boardSkin});tileKeys.set(next,key);if(child)child.replaceWith(next);child=next;
  }
  child.classList.toggle('selected',g.id===Number(shared.selected));const badge=child.querySelector('.tile-top span');if(badge){const status=state.demo||g.recorded?'GRAVAÇÃO':g.status==='finished'?g.result||'FINALIZADO':g.stale?'ATUALIZANDO':'AO VIVO';badge.textContent=status;}
  if(container.children[index]!==child)container.insertBefore(child,container.children[index]||null);
 });
}
function selectGame(id){shared.selected=Number(id);shared.mode='focus';share();render();}
function renderAvailable(){if(typeof renderWatchTeam==='function')renderWatchTeam();if(['join','connect'].includes(state.pending)){const loading='<div class="sidebar-empty">Carregando as partidas da sala…</div>';if(rendered.available!==loading){$('availableList').innerHTML=loading;rendered.available=loading;}return;}const q=$('searchInput').value.toLowerCase(),watched=new Set(state.watched.map(g=>g.id));const source=typeof teamAvailableGames==='function'?teamAvailableGames():state.available;const games=source.filter(g=>`${g.id} ${g.black} ${g.white}`.toLowerCase().includes(q));const html=games.length?games.map(g=>`<article class="available-game"><div class="row spread"><small>PARTIDA #${g.id}</small><small>${g.move_count} lances</small></div><div class="opponents"><span><i class="stone B"></i>${esc(g.black)}</span><small>${esc(g.black_rank)}</small></div><div class="opponents"><span><i class="stone W"></i>${esc(g.white)}</span><small>${esc(g.white_rank)}</small></div><button data-observe="${g.id}" ${watched.has(g.id)||(state.opening_ids||[]).includes(g.id)||state.pending==='observe'?'disabled':''}>${watched.has(g.id)?'✓ Acompanhando':state.pending==='observe'?'Abrindo…':'+ Acompanhar'}</button></article>`).join(''):`<div class="sidebar-empty">${state.demo?'Conecte ao Pandanet para escolher partidas ao vivo.':state.connection==='connected'?'Nenhuma partida encontrada nesta sala.':'Conecte ao servidor para ver as salas e partidas disponíveis.'}</div>`;if(html!==rendered.available){$('availableList').innerHTML=html;rendered.available=html;}}
function render(){if(typeof renderLeagueContext==='function')renderLeagueContext();if(!state.watched.some(g=>g.id===Number(shared.selected))){shared.selected=state.watched[0]?.id??null;if(!output)share();}
$('connectionText').textContent=state.demo?'Demonstração · partidas gravadas':({connected:'Pandanet conectado',connecting:'Conectando…',reconnecting:'Reconectando…',disconnected:'Sem conexão',authentication_required:'Login necessário'}[state.connection]||state.connection);
$('connectionDot').className='dot '+(state.demo?'demo':state.connection==='connected'?'online':'');$('connectBtn').textContent=state.connection==='connected'?'Desconectar':'Conectar';$('watchCount').textContent=state.watched.length+' jogos';$('notice').hidden=!state.message||state.message==='Conexão estabelecida.'||state.message==='Gravações reais de teste · sem conexão com o servidor';$('notice').textContent=state.message||'';$('footerStatus').textContent=state.pending?({connect:'Conectando ao Pandanet…',join:'Entrando na sala…',observe:'Abrindo partida…',refresh:'Atualizando partidas…',unobserve:'Removendo observação…'}[state.pending]||'Atualizando…'):state.demo?'Gravações reais · análise disponível':state.connection==='connected'?'Recebendo atualizações do Pandanet':state.message||'Pronto para conectar';
$('boardSkinSelect').value=shared.boardSkin==='mono'?'mono':'normal';$('focusBtn').classList.toggle('active',shared.mode==='focus');$('mosaicBtn').classList.toggle('active',shared.mode==='mosaic');const empty=!state.watched.length;$('emptyState').hidden=!empty;$('focusView').hidden=empty||shared.mode!=='focus';$('mosaicView').hidden=empty||shared.mode!=='mosaic';$('screenTitle').textContent=shared.mode==='mosaic'?'Todas as partidas':'Mesa de transmissão';
const roomHTML='<option value="0">Sala principal</option>'+state.rooms.filter(r=>Number(r.id)!==0).map(r=>`<option value="${r.id}">${esc(r.name)}</option>`).join('');if($('roomSelect').innerHTML!==roomHTML)$('roomSelect').innerHTML=roomHTML;$('roomSelect').value=String(StateOrder.room(state));$('roomSelect').disabled=state.connection!=='connected'||['connect','join'].includes(state.pending);$('refreshBtn').disabled=state.connection!=='connected';renderAvailable();
if(!empty){
 const cols=Math.max(1,Math.ceil(Math.sqrt(state.watched.length)));
 $('mosaicView').style.setProperty('--cols',cols);$('mosaicView').style.setProperty('--rows',Math.ceil(state.watched.length/cols));
 const key=JSON.stringify([shared.boardSkin,shared.selected,state.demo,state.watched.map(g=>[g.id,g.board,g.board_error,g.status,g.stale,g.result,g.black_player,g.white_player])]);
 if(shared.mode==='focus'){
  if(rendered.rail!==key){const games=output?state.watched.filter(g=>g.id!==Number(shared.selected)):state.watched;updateTiles($('gameRail'),games);if(output){$('focusView').style.setProperty('--side-rows',Math.max(1,Math.ceil(games.length/2)));$('focusView').classList.toggle('has-output-games',games.length>0);}rendered.rail=key;}
  renderBoard();
 }else if(rendered.mosaic!==key){updateTiles($('mosaicView'),state.watched);rendered.mosaic=key;}
 if(output)updateOutputLayout();
}
 if(typeof AuroraAI!=='undefined')AuroraAI.refresh();
}

function renderBoard(){boardFrames.enqueue(paintBoard);}
function paintBoard(){const g=current();if(!g)return;const v=view(g);if(v.cursor!==null)v.cursor=Math.min(v.cursor,g.moves.length);const live=v.cursor===null&&!v.variation.length;
const playerKey=JSON.stringify([g.id,g.black_player,g.white_player]);if(rendered.players!==playerKey){$('players').innerHTML=playerHTML(g,'B')+playerHTML(g,'W');rendered.players=playerKey;}tickClocks();const ply=v.cursor??g.moves.length,timeline=AnalysisView.timeline(g,v);$('numberMode').value=MoveNumbers.normalize(shared.numberMode);$('positionStatus').textContent=(state.demo||g.recorded)?(live?'● GRAVAÇÃO':'● ANÁLISE DA GRAVAÇÃO'):live?(g.status==='finished'?'● FINALIZADO':g.stale?'● SINCRONIZANDO':'● AO VIVO'):'● ANÁLISE';$('positionStatus').className='live-badge '+(!live?'analysis':'');$('gameNumber').textContent=g.recorded?`${I18n.sourceDate(g.date)} · ${g.size} × ${g.size}`:`Partida #${g.id} · ${g.size} × ${g.size}`;$('resultText').textContent=g.result||'';$('moveCounter').textContent=v.variation.length?`Variação ${AnalysisView.count(v)} / ${v.variation.length}`:`${ply} / ${g.moves.length}`;$('moveSlider').max=timeline.max;$('moveSlider').value=timeline.ply;$('analysisTitle').textContent=v.variation.length?'Explorando uma variação':live?'Acompanhar o jogo':'Revisar uma posição';$('analysisHint').textContent=live?'Os novos lances chegam automaticamente.':v.variation.length?'Use as setas para percorrer a variação.':'Clique no próximo lance para seguir a partida ou em outro ponto para explorar.';$('variationInfo').hidden=!v.variation.length;$('variationInfo').textContent=`Variação local · lance ${AnalysisView.count(v)} de ${v.variation.length} · numeração a partir de 1`;$('undoVariation').hidden=!v.variation.length;$('undoVariation').disabled=AnalysisView.count(v)===0;$('leaveVariation').hidden=!v.variation.length;
renderVariantNavigation(g,v);
if(!output){$('moveTreeTitle').textContent=I18n.t('moveTree');$('moveTree').setAttribute('aria-label',I18n.t('moveTree'));MoveTree.render($('moveTree'),g,v,{title:I18n.t('moveTree'),first:I18n.t('first')});}
const token=++frameToken;let board=g.board;const key=g.id+':'+signature(g);try{if(!live){if(!boardCache.has(key))boardCache.set(key,LocalBoard.reconstruct(g,ply,AnalysisView.active(v)));board=boardCache.get(key);}if(token!==frameToken)return;g.displayBoard=board;if(!drag){const boardKey=JSON.stringify([typeof AuroraAI!=='undefined'?AuroraAI.suggestion():null,shared.boardSkin,g.id,board,annotations(g),MoveNumbers.normalize(shared.numberMode),!!v.variation.length,AnalysisView.count(v),v.variationBreaks]);if(rendered.board!==boardKey){updateMainBoard(g,board,annotations(g));rendered.board=boardKey;}finishFeedback();}}catch(e){toast(e.message);}if(typeof AuroraAI!=='undefined')AuroraAI.refresh();}
function navigate(delta,absolute=null){startFeedback();const g=current();if(!g)return;AnalysisView.navigate(g,view(g),delta,absolute);share();renderBoard();}
function renderVariantNavigation(g,v){
 const lines=AnalysisView.lines(g,v);$('variantNavigation').hidden=!lines.length;
 const options=`<option value="main">${esc(I18n.t('mainLine'))}</option>`+lines.map((line,index)=>{const fork=Math.max(0,...line.breaks);return `<option value="${esc(line.id)}">${index+1} · #${line.base+fork+1} ${esc(line.moves[fork]?.point||'')}</option>`;}).join('');
 if($('variantSelect').innerHTML!==options)$('variantSelect').innerHTML=options;
 $('variantSelect').value=v.selectedLine||'main';
 const canSwitch=AnalysisView.alternatives(g,v).choices.length>1;
 $('previousVariant').disabled=$('nextVariant').disabled=!canSwitch;
 $('previousVariant').setAttribute('aria-label',I18n.t('previous')+' · '+I18n.t('variation'));
 $('nextVariant').setAttribute('aria-label',I18n.t('next')+' · '+I18n.t('variation'));
 $('keyboardHint').textContent=`← ${I18n.t('previousMove')} · → ${I18n.t('nextMove')} · ↑/↓ ${I18n.t('variation')} · Home |‹ · End ›|`;
}
function switchVariant(delta){const g=current();if(!g||!AnalysisView.cycle(g,view(g),delta))return;startFeedback();share();renderBoard();}
function openProfile(c){if(output)return;const g=current();if(!g)return;showPlayer(g[c==='B'?'black_player':'white_player'],g.date??(state.demo||g.recorded?'':undefined));}
function pointFromEvent(e){const g=current(),canvas=$('mainBoard').querySelector('canvas');if(!g||!canvas)return null;const box=canvas.getBoundingClientRect(),sx=(e.clientX-box.left)/box.width*720,sy=(e.clientY-box.top)/box.height*720,step=640/(g.size-1),x=Math.round((sx-40)/step),y=Math.round((sy-40)/step);if(x<0||y<0||x>=g.size||y>=g.size)return null;return {x,y,sx,sy,point:'ABCDEFGHJKLMNOPQRSTUVWXYZ'[x]+(g.size-y)};}
$('mainBoard').addEventListener('pointerdown',async e=>{if(output||e.button!==0)return;$('mainBoard').focus({preventScroll:true});const g=current(),p=pointFromEvent(e);if(!g||!p)return;startFeedback();const v=view(g);if(['arrow','freehand'].includes(tool)){pin(g);drag={...p,id:g.id,type:tool,points:[[p.sx,p.sy]],to:[p.x,p.y]};$('mainBoard').setPointerCapture(e.pointerId);return;}
if(tool==='move'){if(analysisBusy||!g.displayBoard)return;analysisBusy=true;try{const result=AnalysisView.play(g,v,p.point,LocalBoard);g.displayBoard=result.board;boardCache.set(g.id+':'+signature(g),result.board);share();renderBoard();}catch(error){toast(error.message);}finally{analysisBusy=false;}return;}

pin(g);let notes=[...annotations(g)];
if(tool==='erase'){notes=notes.filter(m=>Math.hypot(m.x-p.x,m.y-p.y)>0.45);saveNotes(g,notes);return;}
if(tool==='liberties'){
 const group=g.displayBoard&&groupLiberties(g.displayBoard,p.x,p.y);
 if(!group){toast('Clique em uma pedra para mostrar as liberdades do grupo.');return;}
 const index=notes.findIndex(m=>m.type==='liberties'&&group.stones.has(m.x+','+m.y));
 if(index>=0)notes.splice(index,1);else{notes.push({type:tool,x:p.x,y:p.y,color});toast(group.points.length+' liberdade'+(group.points.length===1?'':'s')+' no grupo.');}
 saveNotes(g,notes);return;
}
const index=notes.findIndex(m=>m.x===p.x&&m.y===p.y&&m.type===tool);
if(index>=0)notes.splice(index,1);else{if(['label','number'].includes(tool))notes=notes.filter(m=>!(m.x===p.x&&m.y===p.y&&['label','number'].includes(m.type)));notes.push({type:tool,x:p.x,y:p.y,color});}saveNotes(g,notes);});

$('mainBoard').addEventListener('pointermove',e=>{if(!drag)return;const p=pointFromEvent(e),g=current();if(!p||!g||g.id!==drag.id)return;drag.to=[p.x,p.y];if(drag.type==='freehand')drag.points.push([p.sx,p.sy]);const mark={type:drag.type,x:drag.x,y:drag.y,to:drag.to,points:drag.points,color};updateMainBoard(g,g.displayBoard,[...annotations(g),mark]);});
function finishDrawing(cancel=false){if(!drag)return;const g=current(),d=drag;drag=null;rendered.board='';if(!cancel&&g&&g.id===d.id)saveNotes(g,[...annotations(g),{type:d.type,x:d.x,y:d.y,to:d.to,points:d.points,color}]);else renderBoard();}
$('mainBoard').addEventListener('pointerup',()=>finishDrawing());$('mainBoard').addEventListener('pointercancel',()=>finishDrawing(true));
$('themeSelect').onchange=e=>{applyTheme(e.target.value);localStorage.setItem('aurora-theme',e.target.value);};
$('connectBtn').onclick=()=>{if(state.connection==='connected'){action('disconnect');return;}$('connectDialog').showModal();};
$('loginForm').onsubmit=e=>{e.preventDefault();const username=$('username').value.trim(),password=$('password').value;if(!username||!password){toast('Preencha o usuário e a senha.');return;}action('connect',{username,password});$('password').value='';$('connectDialog').close();};
$('guestBtn').onclick=()=>{action('connect');$('password').value='';$('connectDialog').close();};document.querySelectorAll('.close-dialog').forEach(b=>b.onclick=()=>{b.closest('dialog').close();$('password').value='';});
$('profileForm').onsubmit=async e=>{e.preventDefault();try{await api('player',{account:$('accountField').value,name:$('nameField').value,country:$('countryField').value,rank:$('rankField').value,photo:$('photoField').value,year:state.league_id?profileContext?.year:null,league_id:state.league_id});$('profileDialog').close();toast('Perfil salvo neste computador.');poll();if(typeof reloadDirectory==='function'&&$('directoryDialog').open)reloadDirectory();}catch(error){toast(error.message);}};
$('roomSelect').onchange=async e=>{const room_id=Number(e.target.value);state.joining_room=room_id;state.pending='join';render();try{await api('join',{room_id});}catch(error){state.joining_room=null;state.pending=null;toast(error.message);render();}};$('refreshBtn').onclick=()=>action('refresh');$('searchInput').oninput=renderAvailable;
$('demoBtn').onclick=$('emptyDemo').onclick=()=>{action('demo');shared.games={};share();};$('obsBtn').onclick=()=>window.open('/?output=1','aurora-output','width=1500,height=1000');
$('focusBtn').onclick=()=>{shared.mode='focus';share();render();};$('mosaicBtn').onclick=()=>{shared.mode='mosaic';share();render();};
$('firstMove').onclick=()=>navigate(0,0);$('previousMove').onclick=()=>navigate(-1);$('nextMove').onclick=()=>navigate(1);$('lastMove').onclick=()=>{const g=current();if(g)navigate(0,AnalysisView.timeline(g,view(g)).max);};$('moveSlider').oninput=e=>navigate(0,Number(e.target.value));
$('liveBtn').onclick=()=>{const g=current();if(!g)return;AnalysisView.main(g,view(g),true);share();renderBoard();};
$('leaveVariation').onclick=()=>{const g=current();if(!g)return;AnalysisView.main(g,view(g));share();renderBoard();};
function activateTreeNode(event){const node=event.target.closest('[data-tree-node]'),g=current();if(output||!node||!g)return;if(MoveTree.activate($('moveTree'),g,view(g),node.dataset.treeNode)){startFeedback();share();renderBoard();$('mainBoard').focus({preventScroll:true});}}
$('moveTree').onclick=activateTreeNode;
$('moveTree').onkeydown=e=>{if((e.key==='Enter'||e.key===' ')&&e.target.closest('[data-tree-node]')){e.preventDefault();e.stopPropagation();activateTreeNode(e);}};
$('variantSelect').onchange=e=>{const g=current();if(!g)return;AnalysisView.selectLine(g,view(g),e.target.value,true);share();renderBoard();$('mainBoard').focus({preventScroll:true});};
$('previousVariant').onclick=()=>switchVariant(-1);$('nextVariant').onclick=()=>switchVariant(1);
$('undoVariation').onclick=()=>{const g=current();if(g){AnalysisView.undo(view(g));share();renderBoard();}};
$('numberMode').onchange=e=>{shared.numberMode=MoveNumbers.normalize(e.target.value);share();renderBoard();};
$('boardSkinSelect').onchange=e=>{shared.boardSkin=e.target.value==='mono'?'mono':'normal';share();render();};
$('toolButtons').onclick=e=>{const button=e.target.closest('[data-tool]');if(!button)return;finishDrawing(true);tool=button.dataset.tool;for(const item of $('toolButtons').querySelectorAll('[data-tool]')){const active=item===button;item.classList.toggle('active',active);item.setAttribute('aria-pressed',String(active));}};$('markColor').oninput=e=>color=e.target.value;$('removeCurrent').onclick=()=>{const g=current();if(g)action('unobserve',{id:g.id});};$('clearMarks').onclick=()=>{const g=current();if(g)saveNotes(g,[]);};
document.addEventListener('click',e=>{const remove=e.target.closest('[data-remove]');if(remove){action('unobserve',{id:Number(remove.dataset.remove)});return;}const tile=e.target.closest('[data-game]');if(tile&&!output){selectGame(tile.dataset.game);return;}const observe=e.target.closest('[data-observe]');if(observe){action('observe',{id:Number(observe.dataset.observe)});return;}const profile=e.target.closest('[data-profile]');if(profile)openProfile(profile.dataset.profile);});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')finishDrawing(true);
 const editing=!!(e.target.closest?.('input,select,textarea,[contenteditable]:not([contenteditable="false"])')||document.activeElement?.closest('input,select,textarea,[contenteditable]:not([contenteditable="false"])'));
 const dialog=!!document.querySelector('dialog[open]');
 const command=AnalysisShortcuts.command(e,{output,focus:shared.mode==='focus',hasGame:!!current(),dialog,editing});
 if(command){e.preventDefault();if(command.kind==='move')navigate(command.delta);else if(command.kind==='variant')switchVariant(command.delta);else if(command.kind==='first')navigate(0,0);else{const g=current();navigate(0,AnalysisView.timeline(g,view(g)).max);}return;}
 if(editing||dialog||e.ctrlKey||e.metaKey||e.altKey)return;
 if(e.key==='Enter'){if(e.target.closest('[data-remove]'))return;const tile=document.activeElement.closest('[data-game]'),profile=document.activeElement.closest('[data-profile]');if(tile&&!output)selectGame(tile.dataset.game);if(profile)openProfile(profile.dataset.profile);}
});
function tickClocks(){
 const g=current();if(!g)return;
 for(const c of ['B','W']){
  const el=$('players').querySelector(`[data-profile="${c}"] .clock`);if(!el)continue;
  const clock=g.clocks?.[c],value=el.querySelector('.clock-value');
  const text=formatTime(clock,g);if(value&&value.textContent!==text)value.textContent=text;
  el.classList.toggle('running',!!clock?.estimated&&!clock.stale&&state.connection==='connected');
  const small=el.querySelector('small'),stale=clock?.stale||(clock&&state.connection!=='connected');
  const hint=state.demo||g.recorded?'GRAVAÇÃO':stale?'SEM SINCRONIA':clock?.stones>=0?clock.stones+' PEDRAS':c==='B'?'PRETAS':'BRANCAS';
  if(small&&small.textContent!==hint)small.textContent=hint;
 }
}
function acceptState(next){
 if(!StateOrder.accept(state,next))return;
 for(const g of next.watched){
  g._clockAt=performance.now()-(g.clock_age||0)*1000;
  const previous=lastMoves.get(g.id),appended=previous&&g.moves.length>=previous.length&&previous.every((m,i)=>JSON.stringify(m)===JSON.stringify(g.moves[i]));
  if(previous&&!appended)for(const key of boardCache.keys())if(key.startsWith(g.id+':'))boardCache.delete(key);
  lastMoves.set(g.id,g.moves);
 }
 if(shared.session!==next.session_id){shared={aiSettings:shared.aiSettings||{},aiLive:{},aiFocus:null,aiStatus:shared.aiStatus||null,session:next.session_id,selected:null,mode:'focus',numberMode:MoveNumbers.normalize(shared.numberMode),games:{}};boardCache.clear();LocalBoard.clear();if(!output)share();}
 state=next;if(!drag)render();
}
let polling=false;
async function poll(){
 if(polling)return;polling=true;
 try{const response=await fetch('/api/state',{cache:'no-store'});if(!response.ok)throw Error('Servidor local indisponível');acceptState(await response.json());}
 catch(error){$('connectionText').textContent='Aplicativo local desconectado';$('connectionDot').className='dot';$('footerStatus').textContent=error.message;}
 finally{polling=false;}
}
const updates=new EventSource('/api/events');
updates.onopen=()=>render();
updates.onmessage=event=>{try{acceptState(JSON.parse(event.data));}catch(error){toast('Falha ao atualizar a tela: '+error.message);}};
updates.onerror=()=>{$('connectionText').textContent='Reconectando ao aplicativo…';$('connectionDot').className='dot';};
window.addEventListener('pagehide',()=>updates.close());
poll();setInterval(tickClocks,250);

document.addEventListener('aurora-language',()=>{if(current())renderBoard();});

// Resize only when the output window changes; no polling or network requests.
function updateOutputLayout(){
 if(!output||shared.mode!=='mosaic'||!state.watched.length)return;
 const host=$('mosaicView'),rect=host.getBoundingClientRect();
 const height=Math.max(1,window.innerHeight-rect.top-12);
 const caption=64+(shared.aiSettings?.obsBars===false?0:22);
 const layout=OutputLayout.grid(state.watched.length,rect.width,height,12,caption);
 host.style.height=height+'px';
 const offset=(rect.width-layout.cols*layout.boardSize-(layout.cols-1)*12)/2;
 [...host.children].forEach((child,i)=>{child.style.left=(offset+(i%layout.cols)*(layout.boardSize+12))+'px';child.style.top=(Math.floor(i/layout.cols)*(layout.boardSize+caption+12))+'px';child.style.width=layout.boardSize+'px';});
}
if(output)window.addEventListener('resize',()=>boardFrames.enqueue(()=>{updateOutputLayout();if(shared.mode==='focus')paintBoard();}));
