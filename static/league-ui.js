'use strict';
let watchTeamCode='',watchTeamContext='',teamOpening=false;
let leagueCatalog=[],directoryData=null,directoryPage=0,lastLeagueContext='',catalogLoading=false,directoryLoading=false,lastSyncStatus='',directoryRequest=0;
const normalized=text=>String(text||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
async function loadLeagueCatalog(){if(catalogLoading)return;catalogLoading=true;try{const response=await fetch('/api/leagues');if(!response.ok)throw Error('Não foi possível carregar as ligas.');leagueCatalog=(await response.json()).leagues;renderLeagueContext(true);}catch(e){toast(e.message);}finally{catalogLoading=false;}}
function selectedLeague(){return leagueCatalog.find(l=>l.id===state.league_id);}
function renderLeagueContext(force=false){
 const league=Number(state.room_id)!==0&&state.room_capabilities?.league!==false?selectedLeague():null;
 $('seasonControl').hidden=!league;
 $('directoryBtn').hidden=!league;
 $('watchTeamControls').hidden=!league;
 const associated=leagueCatalog.filter(l=>(state.room_league_ids||[]).includes(l.id));
 $('roomLeagueControl').hidden=!league||associated.length<2||state.room_capabilities?.league_choice===false;
 const choices=associated.map(l=>`<option value="${esc(l.id)}">${esc(l.name)}</option>`).join('');
 if($('roomLeagueSelect').innerHTML!==choices)$('roomLeagueSelect').innerHTML=choices;
 $('roomLeagueSelect').value=state.league_id||'';
 $('roomLeagueSelect').disabled=['connect','join'].includes(state.pending);
 const enabled=!!league&&!['connect','join'].includes(state.pending);
 $('directoryBtn').disabled=!enabled;$('syncLeagueBtn').disabled=!enabled||!!state.league_sync?.busy;
 if(!league){
  watchTeamCode='';watchTeamContext='';directoryData=null;lastLeagueContext='';directoryRequest++;
  $('seasonSelect').innerHTML='<option value="">—</option>';$('seasonSelect').disabled=true;
  $('leagueHeading').textContent=state.rooms.find(r=>r.id===state.room_id)?.name||'Sala principal';
  if($('directoryDialog').open)$('directoryDialog').close();renderWatchTeam();return;
 }
 const season=league.seasons.find(s=>s.season_id===state.season_id),key=JSON.stringify([state.league_id,state.season_id,leagueCatalog]);
 if(force||lastLeagueContext!==key){
  $('seasonSelect').innerHTML=league.seasons.map(s=>`<option value="${esc(s.season_id)}">${esc(s.season_name)}</option>`).join('')||'<option value="">Sem cadastro importado</option>';
  $('seasonSelect').value=state.season_id||'';$('seasonSelect').disabled=!enabled||!league.seasons.length;
  $('leagueHeading').textContent=league.name+(season?' · '+season.season_name:'');lastLeagueContext=key;
  const context=JSON.stringify([state.league_id,state.season_id]);
  if(watchTeamContext!==context){watchTeamContext=context;watchTeamCode='';directoryData=null;renderWatchTeam();}
  reloadDirectory();
 }
 $('seasonSelect').disabled=!enabled||!league.seasons.length;
 const sync=state.league_sync||{},syncKey=JSON.stringify(sync);
 $('syncLeagueBtn').disabled=!enabled||!!sync.busy;
 if(syncKey!==lastSyncStatus){const previous=lastSyncStatus;lastSyncStatus=syncKey;$('directoryStatus').textContent=sync.message||'';$('directoryStatus').classList.toggle('directory-status-error',!!sync.error);if(previous&&sync.updated_at){loadLeagueCatalog();if($('directoryDialog').open)reloadDirectory();}}
}
async function chooseLeague(league_id,season_id){try{await api('league',{league_id,season_id});await poll();directoryPage=0;}catch(e){toast(e.message);renderLeagueContext(true);}}
async function reloadDirectory(){const request=++directoryRequest;directoryLoading=true;try{
 const response=await fetch('/api/directory');if(!response.ok)throw Error('Não foi possível abrir o cadastro.');const received=await response.json();if(request!==directoryRequest||received.league_id!==state.league_id||received.season_id!==state.season_id)return;directoryData=received;directoryPage=0;
 const league=selectedLeague(),season=league?.seasons.find(s=>s.season_id===directoryData.season_id);$('directoryTitle').textContent=league?.name||'Equipes e jogadores';
 const count=directoryData.teams.reduce((n,t)=>n+t.players.length,0);const updated=season?.imported_at?new Date(season.imported_at).toLocaleString(I18n.locale):'';
 $('directorySummary').textContent=`${season?.season_name||'Sem temporada importada'} · ${directoryData.teams.length} equipes · ${count} participações · ${directoryData.total_people} pessoas no banco`+(updated?' · Importado em '+updated:'')+(directoryData.teams.some(t=>!t.players.length)?' · Há equipe com elenco ainda não publicado.':'');
 const previous=$('directoryTeam').value;$('directoryTeam').innerHTML='<option value="">Todas as equipes</option>'+directoryData.teams.map(t=>`<option value="${esc(t.code)}">${esc(t.country||t.name)}</option>`).join('');if(directoryData.teams.some(t=>t.code===previous))$('directoryTeam').value=previous;
 renderDirectory();renderWatchTeam();renderAvailable();
 }catch(e){toast(e.message);}finally{directoryLoading=false;}}
function renderDirectory(){if(!directoryData)return;const q=normalized($('directorySearch').value),teamCode=$('directoryTeam').value,people=directoryData.teams.filter(t=>!teamCode||t.code===teamCode).flatMap(t=>t.players.map(p=>({...p,team:t.name,country:t.country})));
 const filtered=people.filter(p=>normalized([p.name,p.team,p.country,...p.accounts].join(' ')).includes(q)),pages=Math.max(1,Math.ceil(filtered.length/24));directoryPage=Math.max(0,Math.min(directoryPage,pages-1));
 $('directoryGrid').innerHTML=filtered.slice(directoryPage*24,directoryPage*24+24).map(p=>`<article class="directory-card"><img class="avatar" loading="lazy" referrerpolicy="no-referrer" src="${esc(p.photo||'/silhouette.svg')}" alt="${p.photo?'Foto de '+esc(p.name):'Sem foto'}" onerror="this.onerror=null;this.src='/silhouette.svg'"><div class="directory-card-content"><h3>${esc(p.name)}</h3><p>${esc(p.rank||'Graduação não informada')} · ${esc(p.country||p.team)}</p><p>${p.captain?'Capitão · ':''}${p.trainer?'Treinador · ':''}${p.position?'Jogador '+p.position:''}</p><small>${esc(p.accounts.join(' / ')||p.account_raw||'Conta não publicada')}</small><p><a href="${esc(p.source_url)}" target="_blank" rel="noopener noreferrer">Cadastro oficial ↗</a></p><button class="quiet" data-directory-person="${p.person_id}" ${p.accounts.length?'':'disabled'} title="${p.accounts.length?'Editar o perfil usado na transmissão':'É necessária uma conta Pandanet para associar a uma partida'}">Editar perfil local</button></div></article>`).join('')||(teamCode&&!q&&directoryData.teams.find(t=>t.code===teamCode)?.players.length===0?'<p>Esta equipe ainda não possui jogadores publicados na fonte.</p>':'<p>Nenhum jogador encontrado.</p>');
 $('directoryPage').textContent=`${filtered.length} resultados · Página ${directoryPage+1} de ${pages}`;$('directoryPrevious').disabled=directoryPage===0;$('directoryNext').disabled=directoryPage>=pages-1;
}
function currentTeam(){return directoryData&&directoryData.league_id===state.league_id&&directoryData?.season_id===state.season_id?directoryData.teams.find(t=>t.code===watchTeamCode):null;}
function teamAvailableGames(){return watchTeamCode?TeamGames.filter(state.available,currentTeam()||{players:[]}):state.available;}
function renderWatchTeam(){
 const ready=!!directoryData&&directoryData.league_id===state.league_id&&directoryData?.season_id===state.season_id;
 const teams=ready?directoryData.teams:[];
 if(ready&&watchTeamCode&&!teams.some(t=>t.code===watchTeamCode))watchTeamCode='';
 const html='<option value="">Todas as equipes</option>'+teams.map(t=>`<option value="${esc(t.code)}">${esc(t.name||t.country)}</option>`).join('');
 if($('watchTeamSelect').innerHTML!==html)$('watchTeamSelect').innerHTML=html;
 $('watchTeamSelect').value=watchTeamCode;$('watchTeamSelect').disabled=!ready||!state.league_id||['connect','join'].includes(state.pending);
 $('watchTeamBtn').disabled=teamOpening||!currentTeam()||state.connection!=='connected'||!!state.pending||!TeamGames.pending(teamAvailableGames(),state.watched,state.opening_ids).length;
}
$('watchTeamSelect').onchange=e=>{watchTeamCode=e.target.value;renderAvailable();};
$('watchTeamBtn').onclick=async()=>{
 if(teamOpening||!currentTeam()||$('watchTeamBtn').disabled)return;
 teamOpening=true;$('watchTeamBtn').disabled=true;
 try{await api('observe-team',{league_id:state.league_id,season_id:state.season_id,room_id:state.room_id,team_code:watchTeamCode});await poll();}
 catch(e){toast(e.message);}finally{teamOpening=false;renderWatchTeam();}
};
$('roomLeagueSelect').onchange=e=>chooseLeague(e.target.value);
$('seasonSelect').onchange=e=>chooseLeague(state.league_id,e.target.value);
$('directoryBtn').onclick=()=>{$('directoryDialog').showModal();reloadDirectory();};
$('directorySearch').oninput=$('directoryTeam').onchange=()=>{directoryPage=0;renderDirectory();};
$('directoryPrevious').onclick=()=>{directoryPage--;renderDirectory();};$('directoryNext').onclick=()=>{directoryPage++;renderDirectory();};
$('syncLeagueBtn').onclick=async()=>{try{await api('league-sync',{league_id:state.league_id});}catch(e){toast(e.message);}};
$('directoryGrid').onclick=e=>{const button=e.target.closest('[data-directory-person]');if(!button)return;const p=directoryData.teams.flatMap(t=>t.players).find(p=>p.person_id===Number(button.dataset.directoryPerson));if(!p?.accounts.length)return;showPlayer({account:p.accounts[0],name:p.name,rank:p.rank,photo:p.photo},selectedLeague()?.seasons.find(s=>s.season_id===state.season_id)?.season_name.match(/(?:19|20)\d{2}/)?.[0]);};
loadLeagueCatalog();
