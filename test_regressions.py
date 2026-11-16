"""Regressions for local removal, room transitions and push updates."""
import copy,json,tempfile,threading,unittest,urllib.request
from http.server import ThreadingHTTPServer
from app import Studio,Handler,ServerError
from reliable import ObservationSession

class FakeSession:
    def __init__(self):
        self.status='connected';self.wanted=set();self.entered=threading.Event();self.release=threading.Event();self.calls=[]
    def unobserve(self,n):
        self.calls.append(n);self.entered.set();self.release.wait(3)
        raise ServerError('Game no longer exists')
    def snapshot(self):return dict(games={},positions={})
    def poll(self,timeout):self.release.wait(timeout);return True
    def drain_events(self):return []
    def close(self):self.status='disconnected'
    room_id=99
    rooms={}

class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Studio(self.temp.name)
    def tearDown(self):
        self.s.running=False
        if self.s.session and hasattr(self.s.session,'release'):self.s.session.release.set()
        with self.s.changed:self.s.changed.notify_all()
        self.s.thread.join(3);self.temp.cleanup()
    def test_remove_finished_game_before_network_reply(self):
        game=copy.deepcopy(self.s.snapshot()['watched'][0]);game.update(status='finished',result='B+R')
        self.s.selected={game['id']};self.s.set_state(demo=False,watched=[game])
        fake=FakeSession();self.s.session=fake
        self.s.dispatch('unobserve',{'id':game['id']})
        self.assertEqual(self.s.snapshot()['watched'],[])
        self.assertNotIn(game['id'],self.s.selected)
        self.assertTrue(fake.entered.wait(2))
        self.assertEqual(self.s.snapshot()['watched'],[])  # remote call is still blocked
        fake.release.set();self.s.tasks.join()
        self.assertEqual(self.s.snapshot()['watched'],[])  # denial must not restore it
    def test_remove_demo_and_profile_refresh_does_not_restore_it(self):
        n=self.s.snapshot()['watched'][0]['id'];self.s.dispatch('unobserve',{'id':n});self.s.tasks.join()
        self.s.save_player(dict(account='someone',name='Someone'))
        self.assertNotIn(n,[g['id'] for g in self.s.snapshot()['watched']])
    def test_transport_removal_of_finished_or_disappeared_game(self):
        session=ObservationSession();session.status='connected';session.wanted.add(45)
        session.positions[45]=dict(moves={},status='finished')
        session.command=lambda _:self.fail('Finished games must not need a remote command')
        session.unobserve(45);self.assertNotIn(45,session.wanted)
        session.wanted.add(46);session.positions[46]=dict(moves={},status='live')
        def denied(_):raise ServerError('Game does not exist')
        session.command=denied;session.unobserve(46)
        self.assertNotIn(46,session.wanted)
    def test_heartbeat_does_not_download_every_history(self):
        session=ObservationSession(clock=lambda:100);session._last_refresh=0;session.wanted={1,2,3}
        for n in session.wanted:session.position(n)
        calls=[]
        session.refresh_games=lambda:calls.append('games')
        session.sync_history=lambda _:self.fail('Heartbeat must not download all move histories')
        session.maintain();self.assertEqual(calls,['games'])
    def test_sse_delivers_changes_without_polling(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.studio=self.s
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def read_event(stream):
            parts=[]
            while True:
                line=stream.readline().decode()
                if line=='\n':return ''.join(parts)
                if not line:raise AssertionError('Stream closed unexpectedly')
                parts.append(line)
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/events',timeout=3) as stream:
                first=read_event(stream);self.assertIn('data: ',first)
                self.s.set_state(message='Push update received')
                second=read_event(stream);self.assertIn('Push update received',second)
                self.assertNotEqual(first.splitlines()[0],second.splitlines()[0])
        finally:
            self.s.running=False
            with self.s.changed:self.s.changed.notify_all()
            server.shutdown();server.server_close()
    def test_board_clock_age_is_not_reset_by_unrelated_status(self):
        import time
        game=self.s.snapshot()['watched'][0];game['clock_sampled_at']=time.monotonic()-8
        self.s.set_state(watched=[game]);self.s.set_state(pending='refresh')
        self.assertGreaterEqual(self.s.snapshot()['watched'][0]['clock_age'],8)

if __name__=='__main__':unittest.main()
