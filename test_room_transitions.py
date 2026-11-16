import copy,tempfile,threading,unittest
from unittest.mock import patch
from app import Studio
from reliable import ObservationSession
from test_leagues import snapshot

class TransitionSession(ObservationSession):
 def __init__(self):
  super().__init__();self.status='connected';self.room_id=51;self.rooms={51:dict(id=51,name='LatinAmericanTeamChamp'),99:dict(id=99,name='Humanlike bots')}
  self.games={1:dict(id=1,white='oldWhite',black='oldBlack')};self.entered=threading.Event();self.release=threading.Event()
 def join(self,n):self.room_id=n;self.games={}
 def refresh_games(self):self.entered.set();self.release.wait(2);raise TimeoutError('Slow games query')
 def poll(self,timeout=.1):self.release.wait(timeout);return True
 def close(self):self.status='disconnected'

class RoomTransitionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Studio(self.temp.name);self.s.running=False;self.s.thread.join(2);self.session=TransitionSession();self.s.session=self.session;self.s.publish()
 def tearDown(self):
  self.session.release.set();self.s.running=False;self.s.thread.join(3);self.s.query_pool.shutdown(wait=True);self.temp.cleanup()
 def test_context_updates_never_mix_old_room_with_new_league_or_games(self):
  observed=[];original=self.s.set_state
  def capture(**values):original(**values);observed.append(self.s.snapshot())
  self.s.set_state=capture;self.session.room_id=99;self.session.games={2:dict(id=2,white='newWhite',black='newBlack')};self.s.publish()
  self.assertTrue(observed)
  for state in observed:
   self.assertEqual(state['room_id'],99);self.assertIsNone(state['league_id']);self.assertIsNone(state['season_id']);self.assertEqual(state['room_league_ids'],[]);self.assertEqual([g['id'] for g in state['available']],[2])
 def test_slow_or_failed_games_query_does_not_undo_confirmed_room_entry(self):
  self.s.running=True;self.s.thread=threading.Thread(target=self.s.worker,daemon=True);self.s.thread.start();self.s.dispatch('join',dict(room_id=99));self.assertTrue(self.session.entered.wait(2))
  pending=self.s.snapshot();self.assertEqual(pending['room_id'],99);self.assertEqual(pending['joining_room'],99);self.assertIsNone(pending['league_id']);self.assertEqual(pending['available'],[])
  self.session.release.set()
  with self.s.changed:self.assertTrue(self.s.changed.wait_for(lambda:self.s.state.get('joining_room') is None,timeout=2))
  final=self.s.snapshot();self.assertEqual(final['room_id'],99);self.assertIsNone(final['league_id']);self.assertIsNone(final['pending']);self.assertIn('demorou',final['message'])
 def test_late_roster_import_cannot_reactivate_league_after_leaving_its_room(self):
  entered=threading.Event();release=threading.Event()
  def delayed(*args):entered.set();release.wait(2);return snapshot(sid='200')
  try:
   with patch('app.import_league',delayed):
    self.s.sync_league(dict(league_id='latinamericanleague'));self.assertTrue(entered.wait(2));self.session.room_id=99;self.session.games={};self.s.publish();release.set()
    with self.s.changed:self.assertTrue(self.s.changed.wait_for(lambda:not self.s.state['league_sync']['busy'],timeout=2))
    final=self.s.snapshot();self.assertEqual(final['room_id'],99);self.assertIsNone(final['league_id']);self.assertIsNone(final['season_id']);self.assertEqual(final['room_league_ids'],[])
  finally:release.set()

 def test_return_to_main_room_zero_remains_after_every_publish(self):
  # Zero is a real destination, never a missing or fallback room selection.
  self.session.rooms[0]=dict(id=0,name='LatinAmericanTeamChamp')
  self.s.running=True;self.s.thread=threading.Thread(target=self.s.worker,daemon=True);self.s.thread.start();self.s.dispatch('join',dict(room_id=0));self.assertTrue(self.session.entered.wait(2))
  pending=self.s.snapshot();self.assertEqual(pending['room_id'],0);self.assertEqual(pending['joining_room'],0);self.assertIsNone(pending['league_id'])
  self.session.release.set()
  with self.s.changed:self.assertTrue(self.s.changed.wait_for(lambda:self.s.state.get('joining_room') is None,timeout=2))
  for _ in range(3):
   self.s.publish();current=self.s.snapshot();self.assertEqual(current['room_id'],0);self.assertIsNone(current['joining_room']);self.assertIsNone(current['league_id']);self.assertEqual(current['room_league_ids'],[]);self.assertEqual(current['room_capabilities'],dict(league=False,league_choice=False))
