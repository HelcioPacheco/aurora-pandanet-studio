"""Single-owner IGS observation session with recovery and typed state.

Run networking only from one worker; UI consumes snapshot()/drain_events().
Credentials are supplied by a callable and never written to disk.
"""
import copy
import re
import socket
import time
from collections import deque
from decimal import Decimal
from pandanet import Pandanet as Transport


class ServerError(RuntimeError):
    pass


class AuthenticationError(ServerError):
    pass


def result_code(text):
    lower = text.lower()
    loser = re.search(r'\b(white|black)\s+(?:lost by|resigns|forfeits)', lower)
    if loser:
        winner = 'B' if loser[1] == 'white' else 'W'
        if 'resign' in lower: return winner + '+R'
        if 'time' in lower: return winner + '+T'
        margin = re.search(r'lost by\s+([\d.]+)', lower)
        if margin: return winner + '+' + margin[1]
    score = re.search(r'\b([WB])\s+([\d.]+)\s+([WB])\s+([\d.]+)', text)
    if score and score[1] != score[3]:
        a, b = Decimal(score[2]), Decimal(score[4])
        return '0' if a == b else (score[1] if a > b else score[3]) + '+' + str(abs(a-b))
    if 'jigo' in lower: return '0'
    return None


class ObservationSession(Transport):
    def __init__(self, host='igs.joyjoy.net', port=7777, credentials=None,
                 clock=time.monotonic, sleep=time.sleep):
        super().__init__(host, port)
        self.events = deque(maxlen=5000)
        self.transcript = deque(maxlen=1000)
        self.credentials = credentials
        self.clock, self.sleep = clock, sleep
        self.room_id = 0
        self.wanted = set()
        self.needs_sync = set()
        self.status = 'disconnected'
        self._history = None
        self._history_moves = {}
        self._busy = False
        self._last_refresh = 0
        self._last_response = 0
        self._stopped = False

    def emit(self, kind, **data):
        self.events.append(dict(type=kind, **data))

    def position(self, n):
        return self.positions.setdefault(n, {'moves':{}, 'status':'live', 'stale':False, 'clocks':{}})

    def parse(self, line):
        # Inspect lifecycle and identity before the base parser can mutate a record.
        header = re.match(r'15 Game (\d+)\s+[^:]+:\s+(\S+)\s+\(([^)]+)\)\s+vs\s+(\S+)\s+\(([^)]+)\)', line)
        move = re.match(r'15\s+(\d+)\(([BW])\):\s*(\S+)(.*)', line)
        clock_target=re.match(r'15 TIME:\s*(\d+):',line)
        if clock_target and self.positions.get(int(clock_target[1]),{}).get('status') in ('finished','identity_conflict'):
            self.emit('raw',line=line);return
        if header:
            n=int(header[1]);old=self.positions.get(n,{})
            if old.get('status')=='finished':
                self.context=None;self.emit('raw',line=line);return
            if old.get('white') and old.get('black') and (old['white'],old['black'])!=(header[2],header[4]):
                old.update(status='identity_conflict',stale=True,to_play=None)
                self.wanted.discard(n);self.needs_sync.discard(n);self.context=None
                self.emit('raw',line=line);self.emit('identity_conflict',game_id=n,candidate_id=n);return
        if move:
            n=self.context;old=self.positions.get(n,{})
            if n is None or old.get('status')=='finished' and self._history!=n:
                self.emit('raw',line=line);return
            value=dict(color=move[2],point=move[3])
            if move[4].strip():value['extra']=move[4].strip().split()
            # Full histories are staged without leaking partial replacements into live state.
            if self._history==n:
                self.emit('raw',line=line);self._history_moves[int(move[1])]=value;return
            # A replayed move is not an undo and must not erase the following history.
            previous=old.get('moves',{}).get(int(move[1]))
            if previous and (previous['color'],previous['point'].upper())==(value['color'],value['point'].upper()) and n not in self.needs_sync:
                self.emit('raw',line=line);return
            if move[3].lower() in ('resign','resigns'):
                self.emit('raw',line=line)
                old.update(status='finished',result=('W' if move[2]=='B' else 'B')+'+R',to_play=None,stale=False)
                self.wanted.discard(n);self.needs_sync.discard(n)
                self.emit('finished',game_id=n,result=old['result']);return
        previous_moves = dict(self.positions.get(self.context, {}).get('moves', {}))
        super().parse(line)
        if self.events and self.events[-1].get('type') == 'move':
            self.events.pop()
        if header:
            n = int(header[1]); p = self.position(n)
            p.setdefault('clocks', {})
            for color, values in [('W', header[3]), ('B', header[5])]:
                fields = values.split()
                if len(fields) == 3:
                    p['clocks'][color] = dict(captures=int(fields[0]), seconds=int(fields[1]),
                                              stones=int(fields[2]), received_at=self.clock(), source='header')
        move = re.match(r'15\s+(\d+)\(([BW])\):\s*(\S+)(.*)', line)
        if move and self.context is not None:
            n = self.context; p = self.position(n); number = int(move[1])
            value = dict(color=move[2], point=move[3])
            if move[4].strip(): value['extra'] = move[4].strip().split()
            if self._history == n:
                self._history_moves[number] = value
            else:
                # A lower/replaced move invalidates all following moves.
                later = [k for k in p['moves'] if k > number]
                if later:
                    for k in later: del p['moves'][k]
                    self.emit('correction', game_id=n, last_move=number)
                    self.needs_sync.add(n)
                if previous_moves and number > max(previous_moves)+1:
                    self.needs_sync.add(n); p['stale']=True
                    self.emit('gap',game_id=n,number=number)
                p['moves'][number] = value
                if previous_moves.get(number) != value:
                    self.emit('move', game_id=n, number=number, **value)
            p['to_play'] = 'W' if move[2] == 'B' else 'B'
            p['turn_at'] = self.clock()
            p.setdefault('status', 'live'); p.setdefault('stale', False)
        timer = re.match(r'15 TIME:\s*(\d+):([^:]+)\(([BW])\):\s*(\d+)\s+(\d+)/(\d+)\s+(\d+)/(\d+)(.*)', line)
        if timer:
            n = int(timer[1]); main = int(timer[5]); byo = int(timer[7])
            p = self.position(n)
            p.setdefault('clocks', {})[timer[3]] = dict(
                player=timer[2], phase_code=int(timer[4]), main_seconds=main,
                main_total=int(timer[6]), byoyomi_seconds=byo, byoyomi_total=int(timer[8]),
                seconds=main if main else byo, extra=timer[9].strip(),
                received_at=self.clock(), source='TIME')
            # Remaining fractions vary by server time system; preserve all pairs.
            fractions = re.findall(r'(-?\d+)/(-?\d+)', line.split('):',1)[-1])
            p['clocks'][timer[3]]['fractions'] = [[int(a),int(b)] for a,b in fractions]
            if len(fractions)>2: p['clocks'][timer[3]]['stones'] = int(fractions[2][0])
            self.emit('clock', game_id=n, color=timer[3])
        undo = re.match(r'28 Undo in game (\d+):', line)
        if undo:
            n=int(undo[1])
            if self.positions.get(n,{}).get('status')=='finished':return
            self.needs_sync.add(n); self.position(n)['stale']=True
            self.emit('undo', game_id=n)
        elif line.startswith('28 ') and 'undid the last move' in line:
            player=line.split()[1]
            for n,p in self.positions.items():
                if p.get('status')!='finished' and player in (p.get('white'),p.get('black')):
                    self.needs_sync.add(n);p['stale']=True;self.emit('undo',game_id=n)
        match = re.search(r'(?:\{)?Game (\d+):\s*(\S+) vs\.? (\S+)\s*(.*)', line)
        if match and line.startswith(('9 ', '21 ')):
            n=int(match[1]); white=match[2]; black=match[3]; detail=match[4].rstrip('}')
            known=self.positions.get(n,{})
            if known.get('white') and known.get('black') and (known['white'],known['black'])!=(white,black):return
            if known.get('status')=='finished':return
            if '@ Move' in detail:
                for old_id,p in list(self.positions.items()):
                    if p.get('status')=='adjourned' and (p.get('white'),p.get('black'))==(white,black):
                        if old_id in self.wanted:
                            # Candidate only: identity is verified against full history before adoption.
                            p['resume_candidate']=n
                            self.emit('resume_candidate', game_id=old_id, candidate_id=n)
            elif 'adjourned' in detail:
                p=self.position(n);p.update(status='adjourned',stale=True,white=white,black=black,to_play=None)
                self.emit('adjourned',game_id=n)
            elif result_code(detail) is not None or any(word in detail.lower() for word in ('resign','lost by','forfeit','jigo')):
                p=self.position(n);p.update(status='finished',result=result_code(detail),result_text=detail,to_play=None)
                self.games.pop(n,None);self.wanted.discard(n);self.needs_sync.discard(n)
                p['stale']=False
                self.emit('finished',game_id=n,result=p['result'],detail=detail)
        if line.startswith('9 ') and ('has resigned the game' in line or 'has run out of time' in line):
            player=line.split()[1]
            for n,p in self.positions.items():
                if p.get('status','live')=='live' and player in (p.get('white'),p.get('black')):
                    loser='W' if player==p.get('white') else 'B'
                    p.update(status='finished',result=('B' if loser=='W' else 'W')+('T' if 'time' in line else 'R'),result_text=line,to_play=None)
                    p['result']=p['result'][0]+'+'+p['result'][1:]
                    self.wanted.discard(n);self.needs_sync.discard(n);p['stale']=False;self.emit('finished',game_id=n,result=p['result'])

    def command(self, command):
        if self._busy: raise RuntimeError('Use a single networking worker; concurrent commands are unsupported')
        self._busy=True
        try:
            verb,*args=command.split()
            target=args[0] if args else None
            expected={
                'room':r'9 ROOMLIST',
                'games':r'7 \[##\]',
                'observe':r'9 .*?(?:Adding game|already.*observ)',
                'unobserve':r'9 .*?(?:Removing game|not.*observ)',
                'toggle':r'9 Set client',
                'join':None,
            }.get(verb)
            if verb=='join':expected=self.room_confirmation_pattern(int(target))
            if verb=='moves':
                expected=r'15\s+0\([BW]\):'
                if self.games.get(int(target),{}).get('move_count')==0:
                    expected=r'15 Game '+target+r'\s'
            self.send(command)
            response='';end=self.clock()+15
            while self.clock()<end:
                response+=self.receive(min(1,end-self.clock()))
                errors=list(re.finditer(r'(?:^|\n)5 [^\n]+',response))
                marker=re.search(expected,response,re.I) if expected else None
                prompts=list(re.finditer(r'(?:^|\n)1 \d+\r?\n',response))
                if prompts and errors and prompts[-1].start()>errors[-1].start():
                    raise ServerError(response.strip())
                if prompts and marker and prompts[-1].start()>marker.start():
                    self._last_response=self.clock()
                    return response
            raise TimeoutError('No matching response for '+verb)
        finally: self._busy=False

    def connect(self, username=None, password=None):
        if self.sock:
            self.sock.close()
        self.closed=False;self.buffer=b'';self.context=None;self.telnet_state='data'
        self.status='connecting'
        if username is None and self.credentials:
            username,password=self.credentials()
        try:
            # Explicitly validate success, rather than accepting any numbered prompt.
            self.sock=socket.create_connection((self.host,self.port),10)
            self.wait_for(r'Login:')
            if username is None:
                self.send('guest');self.wait_for(r'#>|(?:^|\n)1 5\r?\n')
            else:
                if not re.fullmatch(r'[A-Za-z0-9_-]+',username): raise ValueError('Invalid username')
                if not password or '\n' in password or '\r' in password: raise ValueError('Invalid password')
                self.sock.sendall((username+'\r\n').encode('ascii'))
                self.wait_for(r'Password:|(?:^|\n)1 1\r?\n')
                self.sock.sendall((password+'\r\n').encode('ascii'))
                response=self.wait_for(r'#>|(?:^|\n)1 (?:1|5)\r?\n|Login:|[Ii]nvalid password|[Ww]rong password')
                if not ('#>' in response or re.search(r'(?:^|\n)1 5\r?\n',response)):
                    raise AuthenticationError('Pandanet did not confirm login')
            self.command('toggle client true')
            self.status='connected';self._stopped=False;self.emit('connected')
        except Exception:
            if self.sock: self.sock.close()
            self.closed=True;self.status='disconnected'
            raise
        finally: password=None

    def room_confirmation_pattern(self, room_id):
        if int(room_id)==0:
            # Pandanet confirms returning to the main room by saying "leaving",
            # not "left". Other users' room notifications are never confirmations.
            return r'(?:^|\n)9 You are leaving game room #'+str(self.room_id)+r'(?!\d)'
        return r'(?:^|\n)9 Welcome to the game room #'+str(int(room_id))+r'(?!\d)'

    def join(self, room_id):
        room_id=int(room_id)
        if room_id==0 and self.room_id==0:return ''
        pattern=self.room_confirmation_pattern(room_id)
        response=self.command('join '+str(room_id))
        if not re.search(pattern,response,re.I):
            raise ServerError('Room entry not confirmed: '+response)
        self.room_id=room_id
        self.games.clear()
        self.emit('room',room_id=self.room_id)
        return response

    def refresh_games(self):
        previous=self.games
        self.games={}
        try: self.command('games')
        except Exception:
            self.games=previous;raise
        self._last_refresh=self.clock()
        # Do not assume games missing from room listing have finished.
        return self.games

    def sync_history(self,n):
        n=int(n);old=copy.deepcopy(self.positions.get(n,{}))
        if old.get('status')=='finished':
            self.needs_sync.discard(n);return
        self._history=n;self._history_moves={}
        try:
            self.command('moves '+str(n))
            staged=self._history_moves
            # Nonempty known games must not be replaced by a malformed/empty response.
            if not staged and old.get('moves'): raise ServerError('Empty history; keeping previous state')
            keys=sorted(staged)
            if keys and keys != list(range(0,keys[-1]+1)):
                raise ServerError('Incomplete history; keeping previous state')
            p=self.position(n);p['moves']=dict(staged);p['stale']=False
            if staged and p.get('status','live')=='live':
                p['to_play']='W' if staged[max(staged)]['color']=='B' else 'B'
                p['turn_at']=self.clock()
            self.needs_sync.discard(n)
            self.emit('synchronized',game_id=n,moves=len(staged))
        except Exception:
            current=self.positions.get(n,{})
            if old:
                # A failed history request must not undo an intervening result.
                if current.get('status')=='finished':
                    old.update({key:current[key] for key in ('status','result','result_text','to_play') if key in current})
                    old['stale']=False;self.needs_sync.discard(n)
                else:old['stale']=True
                self.positions[n]=old
            raise
        finally:self._history=None;self._history_moves={}

    def observe(self,n):
        n=int(n)
        if n not in self.wanted:
            self.positions.pop(n,None);self.needs_sync.discard(n)
            if self.context==n:self.context=None
        self.command('observe '+str(n))
        self.wanted.add(n)
        self.command('games '+str(n))
        self.sync_history(n)
        if self.position(n).get('status')!='finished':self.position(n)['status']='live'

    def unobserve(self,n):
        n=int(n)
        was_wanted=n in self.wanted
        self.wanted.discard(n)
        self.needs_sync.discard(n)
        if not was_wanted or self.position(n).get('status')=='finished' or self.status!='connected':return
        try:self.command('unobserve '+str(n))
        except ServerError:self.emit('unsubscribe_unavailable',game_id=n)

    @staticmethod
    def same_record(old,new,allow_rollback=False):
        if (old.get('white'),old.get('black'))!=(new.get('white'),new.get('black')):return False
        a,b=old.get('moves',{}),new.get('moves',{})
        overlap=set(a)&set(b)
        if a and not overlap:return False
        if not allow_rollback and len(b)<len(a):return False
        return all((a[k]['color'],a[k]['point'])==(b[k]['color'],b[k]['point']) for k in overlap)

    def recover(self, attempts=5):
        saved={n:copy.deepcopy(self.positions[n]) for n in self.wanted if n in self.positions}
        for p in self.positions.values():p['stale']=True
        self.status='reconnecting';self.emit('disconnected')
        for attempt in range(attempts):
            if self._stopped:return False
            if attempt:self.sleep(min(2**attempt,30))
            try:
                self.connect()
                if self.room_id:self.join(self.room_id)
                self.refresh_games()
                for old_id,old in saved.items():
                    candidates=[g for g in self.games.values() if (g['white'],g['black'])==(old.get('white'),old.get('black'))]
                    # A numeric ID is not a stable identity; never attach solely by ID.
                    if len(candidates)!=1:
                        self.position(old_id)['status']='unavailable'
                        self.emit('unavailable',game_id=old_id);continue
                    n=candidates[0]['id']
                    # Keep old record until verification has succeeded.
                    backup=copy.deepcopy(self.positions.get(n))
                    self.positions[n]={'moves':{},'status':'live','clocks':{}}
                    self.command('observe '+str(n));self.sync_history(n)
                    fresh=self.positions[n]
                    if not self.same_record(old,fresh,allow_rollback=True):
                        if backup is None:self.positions.pop(n,None)
                        else:self.positions[n]=backup
                        self.command('unobserve '+str(n));self.emit('identity_conflict',game_id=old_id,candidate_id=n)
                        self.position(old_id)['status']='identity_conflict'
                        self.wanted.discard(old_id)
                        continue
                    self.wanted.discard(old_id);self.wanted.add(n)
                    if old_id!=n:
                        self.positions[old_id]['status']='resumed'
                        self.positions[old_id]['resumed_as']=n
                    self.emit('recovered',game_id=n,previous_id=old_id)
                self.status='connected';return True
            except AuthenticationError:
                self.status='authentication_required';self.emit('authentication_required');return False
            except (OSError,TimeoutError,ServerError) as error:
                self.emit('retry',attempt=attempt+1,error=type(error).__name__)
        if self.sock:self.sock.close()
        self.closed=True;self.status='disconnected';self.emit('recovery_failed');return False

    def maintain(self):
        # Verify candidate resumptions using player identity AND matching history.
        if any(p.get('resume_candidate') for p in self.positions.values()):
            for p in self.positions.values():p.pop('resume_candidate',None)
            if not self.recover():raise ConnectionError('Resume synchronization failed')
        for n in list(self.needs_sync & self.wanted):
            try:self.sync_history(n)
            except ServerError:
                self.needs_sync.discard(n)
                self.position(n).update(stale=True,status='unavailable')
                self.emit('sync_unavailable',game_id=n)
        # Periodic complete histories repair missed events and undos; also probe liveness.
        if self.clock()-self._last_refresh>=30:
            self.refresh_games()
            for n in list(self.wanted):
                p=self.position(n)
                if p.get('status') in ('adjourned','unavailable') and any(
                    (g['white'],g['black'])==(p.get('white'),p.get('black')) for g in self.games.values()):
                    if not self.recover():raise ConnectionError('Resume synchronization failed')
                    return
            # Full histories are requested on subscribe, recovery, explicit undo or gaps.
            # Re-downloading every watched history on each heartbeat blocked UI actions.

    def poll(self,timeout=1):
        try:
            if self.closed or self.sock is None or self.sock.fileno() < 0:
                raise ConnectionError('Observation connection is closed')
            self.receive(timeout)
            self.maintain()
            return True
        except (OSError,TimeoutError): return self.recover()

    def clock_view(self,n,color):
        p=self.position(n);c=copy.deepcopy(p.get('clocks',{}).get(color))
        if c is None:return None
        running=c.get('running',p.get('to_play')==color)
        elapsed=max(0,self.clock()-max(c['received_at'],p.get('turn_at',c['received_at'])))
        live=self.status=='connected' and not p.get('stale') and p.get('status','live')=='live'
        c['estimated_seconds']=max(0,c['seconds']-elapsed) if running and live else max(0,c['seconds'])
        c['estimated']=bool(running and live);c['stale']=not live
        # Never invent rollover into the next byoyomi period; server updates are authoritative.
        return c

    def snapshot(self):
        return copy.deepcopy(dict(connection=self.status,room_id=self.room_id,games=self.games,positions=self.positions))

    def drain_events(self):
        events=list(self.events);self.events.clear();return events

    def close(self):
        self._stopped=True
        try:super().close()
        except OSError:
            if self.sock:self.sock.close()
        finally:self.status='disconnected'
