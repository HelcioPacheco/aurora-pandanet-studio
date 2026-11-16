/* Pure roster matching shared by the sidebar and its tests. */
(function(root){
 const TeamGames={
  filter(games,team){
   if(!team)return games;
   const accounts=new Set(team.players.flatMap(p=>p.accounts).map(a=>a.toLowerCase()));
   return games.filter(g=>[g.white,g.black].some(a=>accounts.has(String(a||'').toLowerCase())));
  },
  pending(games,watched,opening=[]){const ids=new Set([...watched.map(g=>g.id),...opening]);return games.filter(g=>!ids.has(g.id));}
 };
 if(typeof module==='object'&&module.exports)module.exports=TeamGames;else root.TeamGames=TeamGames;
})(typeof globalThis==='object'?globalThis:this);
