"""Read-only IGS/Pandanet transport prototype. Python 3.10+, no dependencies."""
import argparse
import json
import re
import select
import socket
import time
from pathlib import Path

GAME = re.compile(r'7 \[\s*(\d+)\]\s+(\S+)\s+\[([^]]+)\]\s+vs\.\s+(\S+)\s+\[([^]]+)\]\s+\(\s*(\d+)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s+(\d+)\s+(\S+)\)\s+\(\s*(\d+)\)')

class Pandanet:
    def __init__(self, host='igs.joyjoy.net', port=7777):
        self.host, self.port = host, port
        self.sock = None
        self.buffer = b''
        self.rooms, self.games, self.positions = {}, {}, {}
        self.events = []
        self.context = None
        self.closed = False
        self.transcript = []
        self.telnet_state = 'data'
        self.telnet_command = None

    def clean_telnet(self, data):
        out = bytearray()
        for byte in data:
            state = self.telnet_state
            if state == 'data':
                if byte == 255: self.telnet_state = 'iac'
                else: out.append(byte)
            elif state == 'iac':
                if byte == 255:
                    out.append(byte); self.telnet_state = 'data'
                elif byte in (251, 252, 253, 254):
                    self.telnet_command = byte; self.telnet_state = 'option'
                elif byte == 250: self.telnet_state = 'sub'
                else: self.telnet_state = 'data'
            elif state == 'option':
                if self.telnet_command in (251, 253):
                    self.sock.sendall(bytes([255, 254 if self.telnet_command == 251 else 252, byte]))
                self.telnet_state = 'data'
            elif state == 'sub':
                if byte == 255: self.telnet_state = 'sub_iac'
            elif state == 'sub_iac':
                self.telnet_state = 'data' if byte == 240 else 'sub'
        return bytes(out)

    def receive(self, timeout=1):
        if self.closed: return ''
        ready, _, _ = select.select([self.sock], [], [], timeout)
        if not ready: return ''
        data = self.sock.recv(65536)
        if not data:
            self.closed = True
            raise ConnectionError('Pandanet closed the connection')
        data = self.clean_telnet(data)
        text = data.decode('cp932', errors='replace')
        self.transcript.append({'direction':'in', 'text':text})
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            self.parse(line.decode('cp932', errors='replace').strip())
        return text

    def parse(self, line):
        self.events.append({'type':'raw', 'line':line})
        room = re.match(r'9 ROOM (\d+): ([^;]+);([^;]*);', line)
        if room:
            n, name, flags = room.groups()
            self.rooms[int(n)] = {'id':int(n), 'name':name, 'flags':flags}
        game = GAME.match(line)
        if game:
            g = game.groups(); n = int(g[0])
            self.games[n] = dict(id=n, white=g[1], white_rank=g[2].strip(), black=g[3], black_rank=g[4].strip(), move_count=int(g[5]), size=int(g[6]), handicap=int(g[7]), komi=float(g[8]), observers=int(g[11]))
        header = re.match(r'15 Game (\d+)\s+[^:]+:\s+(\S+)\s+\(([^)]+)\)\s+vs\s+(\S+)\s+\(([^)]+)\)', line)
        if header:
            n, white, wc, black, bc = header.groups(); self.context = int(n)
            pos = self.positions.setdefault(int(n), {'moves':{}})
            pos.update(white=white, black=black, white_clock=wc.split(), black_clock=bc.split())
        move = re.match(r'15\s+(\d+)\(([BW])\):\s*(\S+)', line)
        if move and self.context is not None:
            number, color, point = move.groups()
            self.positions.setdefault(self.context, {'moves':{}})['moves'][int(number)] = {'color':color, 'point':point}
            self.events.append({'type':'move', 'game_id':self.context, 'number':int(number), 'color':color, 'point':point})
        clock = re.match(r'15 TIME:\s*(\d+):', line)
        if clock:
            self.positions.setdefault(int(clock[1]), {'moves':{}})['time_message'] = line

    def send(self, command):
        # Intentionally restrict this prototype to observation commands.
        if not re.fullmatch(r'(guest|quit|room|games(?: \d+)?|join \d+|observe \d+|unobserve \d+|moves \d+|all \d+|toggle client true)', command):
            raise ValueError('Command not permitted by observation prototype')
        self.transcript.append({'direction':'out', 'text':command})
        self.sock.sendall((command+'\r\n').encode('ascii'))

    def wait_for(self, pattern, timeout=15):
        end = time.monotonic()+timeout; received = ''
        while time.monotonic()<end:
            received += self.receive(min(1, end-time.monotonic()))
            if re.search(pattern, received): return received
        raise TimeoutError('Expected server response did not arrive: '+pattern)

    def command(self, command):
        self.send(command)
        return self.wait_for(r'(?:^|\n)1 \d+\r?\n')

    def connect(self, username=None, password=None):
        self.sock = socket.create_connection((self.host, self.port), 10)
        self.wait_for(r'Login:')
        if username is None:
            self.send('guest')
            self.wait_for(r'#>')
        else:
            if not re.fullmatch(r'[A-Za-z0-9_-]+', username):
                raise ValueError('Invalid account name')
            if password is None or '\r' in password or '\n' in password:
                raise ValueError('Password required')
            self.sock.sendall((username+'\r\n').encode('ascii'))
            self.wait_for(r'Password:|1 1')
            self.sock.sendall((password+'\r\n').encode('ascii'))
            self.wait_for(r'#>|(?:^|\n)1 \d+\r?\n')
        self.command('toggle client true')
        self.buffer = b''

    def observe(self, game_id):
        responses = []
        for command in (f'observe {game_id}', f'games {game_id}', f'moves {game_id}'):
            responses.append(self.command(command))
        return responses

    def close(self):
        if self.sock:
            try:
                if not self.closed: self.send('quit')
            finally: self.sock.close(); self.closed = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=30)
    parser.add_argument('--output', default='session.json')
    args = parser.parse_args()
    client = Pandanet()
    report = {'checks':{}, 'limitations':['Observation transport only; no board reconstruction, reconnect, or full result/undo handling yet.']}
    try:
        client.connect(); report['checks']['guest_login'] = True
        client.command('room'); report['rooms'] = list(client.rooms.values())
        league = next(r for r in client.rooms.values() if r['name']=='LatinAmericanTeamChamp')
        report['league_join_response'] = client.command(f"join {league['id']}")
        report['league_games_response'] = client.command('games')
        report['checks']['league_join_confirmed'] = 'joined' in report['league_join_response'].lower()
        client.command('join 0'); client.games.clear(); client.command('games')
        report['main_room_games'] = list(client.games.values())
        selected = sorted(client.games.values(), key=lambda g:g['observers'], reverse=True)[:2]
        for game in selected: client.observe(game['id'])
        report['observed_ids'] = [g['id'] for g in selected]
        report['initial_move_counts'] = {n:len(p['moves']) for n,p in client.positions.items()}
        baseline = len(client.events); end = time.monotonic()+args.seconds
        while time.monotonic()<end: client.receive(min(1, end-time.monotonic()))
        report['live_moves'] = [e for e in client.events[baseline:] if e['type']=='move']
        report['positions'] = client.positions
        report['checks']['two_histories_received'] = all(client.positions.get(g['id'],{}).get('moves') for g in selected) and len(selected)==2
        for game in selected: client.command(f"unobserve {game['id']}")
    finally:
        client.close()
        report['transcript'] = client.transcript
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in report.items() if k in ('checks','observed_ids','initial_move_counts','live_moves')}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
