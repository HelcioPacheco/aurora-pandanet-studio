const assert=require('node:assert/strict');
const TeamGames=require('./static/team-games.js');
const team={players:[{accounts:['First','Alias']},{accounts:['Second']}]};
const games=[{id:1,white:'FIRST',black:'Else'},{id:2,white:'Other',black:'alias'},{id:3,white:'First',black:'Second'},{id:4,white:'Unrelated',black:'Other'}];
assert.deepEqual(TeamGames.filter(games,team).map(g=>g.id),[1,2,3]);
assert.deepEqual(TeamGames.filter(games,{players:[]}),[]);
assert.deepEqual(TeamGames.filter(games,null),games);
assert.deepEqual(TeamGames.pending(TeamGames.filter(games,team),[{id:1}],[2]).map(g=>g.id),[3]);
console.log('Team filter passed: either color, aliases, case, empty roster, all teams and watched/opening exclusions.');
