"""Local league registry, kept separate from user-edited player profiles."""
import json,sqlite3,hashlib
from pathlib import Path
from league_sources import LEAGUES
class LeagueRegistry:
 def __init__(self,path):
  self.path=Path(path)
  if self.path.exists():
   with sqlite3.connect(str(self.path)) as original:
    legacy=original.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='players'").fetchone();migrated=original.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='league_people'").fetchone()
    if legacy and not migrated and original.execute('SELECT COUNT(*) FROM players').fetchone()[0]:
     backup=self.path.with_name('players.before-leagues.sqlite3')
     if not backup.exists():
      with sqlite3.connect(str(backup)) as destination:original.backup(destination)
  with self.db() as db:
   db.executescript('''
   CREATE TABLE IF NOT EXISTS league_people(id INTEGER PRIMARY KEY,name TEXT NOT NULL,photo TEXT NOT NULL DEFAULT '');
   CREATE TABLE IF NOT EXISTS league_accounts(account_key TEXT PRIMARY KEY,account TEXT NOT NULL,person_id INTEGER NOT NULL REFERENCES league_people(id));
   CREATE TABLE IF NOT EXISTS league_sources(league_id TEXT,source_id TEXT,person_id INTEGER NOT NULL REFERENCES league_people(id),PRIMARY KEY(league_id,source_id));
   CREATE TABLE IF NOT EXISTS league_seasons(league_id TEXT,season_id TEXT,season_name TEXT,source_url TEXT,imported_at TEXT,warnings TEXT,PRIMARY KEY(league_id,season_id));
   CREATE TABLE IF NOT EXISTS league_teams(league_id TEXT,season_id TEXT,code TEXT,name TEXT,country TEXT,source_url TEXT,PRIMARY KEY(league_id,season_id,code));
   CREATE TABLE IF NOT EXISTS league_rosters(league_id TEXT,season_id TEXT,team_code TEXT,person_id INTEGER,name TEXT,rank TEXT,photo TEXT,captain INTEGER,trainer INTEGER,position INTEGER,source_url TEXT,account_raw TEXT,PRIMARY KEY(league_id,season_id,team_code,person_id));
   CREATE TABLE IF NOT EXISTS player_year_overrides(account_key TEXT,league_id TEXT,year INTEGER,rank TEXT,country TEXT,PRIMARY KEY(account_key,league_id,year));
   CREATE TABLE IF NOT EXISTS studio_settings(key TEXT PRIMARY KEY,value TEXT);
   CREATE TABLE IF NOT EXISTS league_seed_versions(league_id TEXT PRIMARY KEY,digest TEXT);
   ''')
 def db(self):
  db=sqlite3.connect(str(self.path),timeout=10);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
 def setting(self,key,default=None):
  with self.db() as db:row=db.execute('SELECT value FROM studio_settings WHERE key=?',(key,)).fetchone();return row[0] if row else default
 def configure(self,league_id,season_id=None):
  if league_id not in {l['id'] for l in LEAGUES}:raise ValueError('Liga desconhecida.')
  seasons=self.seasons(league_id)
  season_id=str(season_id or (seasons[0]['season_id'] if seasons else ''))
  if season_id and season_id not in {s['season_id'] for s in seasons}:raise ValueError('Temporada não cadastrada.')
  with self.db() as db:
   db.execute('INSERT OR REPLACE INTO studio_settings VALUES(?,?)',('league_id',league_id));db.execute('INSERT OR REPLACE INTO studio_settings VALUES(?,?)',('season_id:'+league_id,season_id))
  return league_id,season_id
 def selected(self):
  league_id=self.setting('league_id','latinamericanleague');seasons=self.seasons(league_id)
  return league_id,self.setting('season_id:'+league_id,seasons[0]['season_id'] if seasons else '')
 def seasons(self,league_id):
  with self.db() as db:return [dict(r) for r in db.execute('SELECT * FROM league_seasons WHERE league_id=? ORDER BY CAST(season_id AS INTEGER) DESC',(league_id,))]
 def catalog(self):
  result=[]
  with self.db() as db:
   for league in LEAGUES:
    seasons=self.seasons(league['id']);chosen=self.setting('season_id:'+league['id'],seasons[0]['season_id'] if seasons else '')
    counts=db.execute('SELECT COUNT(DISTINCT team_code),COUNT(DISTINCT person_id) FROM league_rosters WHERE league_id=? AND season_id=?',(league['id'],chosen)).fetchone()
    result.append(dict(**league,seasons=seasons,season_id=chosen,teams=db.execute('SELECT COUNT(*) FROM league_teams WHERE league_id=? AND season_id=?',(league['id'],chosen)).fetchone()[0],players=counts[1]))
  return result
 def import_snapshot(self,snapshot,seed_digest=None):
  lid=snapshot['league_id'];sid=str(snapshot['season_id'])
  if lid not in {l['id'] for l in LEAGUES} or not snapshot.get('teams') or not any(t.get('players') for t in snapshot['teams']):raise ValueError('Cadastro de liga inválido.')
  with self.db() as db:
   db.execute('DELETE FROM league_rosters WHERE league_id=? AND season_id=?',(lid,sid));db.execute('DELETE FROM league_teams WHERE league_id=? AND season_id=?',(lid,sid))
   for team in snapshot['teams']:
    db.execute('INSERT INTO league_teams VALUES(?,?,?,?,?,?)',(lid,sid,team['code'],team['name'],team.get('country',''),team['url']))
    for p in team['players']:
     source_id=p.get('source_id') or team['code']+':'+hashlib.sha256(p['name'].encode()).hexdigest()[:20]
     source=db.execute('SELECT person_id FROM league_sources WHERE league_id=? AND source_id=?',(lid,source_id)).fetchone()
     aliases=p.get('accounts',[]);ids={r[0] for account in aliases for r in db.execute('SELECT person_id FROM league_accounts WHERE account_key=?',(account.lower(),))}
     if source:ids.add(source[0])
     if len(ids)>1:raise ValueError('Conflito de identidade no cadastro de '+p['name']+'. Cadastro anterior preservado.')
     person_id=next(iter(ids)) if ids else db.execute('INSERT INTO league_people(name,photo) VALUES(?,?)',(p['name'],p.get('photo',''))).lastrowid
     db.execute('UPDATE league_people SET name=?,photo=CASE WHEN ?<>\'\' THEN ? ELSE photo END WHERE id=?',(p['name'],p.get('photo',''),p.get('photo',''),person_id))
     db.execute('INSERT OR REPLACE INTO league_sources VALUES(?,?,?)',(lid,source_id,person_id))
     for account in aliases:db.execute('INSERT OR REPLACE INTO league_accounts VALUES(?,?,?)',(account.lower(),account,person_id))
     db.execute('''INSERT INTO league_rosters VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(league_id,season_id,team_code,person_id) DO UPDATE SET captain=MAX(captain,excluded.captain),trainer=MAX(trainer,excluded.trainer),position=CASE WHEN position=0 THEN excluded.position ELSE position END,rank=CASE WHEN rank='' THEN excluded.rank ELSE rank END,photo=CASE WHEN photo='' THEN excluded.photo ELSE photo END''',(lid,sid,team['code'],person_id,p['name'],p.get('rank',''),p.get('photo',''),int(p.get('captain',False)),int(p.get('trainer',False)),p.get('order',0),p['source_url'],p.get('account_raw','')))
   db.execute('INSERT OR REPLACE INTO league_seasons VALUES(?,?,?,?,?,?)',(lid,sid,snapshot['season_name'],snapshot['source_url'],snapshot['imported_at'],json.dumps(snapshot.get('warnings',[]),ensure_ascii=False)))
   if seed_digest:db.execute('INSERT OR REPLACE INTO league_seed_versions VALUES(?,?)',(lid,seed_digest))
 def load_seed(self,directory):
  for file in sorted(Path(directory).glob('*.json')):
   raw=file.read_bytes();snapshot=json.loads(raw);digest=hashlib.sha256(raw).hexdigest()
   with self.db() as db:old=db.execute('SELECT digest FROM league_seed_versions WHERE league_id=?',(snapshot['league_id'],)).fetchone();exists=db.execute('SELECT 1 FROM league_seasons WHERE league_id=? AND season_id=?',(snapshot['league_id'],str(snapshot['season_id']))).fetchone()
   # A bundled snapshot never overwrites a roster already updated by this installation.
   if not exists:self.import_snapshot(snapshot,digest)
 def profile_map(self,league_id,season_id):
  with self.db() as db:
   result={r['account_key']:dict(name=r['name'],photo=r['photo'],rank='',country='',team='',source_url='') for r in db.execute('SELECT a.account_key,p.name,p.photo FROM league_accounts a JOIN league_people p ON p.id=a.person_id')}
   for r in db.execute('''SELECT a.account_key,r.*,t.name AS team,t.country FROM league_rosters r JOIN league_accounts a ON a.person_id=r.person_id JOIN league_teams t ON t.league_id=r.league_id AND t.season_id=r.season_id AND t.code=r.team_code WHERE r.league_id=? AND r.season_id=? ORDER BY r.position DESC''',(league_id,season_id)):
    result[r['account_key']]=dict(name=r['name'],photo=r['photo'] or result.get(r['account_key'],{}).get('photo',''),rank=r['rank'],country=r['country'],team=r['team'],source_url=r['source_url'],person_id=r['person_id'],league_id=league_id,season_id=season_id)
   return result
 def directory(self,league_id=None,season_id=None):
  if not league_id:league_id,season_id=self.selected()
  if season_id is None:season_id=self.setting('season_id:'+league_id,self.seasons(league_id)[0]['season_id'] if self.seasons(league_id) else '')
  with self.db() as db:
   accounts={}
   for r in db.execute('SELECT * FROM league_accounts'):accounts.setdefault(r['person_id'],[]).append(r['account'])
   teams=[]
   for team in db.execute('SELECT * FROM league_teams WHERE league_id=? AND season_id=? ORDER BY name',(league_id,season_id)):
    players=[dict(r,accounts=accounts.get(r['person_id'],[])) for r in db.execute('SELECT * FROM league_rosters WHERE league_id=? AND season_id=? AND team_code=? ORDER BY CASE WHEN position=0 THEN 0 ELSE position END,name',(league_id,season_id,team['code']))]
    teams.append(dict(team,players=players))
   total=db.execute('SELECT COUNT(*) FROM league_people').fetchone()[0]
  return dict(league_id=league_id,season_id=season_id,teams=teams,total_people=total)
 def year_profile(self,account,league_id,year):
  """Never borrow a rank from an adjacent year or another league."""
  import re
  seasons=[s for s in self.seasons(league_id) if year in [int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',s['season_name'])]]
  selected=self.setting('season_id:'+league_id,'')
  seasons.sort(key=lambda s:s['season_id']!=selected)
  for season in seasons:
   p=self.profile_map(league_id,season['season_id']).get(account.lower(),{})
   if p.get('season_id'):return p
  return {}
 def search(self,query,limit=40):
  query=query.casefold().strip()
  with self.db() as db:
   rows=db.execute('SELECT a.account,p.name,p.photo FROM league_accounts a JOIN league_people p ON p.id=a.person_id ORDER BY p.name').fetchall()
  return [dict(r) for r in rows if query in r['account'].casefold() or query in r['name'].casefold()][:limit]

 def year_override(self,account,league_id,year):
  with self.db() as db:
   row=db.execute('SELECT rank,country FROM player_year_overrides WHERE account_key=? AND league_id=? AND year=?',(account.lower(),league_id,year)).fetchone()
   return dict(row) if row else {}
