"""Aurora Pandanet Studio: local-only application, standard-library server."""
import argparse,copy,json,os,queue,secrets,sqlite3,sys,threading,time,webbrowser,shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from player_service import SocialClient,account_name,ArchiveError
from countries import country_code
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parent
APP_VERSION='0.4.7'
sys.path.insert(0,str(ROOT/'transport'))
from reliable import ObservationSession,ServerError
from board import reconstruct,IllegalMove
from leagues import LeagueRegistry
from league_sources import LEAGUES,import_league

class StudioSession(ObservationSession):
    def __init__(self, on_status, **kwargs):
        super().__init__(**kwargs)
        self._on_status = on_status

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == 'status' and getattr(self, '_on_status', None):
            self._on_status(value)


class Studio:
    def __init__(self,data_dir=None):
        self.lock=threading.RLock();self.changed=threading.Condition(self.lock);self.tasks=queue.Queue();self.session=None;self.saved_credentials=None
        self.revision=0;self._published_at=time.monotonic();self._profiles_cache=None;self.selected=set();self.removed=set();self.opening=set()
        self.running=True;self.cache={};self.metadata={};self.last_valid_games={};self.profile_version=0
        self._year_profiles={};self.recordings={};self.recording_handles={};self.job_lock=threading.Lock();self.jobs={};self.query_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='player-query');self.social=SocialClient(lambda:self.saved_credentials);self.site_profiles={};self.history_checked=set();self.history_lock=threading.Lock()
        self.data=Path(data_dir) if data_dir else ROOT/'data';self.data.mkdir(exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS players(account TEXT PRIMARY KEY,name TEXT,country TEXT,rank TEXT,photo TEXT)')
        self.registry=LeagueRegistry(self.data/'players.sqlite3');self.registry.load_seed(ROOT/'league-seed')
        self.league_sync_lock=threading.Lock()
        league_id,season_id=self.registry.selected()
        self.state=dict(server_id=secrets.token_hex(8),joining_room=None,league_id=None,season_id=None,room_league_ids=[],room_capabilities=dict(league=False,league_choice=False),league_sync=dict(busy=False,message=''),connection='disconnected',session_id=secrets.token_hex(6),room_id=0,rooms=[],available=[],watched=[],message='',demo=False,pending=None)
        self.demo()
        self.thread=threading.Thread(target=self.worker,daemon=True);self.thread.start()
    def db(self):return sqlite3.connect(str(self.data/'players.sqlite3'))
    def set_state(self, **values):
        with self.changed:
            if all(self.state.get(k) == v for k, v in values.items()):
                return
            self.state.update(values)
            self.revision += 1
            self._published_at = time.monotonic()
            self.changed.notify_all()

    def profiles(self):
        with self.lock:
            if self._profiles_cache is None:
                with self.db() as db:
                    self._profiles_cache=(self.registry.profile_map(self.state['league_id'],self.state['season_id']) if self.state.get('league_id') else {})
                    for r in db.execute('SELECT * FROM players'):
                        key=r[0].lower();profile=self._profiles_cache.setdefault(key,{})
                        profile.update({k:v for k,v in zip(('name','country','rank','photo'),r[1:]) if v});profile['manual_fields']=[k for k,v in zip(('name','country','rank','photo'),r[1:]) if v]
                        profile['account']=r[0]
            return self._profiles_cache

    def player(self,account,rank,profiles,game_date=None):
        value=date.today().isoformat() if game_date is None else str(game_date)
        year=int(value[:4]) if len(value)>=4 and value[:4].isdigit() else None
        league_id=self.state.get('league_id')
        cache_key=(league_id,year,account.lower())
        if cache_key not in self._year_profiles:self._year_profiles[cache_key]=(self.registry.year_profile(account,league_id,year) if year and league_id else {},self.registry.year_override(account,league_id,year) if year and league_id else {})
        p=profiles.get(account.lower(),{});historical,override=self._year_profiles[cache_key]
        site=self.site_profiles.get(account.lower(),{})
        # Rank and represented country belong to the game year, never a neighboring roster.
        country=override.get('country') or historical.get('country') or (p.get('country') if 'country' in p.get('manual_fields',[]) else '') or site.get('country') or ''
        game_rank=(override.get('rank') or historical.get('rank') or rank or '') if game_date is not None else (p.get('rank') or historical.get('rank') or rank or '')
        return dict(account=account,name=(p.get('name') if 'name' in p.get('manual_fields',[]) else '') or historical.get('name') or p.get('name') or site.get('name') or account,country=country,country_code=country_code(country),rank=game_rank,photo=(p.get('photo') if 'photo' in p.get('manual_fields',[]) else '') or historical.get('photo') or p.get('photo') or site.get('photo') or '',team=historical.get('team',''),source_url=historical.get('source_url') or site.get('source_url',''),person_id=historical.get('person_id') or p.get('person_id'),year=year,rank_source='manual' if override.get('rank') else 'league' if historical.get('rank') else 'game',league_rank=historical.get('rank',''),game_rank=rank or '')
    def demo(self,reset=True):
        raw=json.loads((ROOT/'demo.json').read_text())
        if not reset:
            visible={g['id'] for g in self.state['watched']}
            raw=[g for g in raw if g['id'] in visible]
        profiles=self.profiles();watched=[]
        for g in raw:
            g=copy.deepcopy(g);g['white_player']=self.player(g['white'],g.get('white_rank'),profiles,g.get('date',''));g['black_player']=self.player(g['black'],g.get('black_rank'),profiles,g.get('date',''))
            g['board']=reconstruct(g['moves'],g['size'],handicap=g.get('handicap',0));g['status']='recorded';g['clocks']={}
            watched.append(g)
        self.set_state(league_id=None,season_id=None,room_league_ids=[],room_capabilities=dict(league=False,league_choice=False),connection='disconnected',session_id=secrets.token_hex(6) if reset else self.state['session_id'],demo=True,watched=watched,available=[],rooms=[],message='Gravações reais de teste · sem conexão com o servidor',room_id=0)
    def publish(self):
        s=self.session;self.associate_room();snap=s.snapshot();profiles=self.profiles();watched=[]
        for n,game in snap['games'].items():
            previous=self.metadata.get(n)
            if n in self.selected and previous and (previous.get('white'),previous.get('black'))!=(game.get('white'),game.get('black')):continue
            self.metadata[n]=copy.deepcopy(game)
        for n,p in snap['positions'].items():
            if n not in s.wanted and p.get('status') not in ('finished','adjourned','unavailable','identity_conflict'):continue
            # Global result announcements are not automatically added to the transmission.
            if n not in getattr(self,'selected',set()):continue
            g=copy.deepcopy(self.metadata.get(n,{}));g.update(id=n,white=p.get('white',g.get('white','')),black=p.get('black',g.get('black','')))
            g['size']=g.get('size',19);g['moves']=[dict(v,number=int(k)) for k,v in sorted(p['moves'].items(),key=lambda kv:int(kv[0]))]
            g['status']=p.get('status','live');g['stale']=p.get('stale',False);g['result']=p.get('result');g['clocks']={c:s.clock_view(n,c) for c in ('B','W')}
            g['white_player']=self.player(g['white'],g.get('white_rank'),profiles,g.get('date') or date.today().isoformat());g['black_player']=self.player(g['black'],g.get('black_rank'),profiles,g.get('date') or date.today().isoformat())
            g['clock_sampled_at']=time.monotonic()
            key=(n,g['size'],g.get('handicap',0),json.dumps(g['moves'],sort_keys=True))
            try:
                if key not in self.cache:self.cache[key]=reconstruct(g['moves'],g['size'],handicap=g.get('handicap',0))
                g['board']=self.cache[key]
            except (ValueError,KeyError,TypeError):
                g=self.retain_valid_position(g,s)
            if g.get('board') is not None:self.last_valid_games[n]=copy.deepcopy(g)
            watched.append(g)
        watched.extend(copy.deepcopy(list(self.recordings.values())))
        if len(self.cache)>200:self.cache.clear()
        with self.lock:
            watched=[g for g in watched if g['id'] not in self.removed]
            self.set_state(connection=s.status,demo=False,room_id=s.room_id,rooms=list(s.rooms.values()),available=list(s.games.values()),watched=watched)
    def retain_valid_position(self,game,session):
        """Publish a coherent board AND matching move list; never skip a corrupt move."""
        n=game['id'];previous=self.last_valid_games.get(n)
        if previous and (previous['white'],previous['black'])==(game['white'],game['black']):
            safe=copy.deepcopy(previous)
            for key in ('status','result','clocks','clock_sampled_at','white_player','black_player'):
                safe[key]=game.get(key)
        else:
            safe=copy.deepcopy(game)
            # Prefix validity is monotonic: once a move fails, every longer history fails.
            # This path is only needed when the first received history is already corrupt.
            low=0;high=len(game['moves'])
            try:
                board=reconstruct([],game['size'],handicap=game.get('handicap',0))
                while low<high:
                    mid=(low+high+1)//2
                    try:candidate=reconstruct(game['moves'][:mid],game['size'],handicap=game.get('handicap',0))
                    except (ValueError,KeyError,TypeError):high=mid-1
                    else:low=mid;board=candidate
                safe['board']=board;safe['moves']=game['moves'][:low]
            except (ValueError,KeyError,TypeError):safe['board']=None;safe['moves']=[]
        safe.pop('board_error',None)
        safe['stale']=game['status']!='finished';safe['sync_pending']=game['status']!='finished'
        if n in session.wanted and game['status'] not in ('finished','identity_conflict'):
            session.needs_sync.add(n)
        # Keep diagnostics out of the broadcast, while retaining the original input in
        # the transport's bounded transcript for investigation.
        return safe

    def dispatch(self, action, data):
        if action == 'unobserve':
            # Membership in our transmission is local, even when the game is over
            # or the network worker is occupied with a slow server response.
            n = int(data['id'])
            with self.lock:
                self.removed.add(n)
                self.selected.discard(n)
                self.recordings.pop(n,None);self.last_valid_games.pop(n,None)
                watched = [g for g in self.state['watched'] if g['id'] != n]
                self.set_state(watched=watched)
        elif action == 'observe':
            with self.lock:
                n=int(data['id'])
                if n in self.selected or n in self.opening or any(g['id']==n for g in self.state['watched']):
                    return dict(accepted=False,already_watched=True)
                self.removed.discard(n);self.opening.add(n)
                self.set_state(opening_ids=sorted(self.opening))
        if action=='join':self.set_state(joining_room=int(data['room_id']))
        self.tasks.put((action, data))
        return dict(accepted=True)

    def worker(self):
        while self.running:
            action = None
            try:
                try:
                    action, data = self.tasks.get(timeout=0 if self.session else .15)
                except queue.Empty:
                    data = {}
                if action:
                    self.set_state(pending=action)
                    if action in ('connect', 'demo', 'disconnect'):
                        if self.session:
                            self.session.close()
                            self.session = None
                        self.saved_credentials = None
                        if action in ('disconnect','demo'):self.social.reset()
                        self.recordings.clear();self.recording_handles.clear()
                        with self.lock:
                            self.selected.clear()
                            self.removed.clear()
                        self.cache.clear();self._profiles_cache=None;self._year_profiles.clear()
                        self.metadata.clear();self.last_valid_games.clear()
                    if action == 'connect':
                        username = data.get('username', '').strip()
                        password = data.pop('password', '')
                        self.saved_credentials = (username, password) if username else None
                        password = None
                        self.session = StudioSession(on_status=lambda status:self.set_state(connection=status), credentials=lambda:self.saved_credentials or (None,None))
                        self.set_state(league_id=None,season_id=None,room_league_ids=[],room_capabilities=dict(league=False,league_choice=False),connection='connecting',session_id=secrets.token_hex(6),demo=False,message='Conectando ao Pandanet…',watched=[])
                        self.session.connect()
                        self.session.command('room')
                        self.session.refresh_games()
                        self.set_state(message='Conexão estabelecida.')
                    elif action == 'demo':
                        self.demo()
                    elif action == 'disconnect':
                        self.set_state(league_id=None,season_id=None,room_league_ids=[],room_capabilities=dict(league=False,league_choice=False),connection='disconnected',demo=False,message='Desconectado.',watched=[],available=[])
                    elif action == 'join':
                        self.require_session().join(int(data['room_id']))
                        # Room entry is confirmed even if its games query is slow or fails.
                        self.publish()
                        self.session.refresh_games()
                        self.set_state(message='')
                    elif action == 'refresh':
                        self.require_session().command('room')
                        self.session.refresh_games()
                        self.set_state(message='')
                    elif action == 'profiles':
                        if self.session:
                            self.publish()
                    elif action == 'observe':
                        n = int(data['id'])
                        if n not in self.selected:self.metadata.pop(n,None);self.last_valid_games.pop(n,None)
                        self.require_session().observe(n)
                        with self.lock:
                            if n not in self.removed:
                                self.selected.add(n)
                        self.set_state(message='')
                    elif action == 'unobserve':
                        n = int(data['id'])
                        if self.session:
                            try:
                                self.session.unobserve(n)
                            except (ServerError, TimeoutError, OSError):
                                # Never put a removed game back into the transmission.
                                pass
                    if self.session:
                        self.publish()
                if self.session and self.session.status == 'connected':
                    if not self.session.poll(.1):
                        self.set_state(message='Conexão interrompida. Use Conectar para tentar novamente.')
                    events = self.session.drain_events()
                    for event in events:
                        if event['type'] == 'recovered' and event['previous_id'] in self.selected:
                            with self.lock:
                                self.selected.discard(event['previous_id'])
                                self.selected.add(event['game_id'])
                            if event['previous_id'] in self.metadata:
                                self.metadata[event['game_id']] = copy.deepcopy(self.metadata[event['previous_id']])
                    if any(e['type'] != 'raw' or e.get('line','').startswith(('15 ', '7 ', '9 ROOM')) for e in events):
                        self.publish()
            except Exception as error:
                message = str(error)
                if 'need to be registered' in message.lower():
                    message = 'Esta sala exige uma conta registrada. Desconecte e entre com seu usuário e senha.'
                elif isinstance(error, TimeoutError):
                    message = 'O Pandanet demorou a responder. Tente atualizar ou reconectar.'
                self.set_state(message=message[:450])
                if self.session and self.session.status in ('connecting','disconnected','authentication_required'):
                    self.session.close()
                    self.session = None
                    self.saved_credentials = None
            finally:
                if action:
                    with self.lock:
                        if action=='observe':self.opening.discard(int(data['id']))
                        self.set_state(pending=None,opening_ids=sorted(self.opening),**({'joining_room':None} if action=='join' else {}))
                    self.tasks.task_done()

    def require_session(self):
        if not self.session or self.session.status!='connected':raise ValueError('Conecte ao Pandanet primeiro.')
        return self.session
    def snapshot(self):
        with self.lock:
            snapshot=copy.deepcopy(self.state)
            snapshot['revision']=self.revision
            for game in snapshot['watched']:
                game['clock_age']=max(0,time.monotonic()-game.pop('clock_sampled_at',time.monotonic()))
            if self.session:
                snapshot['connection']=self.session.status
                if self.session.status!='connected':
                    for game in snapshot['watched']:game['stale']=True
            return snapshot
    def board_at(self,data):
        state=self.snapshot();g=next((g for g in state['watched'] if g['id']==int(data['id'])),None)
        if not g:raise ValueError('Partida não encontrada.')
        variation=data.get('variation',[])
        if len(variation)>1000:raise ValueError('Variação muito longa.')
        for move in variation:
            if move.get('color') not in ('B','W'):raise ValueError('Cor inválida.')
        return reconstruct(g['moves'],g['size'],int(data.get('ply',len(g['moves']))),variation,g.get('handicap',0),setup=g.get('setup') or None,next_color=g.get('next_color'))
    def refresh_profiles(self):
        with self.lock:self._profiles_cache=None;self._year_profiles.clear()
        profiles=self.profiles()
        with self.lock:
            watched=copy.deepcopy(self.state['watched'])
            for g in watched:
                for color in ('white','black'):g[color+'_player']=self.player(g[color],g.get(color+'_rank'),profiles,g.get('date','') if g.get('recorded') or self.state['demo'] else date.today().isoformat())
            self.recordings.update({g['id']:copy.deepcopy(g) for g in watched if g.get('recorded')})
            self.set_state(watched=watched)
    def associated_leagues(self):
        from league_sources import leagues_for_room
        session=self.session
        if not session or session.room_id==0:return []
        room=session.rooms.get(session.room_id,{})
        return leagues_for_room(room.get('name',''))

    def associate_room(self):
        # Publish room, roster context and available games as one coherent state.
        with self.lock:
            leagues=self.associated_leagues();ids=[league['id'] for league in leagues]
            current=self.state.get('league_id')
            league_id=current if current in ids else ids[0] if ids else None
            season_id=(self.state.get('season_id') if current==league_id else self.registry.directory(league_id)['season_id']) if league_id else None
            changed=(current,self.state.get('season_id'))!=(league_id,season_id)
            if changed and league_id:self.registry.configure(league_id,season_id)
            session=self.session
            self.set_state(room_id=session.room_id if session else 0,
                           rooms=list(session.rooms.values()) if session else [],
                           available=list(getattr(session,'games',{}).values()) if session else [],
                           room_league_ids=ids,room_capabilities=dict(league=bool(ids),league_choice=len(ids)>1),league_id=league_id,season_id=season_id)
            if changed:self.refresh_profiles()

    def choose_room_season(self,data):
        league_id=data.get('league_id')
        if league_id not in [league['id'] for league in self.associated_leagues()]:
            raise ValueError('A liga é determinada pela sala selecionada.')
        return self.choose_league(dict(league_id=league_id,season_id=data.get('season_id')))

    def choose_league(self,data):
        league_id,season_id=self.registry.configure(str(data.get('league_id','')),data.get('season_id'))
        with self.lock:
            self.set_state(league_id=league_id,season_id=season_id)
            self.refresh_profiles()
        return dict(saved=True,league_id=league_id,season_id=season_id)
    def observe_team(self,data):
        # Resolve the roster on the server as well: an empty team never means all games.
        with self.lock:
            self.require_session()
            league_id,season_id=self.state.get('league_id'),self.state.get('season_id')
            if not league_id:raise ValueError('Esta sala não tem uma liga associada.')
            if (data.get('league_id'),data.get('season_id'))!=(league_id,season_id) or data.get('room_id')!=self.state['room_id']:
                raise ValueError('A liga, temporada ou sala mudou. Atualize a lista e tente novamente.')
            team_code=str(data.get('team_code',''))
            directory=self.registry.directory()
            team=next((t for t in directory['teams'] if t['code']==team_code),None) if team_code else None
            if not team:raise ValueError('Selecione uma equipe para acompanhar suas partidas.')
            accounts={a.lower() for p in team['players'] for a in p['accounts']}
            games=[g for g in self.state['available'] if any(str(g.get(c,'')).lower() in accounts for c in ('white','black'))]
            queued=[]
            for game in games:
                if self.dispatch('observe',dict(id=game['id']))['accepted']:queued.append(game['id'])
            return dict(accepted=True,queued=queued)

    def league_directory(self):
        if not self.state.get('league_id'):return dict(league_id=None,season_id=None,teams=[],total_people=0)
        result=self.registry.directory(self.state['league_id'],self.state['season_id']);profiles=self.profiles()
        for team in result['teams']:
            for person in team['players']:
                imported=dict(name=person['name'],rank=person['rank'],photo=person['photo'],country=team['country'])
                person['imported']=imported
                for account in person['accounts']:
                    if account.lower() in profiles:
                        override=profiles[account.lower()]
                        for key in ('name','photo'):person[key]=override.get(key) or person[key]
                        season=next((s for s in self.registry.seasons(result['league_id']) if s['season_id']==result['season_id']),{})
                        import re
                        years=re.findall(r'\b(?:19|20)\d{2}\b',season.get('season_name',''))
                        scoped=self.registry.year_override(account,result['league_id'],int(years[0])) if years else {}
                        person['rank']=scoped.get('rank') or person['rank']
                        break
        return result
    def sync_league(self,data):
        if not self.state.get('league_id') or data.get('league_id',self.state['league_id'])!=self.state['league_id']:raise ValueError('Esta sala não tem a liga solicitada associada.')
        league_id=self.state['league_id'];league=next((l for l in LEAGUES if l['id']==league_id),None)
        if not league:raise ValueError('Liga desconhecida.')
        if not self.league_sync_lock.acquire(blocking=False):raise ValueError('Já há uma atualização de cadastros em andamento.')
        self.set_state(league_sync=dict(busy=True,league_id=league_id,message='Consultando o Pandanet…'))
        origin_session=self.session;origin_room=self.session.room_id if self.session else None;origin_season=self.state.get('season_id')
        def run():
            try:
                snapshot=import_league(league,lambda message:self.set_state(league_sync=dict(busy=True,league_id=league_id,message=message)))
                self.registry.import_snapshot(snapshot)
                # Follow a newly published season only when this is the active league.
                with self.lock:
                    if self.session is origin_session and (self.session.room_id if self.session else None)==origin_room and self.state.get('league_id')==league_id and self.state.get('season_id')==origin_season:
                        self.choose_league(dict(league_id=league_id,season_id=snapshot['season_id']))
                self.refresh_profiles()
                self.set_state(league_sync=dict(busy=False,league_id=league_id,message='Cadastro atualizado.',updated_at=snapshot['imported_at']))
            except Exception as error:self.set_state(league_sync=dict(busy=False,league_id=league_id,message=str(error)[:1500],error=True))
            finally:self.league_sync_lock.release()
        threading.Thread(target=run,daemon=True).start()
        return dict(accepted=True)
    def submit_query(self,kind,data):
        if kind not in ('profile','search','archive','archive-login','archive-load','archive-logout'):raise ValueError('Consulta desconhecida.')
        with self.job_lock:
            now=time.monotonic();self.jobs={k:v for k,v in self.jobs.items() if now-v['created']<600}
            if sum(not j['done'] for j in self.jobs.values())>=8:raise ValueError('Aguarde as consultas em andamento.')
            token=secrets.token_urlsafe(18);self.jobs[token]=dict(created=now,done=False)
        def run():
            try:
                if kind=='archive-login':result=self.social.login(data.get('username'),data.pop('password',''))
                elif kind=='archive-logout':result=self.social.logout()
                elif kind=='search':
                    query=str(data.get('query','')).strip()
                    if not query or len(query)>80:raise ValueError('Informe um nome ou conta.')
                    local=self.registry.search(query);remote=[];warning=''
                    try:remote=self.social.search(query)
                    except ArchiveError as error:warning=str(error)
                    merged={p['account'].lower():dict(p,origin='site') for p in remote}
                    merged.update({p['account'].lower():dict(p,origin='database') for p in local})
                    result=dict(players=list(merged.values()),warning=warning)
                elif kind=='profile':
                    account=account_name(data.get('account',''));game_date=str(data.get('date',date.today().isoformat()));year=int(game_date[:4]) if game_date[:4].isdigit() else None;league=self.registry.selected()[0]
                    try:
                        if year:self.ensure_history(league,year)
                    except Exception:pass
                    p=self.player(account,data.get('rank',''),self.profiles(),game_date);warning=''
                    if not p['country'] or not p['photo'] or p['name']==account:
                        try:self.site_profiles[account.lower()]=self.social.profile(account);p=self.player(account,data.get('rank',''),self.profiles(),game_date);self.refresh_profiles()
                        except ArchiveError as error:warning=str(error)
                    result=dict(player=p,warning=warning)
                elif kind=='archive':result=self.social.games(data.get('account',''),data.get('page',1),data.get('force',False))
                else:result=self.load_archive(data['handle'])
                with self.job_lock:self.jobs[token].update(done=True,result=result)
            except Exception as error:
                message=str(error) if isinstance(error,ValueError) else 'Falha na consulta. Tente novamente.'
                with self.job_lock:
                    if token in self.jobs:self.jobs[token].update(done=True,error=message[:500])
            finally:data.pop('password',None)
        self.query_pool.submit(run);return dict(job=token)
    def query_result(self,token):
        with self.job_lock:
            job=self.jobs.get(token)
            if not job:raise ValueError('Consulta expirada.')
            return {k:v for k,v in job.items() if k!='created'}
    def ensure_history(self,league_id,year):
        if not 1990<=year<=date.today().year+1:return
        if self.registry.year_profile('__none__',league_id,year):return
        import re
        if any(str(year) in re.findall(r'\b(?:19|20)\d{2}\b',s['season_name']) for s in self.registry.seasons(league_id)):return
        key=(league_id,year)
        with self.history_lock:
            if key in self.history_checked:return
            from league_sources import seasons_for_year,import_season
            league=next(l for l in LEAGUES if l['id']==league_id)
            for sid,name in seasons_for_year(league,year):self.registry.import_snapshot(import_season(league,sid,name))
            self.history_checked.add(key)
            with self.lock:self._profiles_cache=None;self._year_profiles.clear()
    def load_archive(self,handle):
        with self.lock:
            existing=self.recording_handles.get(handle)
            if existing in self.recordings:return dict(id=existing,loaded=True)
        g=self.social.sgf(handle)
        try:self.ensure_history(self.registry.selected()[0],int(g['date'][:4]))
        except Exception:pass
        profiles=self.profiles()
        for color in ('white','black'):g[color+'_player']=self.player(g[color],g.get(color+'_rank'),profiles,g['date'])
        with self.lock:
            g['id']=min([-1,*self.recordings.keys()])-1;self.recordings[g['id']]=copy.deepcopy(g);self.recording_handles[handle]=g['id'];self.removed.discard(g['id'])
            self.set_state(watched=self.state['watched']+[g])
        return dict(id=g['id'],loaded=True)
    def save_player(self,data):
        account=str(data.get('account','')).strip()
        if not account or len(account)>50:raise ValueError('Conta inválida.')
        photo=str(data.get('photo','')).strip()
        if photo and not photo.startswith('https://'):raise ValueError('Use um endereço HTTPS para a foto.')
        year=data.get('year');league_id=data.get('league_id',self.registry.selected()[0])
        if year is not None:
            year=int(year)
            if not 1990<=year<=date.today().year+1 or league_id not in {l['id'] for l in LEAGUES}:raise ValueError('Ano ou liga inválidos.')
        with self.db() as db:
            old=db.execute('SELECT rank,country FROM players WHERE account=?',(account.lower(),)).fetchone() or ('','')
            db.execute('INSERT OR REPLACE INTO players VALUES(?,?,?,?,?)',(account.lower(),str(data.get('name','')).strip()[:500],old[1] if year else str(data.get('country','')).strip()[:500],old[0] if year else str(data.get('rank','')).strip()[:500],photo[:2000]))
            if year:db.execute('INSERT OR REPLACE INTO player_year_overrides VALUES(?,?,?,?,?)',(account.lower(),league_id,year,str(data.get('rank','')).strip()[:100],str(data.get('country','')).strip()[:100]))

        with self.lock:self._profiles_cache=None;self._year_profiles.clear()
        self.refresh_profiles()
        return dict(saved=True)

from photo_service import PhotoCache
PHOTO_CACHE=PhotoCache()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def valid(self):
        host=self.headers.get('Host','')
        if host not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
            self.send_error(403);return False
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            self.send_error(403);return False
        return True
    def answer(self,data,status=200):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def end_headers(self):
        # Browser analysis uses shared WASM memory on Safari and Chromium.
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        super().end_headers()

    def do_GET(self):
        if not self.valid():return
        path=urlparse(self.path).path
        if path=='/api/leagues':return self.answer(dict(leagues=self.server.studio.registry.catalog()))
        if path=='/api/directory':return self.answer(self.server.studio.league_directory())
        if path=='/api/state':return self.answer(self.server.studio.snapshot())
        if path=='/api/events':return self.events()
        if path=='/api/query':
            try:return self.answer(self.server.studio.query_result(parse_qs(urlparse(self.path).query).get('job',[''])[0]))
            except ValueError as error:return self.answer(dict(error=str(error)),404)
        if path=='/api/archive-status':return self.answer(dict(connected=bool(self.server.studio.social.user),account=self.server.studio.social.user))
        if path=='/api/photo':
            try:
                url=parse_qs(urlparse(self.path).query).get('url',[''])[0]
                if len(url)>2000:raise ValueError('Endereço muito longo.')
                kind,data=PHOTO_CACHE.get(url)
                self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','private, max-age=3600');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
            except (ValueError,OSError):self.send_error(404)
            return
        if path=='/api/health':return self.answer(dict(status='ok',app='Aurora Pandanet Studio',version=APP_VERSION))
        name='index.html' if path=='/' else path.lstrip('/')
        file=ROOT/'static'/name
        if not file.resolve().is_relative_to((ROOT/'static').resolve()) or not file.is_file():return self.send_error(404)
        types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json; charset=utf-8','.ttf':'font/ttf','.wasm':'application/wasm'}
        self.send_response(200);self.send_header('Content-Type',types.get(file.suffix,'application/octet-stream'));self.send_header('Cache-Control','no-cache');self.send_header('Content-Length',str(file.stat().st_size));self.end_headers()
        try:
            with file.open('rb') as source:shutil.copyfileobj(source,self.wfile,512*1024)
        except (BrokenPipeError,ConnectionResetError):pass
    def events(self):
        studio = self.server.studio
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream; charset=utf-8')
        self.send_header('Cache-Control','no-cache, no-transform')
        self.send_header('X-Accel-Buffering','no')
        self.end_headers()
        last = -1
        try:
            while studio.running:
                with studio.changed:
                    if studio.revision == last:
                        studio.changed.wait(timeout=15)
                    changed = studio.revision != last
                    if changed:
                        snapshot = studio.snapshot()
                        last = snapshot['revision']
                if changed:
                    payload = f"id: {last}\ndata: {json.dumps(snapshot,ensure_ascii=False)}\n\n"
                else:
                    payload = ': heartbeat\n\n'
                self.wfile.write(payload.encode('utf-8'))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_POST(self):
        if not self.valid():return
        # Custom header forces a preflight for foreign origins; no CORS is enabled.
        if self.headers.get('X-Aurora')!='studio':return self.answer(dict(error='Solicitação inválida.'),403)
        try:
            length=int(self.headers.get('Content-Length',0))
            if length<0 or length>200000:raise ValueError('Solicitação muito grande.')
            data=json.loads(self.rfile.read(length) or b'{}');path=urlparse(self.path).path
            if not isinstance(data,dict):raise ValueError('Solicitação inválida.')
            if path=='/api/player-query':return self.answer(self.server.studio.submit_query(str(data.pop('kind','')),data),202)
            if path=='/api/league':return self.answer(self.server.studio.choose_room_season(data))
            if path=='/api/observe-team':return self.answer(self.server.studio.observe_team(data),202)
            if path=='/api/league-sync':return self.answer(self.server.studio.sync_league(data),202)
            if path=='/api/board':return self.answer(self.server.studio.board_at(data))
            if path=='/api/player':return self.answer(self.server.studio.save_player(data))
            action=path.removeprefix('/api/')
            if action not in ('connect','disconnect','join','refresh','observe','unobserve','demo'):return self.send_error(404)
            return self.answer(self.server.studio.dispatch(action,data),202)
        except (ValueError,KeyError,IllegalMove) as error:self.answer(dict(error=str(error)),400)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);ap.add_argument('--open',action='store_true');args=ap.parse_args()
    import urllib.request
    server=None
    for port in range(args.port,args.port+10):
        try:
            server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
            break
        except OSError as error:
            url=f'http://127.0.0.1:{port}'
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=1) as response:existing=json.load(response)
                if existing.get('app')=='Aurora Pandanet Studio' and existing.get('version')==APP_VERSION:
                    print('Aurora '+APP_VERSION+' já está aberto: '+url,flush=True)
                    if args.open:webbrowser.open(url)
                    return
                if existing.get('app')=='Aurora Pandanet Studio':
                    print('Versão anterior aberta em '+url+'; abrindo a versão '+APP_VERSION+' em outra porta.',flush=True)
            except (OSError,ValueError):pass
            if isinstance(error,PermissionError):
                print('Sem permissão para abrir uma porta local.',flush=True)
                return
    if server is None:
        print('Não foi possível abrir uma porta local. Feche a versão anterior e tente novamente.',flush=True)
        return
    server.studio=Studio()
    url=f'http://127.0.0.1:{server.server_port}';print('Aurora Pandanet Studio: '+url,flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.studio.running=False
        server.studio.social.reset();server.studio.query_pool.shutdown(wait=False)
        if server.studio.session:server.studio.session.close()
        server.server_close()
if __name__=='__main__':main()
