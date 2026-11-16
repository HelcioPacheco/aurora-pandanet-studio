import json,tempfile,time,threading,unittest,copy
from pathlib import Path
from unittest.mock import patch
from app import Studio
from leagues import LeagueRegistry
from player_service import parse_archive,parse_public_profile,safe_url,ArchiveError,SocialClient
from sgf import read_sgf
from countries import country_code
from test_leagues import snapshot

class PlayerTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.studio=Studio(self.temp.name)
 def tearDown(self):self.studio.running=False;self.studio.thread.join(2);self.studio.query_pool.shutdown(wait=True);self.temp.cleanup()
 def test_rank_is_selected_by_game_year_with_exact_fallback(self):
  for sid,year,rank in [('100',2024,'3d'),('101',2025,'2d')]:
   d=snapshot(sid=sid,account='Historic',rank=rank);d['season_name']='Liga '+str(year);self.studio.registry.import_snapshot(d)
  self.studio.choose_league(dict(league_id='latinamericanleague',season_id='101'))
  self.assertEqual(self.studio.player('Historic','1d',self.studio.profiles(),'2024-07-01')['rank'],'3d')
  self.assertEqual(self.studio.player('Historic','1d',self.studio.profiles(),'2025-07-01')['rank'],'2d')
  p=self.studio.player('Historic','1d',self.studio.profiles(),'2023-07-01');self.assertEqual(p['rank'],'1d');self.assertEqual(p['rank_source'],'game');self.assertEqual(p['country'],'')
 def test_undated_record_uses_game_rank(self):
  p=self.studio.player('HelcioAlex','2d+',self.studio.profiles(),'')
  self.assertIsNone(p['year']);self.assertEqual(p['rank'],'2d+');self.assertEqual(p['rank_source'],'game')
 def test_edit_is_scoped_to_year_and_preserves_other_years(self):
  d=snapshot(sid='100',account='Historic',rank='3d');d['season_name']='Liga 2024';self.studio.registry.import_snapshot(d);self.studio.choose_league(dict(league_id='latinamericanleague',season_id='100'))
  self.studio.save_player(dict(account='Historic',year=2024,rank='2d',name='Editor',country='Brazil',photo=''))
  p=self.studio.player('Historic','1k',self.studio.profiles(),'2024');self.assertEqual(p['rank'],'2d');self.assertEqual(p['name'],'Editor');self.assertEqual(p['country_code'],'BR');self.assertEqual(p['rank_source'],'manual')
  self.assertEqual(self.studio.player('Historic','1k',self.studio.profiles(),'2023')['rank'],'1k')
 def test_unknown_country_has_no_default_flag(self):
  p=self.studio.player('NewAccount','3k',self.studio.profiles(),'2026');self.assertEqual(p['country'],'');self.assertEqual(p['country_code'],'');self.assertEqual(p['photo'],'')
  self.assertEqual(country_code('República Dominicana'),'DO');self.assertEqual(country_code('Other'),'')
 def test_slow_site_query_does_not_block_local_state_or_analysis(self):
  entered=threading.Event();release=threading.Event()
  def slow(*args):entered.set();release.wait(2);return dict(country='Japan')
  with patch.object(self.studio.social,'profile',side_effect=slow):
   token=self.studio.submit_query('profile',dict(account='Unknown',date='2026',rank='2d'))['job'];self.assertTrue(entered.wait(1));g=self.studio.snapshot()['watched'][0];self.assertEqual(self.studio.board_at(dict(id=g['id'],ply=0))['stones'],[]);self.assertFalse(self.studio.query_result(token)['done']);release.set()
   deadline=time.monotonic()+2
   while not self.studio.query_result(token)['done'] and time.monotonic()<deadline:time.sleep(.01)
   self.assertEqual(self.studio.query_result(token)['result']['player']['country_code'],'JP')
 def test_loaded_recording_removal_and_live_publication_keep_independent_membership(self):
  sgf='(;GM[1]SZ[9]PW[White]PB[Black]DT[2026-01-01]WR[2d]BR[1d];B[aa];W[bb])'
  with patch.object(self.studio.social,'sgf',return_value=read_sgf(sgf)):
   n=self.studio.load_archive('handle')['id'];self.assertEqual(self.studio.load_archive('handle')['id'],n);self.assertEqual(len(self.studio.board_at(dict(id=n,ply=1))['stones']),1)
   self.studio.dispatch('unobserve',dict(id=n));self.assertNotIn(n,self.studio.recordings);self.assertFalse(any(g['id']==n for g in self.studio.snapshot()['watched']))

class ParserTests(unittest.TestCase):
 def test_only_public_profile_fields_and_no_default_photo(self):
  raw='<table><tr><td>Country</td><td>Brazil</td><td>Visible to all</td></tr><tr><td>Real name</td><td>Private name</td><td>Not visible</td></tr><tr><td>Email</td><td>private@example.test</td></tr></table><img src="photo/150/16.jpg">'
  p=parse_public_profile(raw,'https://sns.pandanet.co.jp/prof_show.php',True);self.assertEqual(p,{'country':'Brazil'})
 def test_archive_parser_nested_tables_and_pagination(self):
  raw='''<table><tr><td><table><tr><td>O</td><td>2026/09/29 08:21</td><td>Opponent 3d+</td><td>HelcioAlex 2d+</td><td>19</td><td>-</td><td>6.5</td><td>Black won by resign</td><td><a href="https://my.pandanet.co.jp/cgi-bin/cgi.exe?MHkey=SECRET&amp;pg=DownLoadUGI&amp;mode=sgf">SGF</a></td><td>SNS</td></tr></table></td></tr></table><a href="javascript:ShowPage('2')">2</a><form name="theForm"><input name="key" value="SECRET"></form>'''
  records,pages,form=parse_archive(raw,'https://my.pandanet.co.jp/');self.assertEqual(len(records),1);self.assertEqual(records[0]['black']['account'],'HelcioAlex');self.assertEqual(pages,2);self.assertEqual(form['key'],'SECRET')
 def test_foreign_profile_selects_all_results_not_only_mutual_games(self):
  c=SocialClient();c.user='TestOwner'
  raw='<table><tr><td>Country</td><td>Japan</td></tr></table><a href="https://my.pandanet.co.jp/cgi-bin/cgi.exe?MHkey=DUMMY&amp;pg=SearchResult&amp;OppName=PublicTest">View your game results</a><a href="https://my.pandanet.co.jp/cgi-bin/cgi.exe?MHkey=DUMMY&amp;pg=SearchResult&amp;MyName=PublicTest">View all game results</a>'
  with patch.object(c,'request',return_value=(raw,'https://sns.pandanet.co.jp/myfriend.php?id=PublicTest')):
   self.assertEqual(c.profile('PublicTest')['country'],'Japan');self.assertIn('MyName=PublicTest',c.archive_targets['publictest']);self.assertNotIn('OppName=',c.archive_targets['publictest'])
 def test_logout_forgets_tokens_even_when_site_is_unavailable(self):
  c=SocialClient();c.user='TestOwner';c.handles={'temporary':('https://my.pandanet.co.jp/','TestOwner')}
  with patch.object(c,'request',side_effect=ArchiveError('Offline')):self.assertFalse(c.logout()['connected'])
  self.assertEqual(c.user,'');self.assertEqual(c.handles,{})
 def test_historical_discovery_ignores_current_season_sidebar(self):
  from league_sources import seasons_for_year,LEAGUES
  index='<a href="/communities/latinamericanleague/seasons/OLD">Championship 2025</a>'
  page='<div id="container-main-content"><a href="/communities/latinamericanleague/teams/43/BRA">Brazil</a></div>'+('<a href="/communities/latinamericanleague/teams/48/BRA">Brazil</a>'*10)
  with patch('league_sources.fetch',side_effect=[(index,'index'),(page,'season')]):self.assertEqual(seasons_for_year(LEAGUES[0],2025),[('43','Championship 2025')])
 def test_official_origin_guard(self):
  for url in ['http://sns.pandanet.co.jp/','https://evil.test/','https://sns.pandanet.co.jp.evil.test/','https://u@sns.pandanet.co.jp/']:
   with self.assertRaises(ArchiveError):safe_url(url)
 def test_sgf_escapes_mainline_pass_and_setup(self):
  g=read_sgf(r'(;GM[1]SZ[9]PW[W]PB[B]DT[2025]C[escaped \] ;B[zz\] ( text]AB[aa]PL[W];W[bb];B[](;W[cc])(;W[dd]))');self.assertEqual(len(g['moves']),3);self.assertEqual(g['moves'][1]['point'],'PASS');self.assertEqual(len(g['board']['stones']),3)
  for bad in ['(;GM[2]PW[W]PB[B])','(;PW[W]PB[B];B[zz])','(;PW[W]PB[B];B[aa];W[aa])','(;PW[W]PB[B];B[aa]']:
   with self.assertRaises(ValueError):read_sgf(bad)
 def test_all_locale_packs_have_native_names_and_identical_keys(self):
  folder=Path(__file__).parent/'static'/'locales';catalog=json.loads((folder/'catalog.json').read_text());self.assertEqual(len(catalog),48);keys=None
  for row in catalog:
   pack=json.loads((folder/(row['code']+'.json')).read_text());self.assertTrue(pack['name']);self.assertTrue(all(pack['messages'].values()))
   if keys is None:keys=set(pack['messages'])
   self.assertEqual(keys,set(pack['messages']))
  self.assertEqual(json.loads((folder/'ja.json').read_text())['messages']['liberties'],'連の呼吸点')
