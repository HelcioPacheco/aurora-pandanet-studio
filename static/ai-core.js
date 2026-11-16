'use strict';
const AiCore=(()=>{
 const defaults={enabled:false,showSuggestion:false,level:'balanced',metric:'winrate',obsBars:true,obsSuggestion:false,rules:'auto',defaultKomi:6.5,handicapKomi:.5};
 const levels={light:{background:1,visits:16,ms:600},balanced:{background:4,visits:64,ms:1800},deep:{background:8,visits:256,ms:5000}};
 function settings(value={}){const s={...defaults,...value};for(const k of ['enabled','showSuggestion','obsBars','obsSuggestion'])s[k]=s[k]===true;if(!levels[s.level])s.level='balanced';if(!['winrate','score'].includes(s.metric))s.metric='winrate';if(!['auto','japanese','chinese','aga','tromp-taylor','new-zealand'].includes(s.rules))s.rules='auto';for(const k of ['defaultKomi','handicapKomi']){s[k]=Number(s[k]);if(!Number.isFinite(s[k])||Math.abs(s[k])>100)s[k]=defaults[k];}return s;}
 function ruleName(value){const t=String(value||'japanese').trim().toLowerCase();if(/^(japanese|japan|jp|igs|pandanet|korean)$/.test(t))return 'japanese';if(/^(chinese|china|cn)$/.test(t))return 'chinese';if(t==='aga')return 'aga';if(/^(nz|new[- ]zealand)$/.test(t))return 'new-zealand';if(/^(tromp[- ]taylor|tt)$/.test(t))return 'tromp-taylor';throw Error('Regras não reconhecidas. Escolha as regras na configuração da IA.');}
 function position(g,v,config,reconstruct){
  const s=settings(config),size=Number(g.size);if(size!==19)throw Error('A IA desta versão suporta tabuleiros 19 × 19.');
  const ply=v?Math.max(0,Math.min(v.cursor??g.moves.length,g.moves.length)):g.moves.length;
  const variation=v?(v.variation||[]).slice(0,Math.max(0,Math.min(v.variationCursor??v.variation?.length??0,v.variation?.length??0))):[];
  // The caller passes the active variation explicitly, independent of its stored siblings.
  const active=v?.aiVariation??variation,board=reconstruct(g,ply,active);
  let history=g.moves.slice(0,ply).concat(active),setup=reconstruct(g,0).stones;
  if(history[0]?.point.toLowerCase()==='handicap'){setup=reconstruct(g,1).stones;history=history.slice(1);}
  const letters='ABCDEFGHJKLMNOPQRSTUVWXYZ',col=c=>{if(c==='B')return 1;if(c==='W')return 2;throw Error('Cor inválida no histórico.');};
  const moves=history.map(m=>{const point=String(m.point).toUpperCase();if(['PASS','PA',''].includes(point))return {loc:-1,col:col(m.color)};const x=letters.indexOf(point[0]),y=size-Number(point.slice(1));if(x<0||x>=size||!Number.isInteger(y)||y<0||y>=size)throw Error('Coordenada inválida no histórico.');return {loc:y*size+x,col:col(m.color)};});
  setup=setup.map(([x,y,c])=>({loc:y*size+x,col:col(c)})).sort((a,b)=>a.loc-b.loc);
  const known=g.komi!==null&&g.komi!==undefined&&String(g.komi).trim()!==''&&Number.isFinite(Number(g.komi));
  const komi=known?Number(g.komi):(g.handicap>=2?s.handicapKomi:s.defaultKomi),rules=ruleName(s.rules==='auto'?g.rules:s.rules),toPlay=col(board.next_color),firstPlayer=moves[0]?.col??toPlay;
  const expected=Array(size*size).fill(0);for(const [x,y,c] of board.stones)expected[y*size+x]=col(c);
  const key=JSON.stringify([size,rules,komi,setup,moves,toPlay,firstPlayer]);
  return {key,size,rules,komi,assumedKomi:!known,moves,setup,toPlay,firstPlayer,expected};
 }
 function point(loc,size=19){return loc<0?'PASS':'ABCDEFGHJKLMNOPQRSTUVWXYZ'[loc%size]+(size-Math.floor(loc/size));}
 function valid(r){return !!r&&!r.error&&Number.isFinite(r.blackWinrate)&&r.blackWinrate>=0&&r.blackWinrate<=1&&Number.isFinite(r.blackScore);}
 function values(r,locale='en'){
  if(!valid(r))return {black:'● —',white:'○ —',score:'—'};
  const number=new Intl.NumberFormat(locale,{minimumFractionDigits:1,maximumFractionDigits:1}),percent=n=>number.format(100*n)+'%';
  return {black:'● '+percent(r.blackWinrate),white:'○ '+percent(1-r.blackWinrate),score:(r.blackScore>0?'● +':r.blackScore<0?'○ +':'')+number.format(Math.abs(r.blackScore))};
 }
 function fraction(result,metric){if(!valid(result))return null;return metric==='score'?.5+.5*Math.tanh(result.blackScore/15):Math.max(0,Math.min(1,result.blackWinrate));}
 function label(r,metric){if(!r)return '—';if(metric==='score')return (r.blackScore>=0?'B+':'W+')+Math.abs(r.blackScore).toFixed(1);return 'B '+(100*r.blackWinrate).toFixed(1)+'% · W '+(100*(1-r.blackWinrate)).toFixed(1)+'%';}
 return {defaults,levels,settings,position,point,fraction,label,ruleName,valid,values};
})();
if(typeof module!=='undefined')module.exports=AiCore;
