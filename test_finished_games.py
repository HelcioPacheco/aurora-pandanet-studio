"""Post-game updates must never replace a broadcast with an illegal position."""
import copy,tempfile,unittest
from app import Studio
from reliable import ObservationSession


def header(session,n=1,white='white',black='black'):
 session.parse(f'15 Game {n} I: {white} (0 200 -1) vs {black} (0 300 -1)')
def moves(session,points=('D4','Q16','D16','Q4')):
 for i,point in enumerate(points):session.parse(f'15 {i}({"B" if i%2==0 else "W"}): {point}')
def finish(session):session.parse('21 {Game 1: white vs black : Black lost by Resign}')

class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.s=ObservationSession();self.s.status='connected';self.s.wanted.add(1);header(self.s);moves(self.s)
 def test_completed_record_ignores_late_moves_headers_timers_and_undo(self):
  finish(self.s);before=copy.deepcopy(self.s.positions[1])
  for line in ['15 4(B): D4','15 Game 1 I: newwhite (0 99 -1) vs newblack (0 99 -1)','15 0(B): Q16','15 TIME:1:newwhite(W): 1 0/60 479/600 14/25','28 Undo in game 1: white vs black: Q4','21 {Game 1: newwhite vs newblack : White lost by Resign}']:
   self.s.parse(line)
  self.assertEqual(self.s.positions[1],before);self.assertNotIn(1,self.s.wanted);self.assertNotIn(1,self.s.needs_sync)
 def test_duplicate_earlier_move_does_not_truncate_history_or_restart_clock(self):
  before=copy.deepcopy(self.s.positions[1]);self.s.drain_events();self.s.parse('15 0(B): D4')
  self.assertEqual(self.s.positions[1],before);self.assertFalse(any(e['type']=='move' for e in self.s.drain_events()))
 def test_active_id_reuse_preserves_original_players_and_moves(self):
  before=copy.deepcopy(self.s.positions[1]['moves']);header(self.s,white='newwhite',black='newblack');self.s.parse('15 0(B): Q16')
  self.assertEqual(self.s.positions[1]['moves'],before);self.assertEqual(self.s.positions[1]['white'],'white');self.assertEqual(self.s.positions[1]['status'],'identity_conflict');self.assertNotIn(1,self.s.wanted)
 def test_resignation_control_is_not_a_stone(self):
  before=copy.deepcopy(self.s.positions[1]['moves']);self.s.parse('15 4(B): Resign')
  self.assertEqual(self.s.positions[1]['moves'],before);self.assertEqual(self.s.positions[1]['result'],'W+R');self.assertEqual(self.s.positions[1]['status'],'finished')
 def test_history_is_staged_and_preserves_finish_arriving_during_sync(self):
  before=copy.deepcopy(self.s.positions[1]['moves'])
  def reply(command):
   header(self.s);self.s.parse('15 0(B): Q4');self.assertEqual(self.s.positions[1]['moves'],before)
   self.s.parse('15 1(W): D16');finish(self.s);self.s.parse('15 2(B): D4')
  self.s.command=reply;self.s.sync_history(1)
  self.assertEqual(self.s.positions[1]['moves'][0]['point'],'Q4');self.assertEqual(len(self.s.positions[1]['moves']),3);self.assertEqual(self.s.positions[1]['status'],'finished');self.assertEqual(self.s.positions[1]['result'],'W+R')
 def test_staged_history_restores_live_turn_without_restarting_a_finished_clock(self):
  def reply(command):header(self.s);moves(self.s,('D4','Q16','D16'))
  self.s.command=reply;self.s.sync_history(1)
  self.assertEqual(self.s.positions[1]['to_play'],'W');self.assertTrue(self.s.clock_view(1,'W')['estimated'])
 def test_finished_history_is_never_downloaded_again(self):
  finish(self.s);self.s.command=lambda _:self.fail('Finished history must remain frozen');self.s.sync_history(1)
 def test_failed_history_request_cannot_undo_an_intervening_result(self):
  before=copy.deepcopy(self.s.positions[1]['moves'])
  def reply(command):
   finish(self.s);raise TimeoutError('History request interrupted')
  self.s.command=reply
  with self.assertRaises(TimeoutError):self.s.sync_history(1)
  self.assertEqual(self.s.positions[1]['status'],'finished');self.assertEqual(self.s.positions[1]['result'],'W+R');self.assertEqual(self.s.positions[1]['moves'],before);self.assertFalse(self.s.positions[1]['stale']);self.assertNotIn(1,self.s.needs_sync)
 def test_explicit_reobserve_after_removal_uses_fresh_history(self):
  finish(self.s)
  def reply(command):
   if command.startswith('observe'):header(self.s,white='newwhite',black='newblack')
   if command.startswith('moves'):moves(self.s,('Q4','D16'))
  self.s.command=reply;self.s.observe(1)
  self.assertEqual(self.s.positions[1]['white'],'newwhite');self.assertEqual(self.s.positions[1]['status'],'live');self.assertEqual(len(self.s.positions[1]['moves']),2)

class BroadcastPositionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.studio=Studio(self.temp.name);self.studio.running=False;self.studio.thread.join(2)
  self.s=ObservationSession();self.s.status='connected';self.s.wanted={1};header(self.s)
  self.s.games[1]=dict(id=1,white='white',black='black',white_rank='2d',black_rank='3d',size=19,handicap=0)
  self.studio.session=self.s;self.studio.selected={1}
 def tearDown(self):self.studio.query_pool.shutdown(wait=True);self.temp.cleanup()
 def published(self):self.studio.publish();return self.studio.snapshot()['watched'][0]
 def test_invalid_update_keeps_board_and_history_together_then_recovers(self):
  moves(self.s,('D4','Q16'));before=self.published();self.s.parse('15 2(B): D4');safe=self.published()
  self.assertEqual(safe['board'],before['board']);self.assertEqual(safe['moves'],before['moves']);self.assertNotIn('board_error',safe);self.assertTrue(safe['stale']);self.assertIn(1,self.s.needs_sync)
  def reply(command):header(self.s);moves(self.s,('D4','Q16','D16'))
  self.s.command=reply;self.s.sync_history(1);fresh=self.published();self.assertEqual(len(fresh['moves']),3);self.assertEqual(len(fresh['board']['stones']),3);self.assertFalse(fresh['stale']);self.assertNotIn('sync_pending',fresh)
 def test_first_invalid_history_exposes_only_its_legal_prefix(self):
  moves(self.s,('D4','D4','Q16'));safe=self.published();self.assertEqual(len(safe['moves']),1);self.assertEqual(safe['board']['ply'],1);self.assertEqual(len(safe['board']['stones']),1);self.assertNotIn('board_error',safe)
 def test_finish_with_bad_tail_keeps_last_valid_position_and_result(self):
  moves(self.s,('D4','Q16'));before=self.published();self.s.parse('15 2(B): D4');finish(self.s);safe=self.published()
  self.assertEqual(safe['board'],before['board']);self.assertEqual(safe['moves'],before['moves']);self.assertEqual(safe['status'],'finished');self.assertEqual(safe['result'],'W+R');self.assertNotIn(1,self.s.needs_sync);self.assertFalse(safe['stale'])
 def test_reused_listing_does_not_replace_finished_metadata(self):
  moves(self.s);before=self.published();finish(self.s)
  self.s.games[1]=dict(id=1,white='newwhite',black='newblack',white_rank='9d',black_rank='8d',size=9,handicap=2)
  header(self.s,white='newwhite',black='newblack');moves(self.s,('D4','D4'));safe=self.published()
  self.assertEqual(safe['size'],19);self.assertEqual(safe['white_player']['rank'],'2d');self.assertEqual(safe['black'],'black');self.assertEqual(safe['board'],before['board']);self.assertEqual(safe['status'],'finished')
