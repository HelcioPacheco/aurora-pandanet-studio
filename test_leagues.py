import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from leagues import LeagueRegistry
from league_sources import LEAGUES,parse_team,discover,team_links
from app import Studio

def snapshot(lid='latinamericanleague',sid='1',name='Nome oficial',account='TestPlayer',rank='3 dan'):
 return dict(league_id=lid,season_id=sid,season_name='Temporada '+sid,source_url='https://pandanet-igs.com/communities/'+lid+'/teams/'+sid,imported_at='2026-10-18T12:00:00+00:00',warnings=[],teams=[dict(code='BRA',name='Brazil',country='Brasil',url='https://pandanet-igs.com/team',players=[dict(source_id='11',name=name,accounts=[account],rank=rank,photo='',source_url='https://pandanet-igs.com/team#11',account_raw=account,order=1,captain=True)])])
class RegistryTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.registry=LeagueRegistry(Path(self.temp.name)/'test.sqlite3')
 def tearDown(self):self.temp.cleanup()
 def test_case_insensitive_identity_and_contextual_rank(self):
  self.registry.import_snapshot(snapshot());self.registry.import_snapshot(snapshot('euroteamchamps',account='testplayer',rank='4 dan'))
  self.assertEqual(self.registry.directory()['total_people'],1)
  self.assertEqual(self.registry.profile_map('latinamericanleague','1')['testplayer']['rank'],'3 dan')
  self.assertEqual(self.registry.profile_map('euroteamchamps','1')['testplayer']['rank'],'4 dan')
 def test_same_name_does_not_merge_different_accounts(self):
  self.registry.import_snapshot(snapshot());self.registry.import_snapshot(snapshot('euroteamchamps',account='DifferentAccount'))
  self.assertEqual(self.registry.directory()['total_people'],2)
 def test_seasons_persist_and_empty_teams_are_retained(self):
  first=snapshot();first['teams'].append(dict(code='EMPTY',name='Empty',country='',url='https://pandanet-igs.com/empty',players=[]));self.registry.import_snapshot(first)
  self.registry.import_snapshot(snapshot(sid='2',rank='5 dan'));self.registry.configure('latinamericanleague','1')
  self.assertEqual(LeagueRegistry(self.registry.path).selected(),('latinamericanleague','1'))
  self.assertEqual(len(self.registry.directory()['teams']),2);self.assertEqual(self.registry.catalog()[0]['teams'],2)
 def test_failed_import_rolls_back(self):
  self.registry.import_snapshot(snapshot());self.registry.import_snapshot(snapshot('euroteamchamps',account='Another'))
  conflicting=snapshot(account='Another',name='Conflito')
  with self.assertRaises(ValueError):self.registry.import_snapshot(conflicting)
  self.assertEqual(self.registry.profile_map('latinamericanleague','1')['testplayer']['name'],'Nome oficial')
 def test_seed_does_not_replace_user_refresh(self):
  seed=Path(self.temp.name)/'seed';seed.mkdir();(seed/'league.json').write_text(json.dumps(snapshot()))
  self.registry.load_seed(seed);self.registry.import_snapshot(snapshot(name='Atualizado'));self.registry.load_seed(seed)
  self.assertEqual(self.registry.profile_map('latinamericanleague','1')['testplayer']['name'],'Atualizado')
 def test_captain_and_player_are_one_membership(self):
  data=snapshot();captain=data['teams'][0]['players'][0];captain['order']=0;captain['rank']='';captain['photo']='';player=copy.deepcopy(captain);player.update(order=1,rank='3 dan',photo='https://pandanet-igs.com/photo.jpg',captain=False);data['teams'][0]['players'].append(player)
  self.registry.import_snapshot(data);players=self.registry.directory('latinamericanleague','1')['teams'][0]['players'];self.assertEqual(len(players),1);self.assertTrue(players[0]['captain']);self.assertEqual(players[0]['rank'],'3 dan');self.assertEqual(players[0]['position'],1)
 def test_existing_editorial_database_is_backed_up(self):
  import sqlite3
  path=Path(self.temp.name)/'legacy.sqlite3'
  with sqlite3.connect(path) as db:db.execute('CREATE TABLE players(account TEXT PRIMARY KEY,name TEXT,country TEXT,rank TEXT,photo TEXT)');db.execute('INSERT INTO players VALUES(?,?,?,?,?)',('mine','Nome','Brasil','3d',''))
  LeagueRegistry(path);backup=path.with_name('players.before-leagues.sqlite3');self.assertTrue(backup.exists())
  with sqlite3.connect(backup) as db:self.assertEqual(db.execute('SELECT name FROM players').fetchone()[0],'Nome')
 def test_invalid_selection_and_empty_import(self):
  with self.assertRaises(ValueError):self.registry.configure('unknown')
  with self.assertRaises(ValueError):self.registry.import_snapshot(dict(snapshot(),teams=[]))
 def test_manual_profiles_override_import_without_being_overwritten(self):
  studio=Studio(self.temp.name)
  try:
   studio.registry.import_snapshot(snapshot(account='Counter'));studio.choose_league(dict(league_id='latinamericanleague',season_id='1'))
   g=next(g for g in studio.snapshot()['watched'] if g['black']=='Counter' or g['white']=='Counter');p=g['black_player'] if g['black']=='Counter' else g['white_player'];self.assertEqual(p['name'],'Nome oficial')
   studio.save_player(dict(account='Counter',name='Nome escolhido',rank='7 dan',country='Brasil',photo=''))
   studio.registry.import_snapshot(snapshot(account='Counter',name='Nome novo na fonte',rank='5 dan'));studio.refresh_profiles()
   self.assertEqual(studio.player('COUNTER','1k',studio.profiles())['name'],'Nome escolhido')
   self.assertEqual(studio.player('COUNTER','1k',studio.profiles())['rank'],'7 dan')
  finally:studio.running=False;studio.thread.join(2)
class SyncTests(unittest.TestCase):
 def test_network_import_does_not_block_local_analysis_and_failure_keeps_data(self):
  import threading,time
  started=threading.Event();release=threading.Event()
  with tempfile.TemporaryDirectory() as folder:
   studio=Studio(folder)
   def failing_fetch(league,progress):
    started.set();release.wait(3);raise ValueError('Fonte temporariamente indisponível')
   try:
    studio.choose_league(dict(league_id='latinamericanleague'))
    before=studio.registry.directory()['total_people']
    with patch('app.import_league',failing_fetch):
     studio.sync_league(dict(league_id='latinamericanleague'));self.assertTrue(started.wait(1))
     game=studio.snapshot()['watched'][0];self.assertEqual(studio.board_at(dict(id=game['id'],ply=0))['stones'],[])
     self.assertTrue(studio.snapshot()['league_sync']['busy']);release.set()
     deadline=time.monotonic()+3
     while studio.snapshot()['league_sync']['busy'] and time.monotonic()<deadline:time.sleep(.01)
     self.assertTrue(studio.snapshot()['league_sync']['error']);self.assertEqual(studio.registry.directory()['total_people'],before)
   finally:release.set();studio.running=False;studio.thread.join(2)
class SourceTests(unittest.TestCase):
 def test_parser_only_imports_requested_fields_and_resolves_photos(self):
  raw='''<div id="container-main-content"><h1>Brazil</h1><div class="player_profile"><img src="/photo.jpg"><h4><a name="123">1: Test Name</a><b>(Captain)</b></h4><ul><li><b>Pandanet account:</b> AccountOne</li><li><b>Rank:</b> 3 dan</li><li><b>Email:</b> private@example.test</li></ul></div></div>'''
  t=parse_team(raw,dict(code='BRA',name='Brazil',url='https://pandanet-igs.com/team'),LEAGUES[0]);p=t['players'][0]
  self.assertTrue(p['captain']);self.assertEqual(p['accounts'],['AccountOne']);self.assertEqual(p['photo'],'https://pandanet-igs.com/photo.jpg');self.assertNotIn('email',p)
 def test_current_page_season_detection_and_deduplicated_teams(self):
  raw='<h2 class="current-season-right-panel-title">Current season</h2><a href="/communities/latinamericanleague/teams/48/BRA">Brazil</a>'*2
  self.assertEqual(discover(raw,LEAGUES[0]),('48','Current season'));self.assertEqual(len(team_links(raw,LEAGUES[0],'48')),1)
 def test_official_empty_team_is_explicit_but_error_page_is_rejected(self):
  team=dict(code='T2',name='Toronto 2',url='https://pandanet-igs.com/team')
  parsed=parse_team('<div id="container-main-content"><h1>Toronto 2</h1></div>',team,LEAGUES[-1]);self.assertEqual(parsed['players'],[]);self.assertTrue(parsed['warnings'])
  with self.assertRaises(ValueError):parse_team('<h1>Error</h1>',team,LEAGUES[-1])
