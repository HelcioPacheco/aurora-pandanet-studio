import copy,tempfile,unittest
from types import SimpleNamespace
from app import Studio
from test_leagues import snapshot

class TeamGamesTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Studio(self.temp.name);self.s.running=False;self.s.thread.join(2)
  roster=snapshot();roster['teams'][0]['players'][0]['accounts']=['TestPlayer','Alias']
  roster['teams'].append(dict(code='EMPTY',name='Empty',country='',url='https://pandanet-igs.com/empty',players=[]))
  self.s.registry.import_snapshot(roster);self.s.choose_league(dict(league_id='latinamericanleague',season_id='1'))
  self.s.session=SimpleNamespace(status='connected')
  self.s.set_state(demo=False,room_id=7,watched=[],available=[dict(id=1,white='TESTPLAYER',black='Other'),dict(id=2,white='Other',black='alias'),dict(id=3,white='Other',black='Unrelated'),dict(id=4,white='TestPlayer',black='Alias')])
  self.args=dict(league_id='latinamericanleague',season_id='1',room_id=7,team_code='BRA')
 def tearDown(self):self.s.query_pool.shutdown(wait=True);self.temp.cleanup()
 def test_batch_matches_both_colors_and_deduplicates_in_flight_and_watched(self):
  self.s.selected={1};self.s.set_state(watched=[dict(id=1)])
  self.assertEqual(self.s.observe_team(self.args)['queued'],[2,4])
  self.assertEqual(self.s.observe_team(self.args)['queued'],[])
  self.assertFalse(self.s.dispatch('observe',dict(id=2))['accepted']);self.assertEqual(self.s.tasks.qsize(),2)
  self.assertEqual(self.s.snapshot()['opening_ids'],[2,4])
 def test_all_teams_cannot_open_a_batch(self):
  for code in ('','ALL','unknown'):
   with self.assertRaises(ValueError):self.s.observe_team(dict(self.args,team_code=code))
  self.assertTrue(self.s.tasks.empty())
 def test_empty_roster_never_matches_everything(self):self.assertEqual(self.s.observe_team(dict(self.args,team_code='EMPTY'))['queued'],[])
 def test_stale_league_season_and_room_are_rejected(self):
  for values in (dict(league_id='euroteamchamps'),dict(season_id='old'),dict(room_id=8)):
   with self.assertRaises(ValueError):self.s.observe_team(dict(self.args,**values))
 def test_disconnected_does_not_queue(self):
  self.s.session.status='disconnected'
  with self.assertRaises(ValueError):self.s.observe_team(self.args)
  self.assertTrue(self.s.tasks.empty())
 def test_matching_uses_selected_season_only(self):
  new=snapshot(sid='2',account='NewAccount');new['teams'][0]['players'][0]['source_id']='22';self.s.registry.import_snapshot(new);self.s.choose_league(dict(league_id='latinamericanleague',season_id='2'))
  self.assertEqual(self.s.observe_team(dict(self.args,season_id='2'))['queued'],[])

class RoomLeagueTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.s=Studio(self.temp.name);self.s.running=False;self.s.thread.join(2)
  self.s.session=SimpleNamespace(status='connected',room_id=1,rooms={1:dict(id=1,name='LatinAmericanTeamChamp'),2:dict(id=2,name='Humanlike bots'),3:dict(id=3,name='EuroTeamChamps')})
 def tearDown(self):self.s.query_pool.shutdown(wait=True);self.temp.cleanup()
 def test_all_leagues_are_identified_by_explicit_room_names(self):
  from league_sources import leagues_for_room
  for name,lid in [(' LatinAmericanTeamChamp ','latinamericanleague'),('europeanteamchamp','euroteamchamps'),('EuroTeamChamps','euroteamchamps'),('AGA City League','agacityleague'),('AGA City League(Manual)','agacityleague')]:
   self.assertEqual(leagues_for_room(name)[0]['id'],lid)
  for name in ('Humanlike bots','Sala principal','Other EuropeanTeamChamp',''):
   self.assertEqual(leagues_for_room(name),[])
 def test_room_switch_removes_league_context_and_restores_associated_league(self):
  self.s.associate_room();self.assertEqual(self.s.snapshot()['league_id'],'latinamericanleague')
  self.s.session.room_id=2;self.s.associate_room();self.assertIsNone(self.s.snapshot()['league_id']);self.assertIsNone(self.s.snapshot()['season_id']);self.assertEqual(self.s.league_directory()['teams'],[])
  with self.assertRaises(ValueError):self.s.choose_room_season(dict(league_id='latinamericanleague'))
  with self.assertRaises(ValueError):self.s.sync_league(dict(league_id='latinamericanleague'))
  with self.assertRaises(ValueError):self.s.observe_team(dict(team_code='BRA'))
  self.s.session.room_id=3;self.s.associate_room();self.assertEqual(self.s.snapshot()['room_league_ids'],['euroteamchamps','PYGETC'])
  self.s.choose_room_season(dict(league_id='PYGETC'));self.s.associate_room();self.assertEqual(self.s.snapshot()['league_id'],'PYGETC')
  with self.assertRaises(ValueError):self.s.choose_room_season(dict(league_id='latinamericanleague'))
 def test_no_room_association_has_no_implicit_league_profile(self):
  self.s.associate_room();self.s.session.room_id=2;self.s.associate_room()
  profile=self.s.player('HelcioAlex','1k',self.s.profiles(),'2026')
  self.assertEqual(profile['rank'],'1k');self.assertEqual(profile['country'],'')
