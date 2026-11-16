import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from app import Studio,Handler

class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.studio=Studio(cls.temp.name)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.server.studio=cls.studio
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.studio.running=False;cls.studio.thread.join(2);cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def request(self,path,data=None,headers=None):
        headers=headers or {}
        if data is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        return urllib.request.urlopen(req)
    def test_demo_state(self):
        with self.request('/api/state') as response:s=json.load(response)
        self.assertTrue(s['demo']);self.assertEqual(len(s['watched']),4)
        self.assertTrue(all(g['board'] for g in s['watched']))
        self.assertTrue(s['session_id'])
    def test_local_request_guard(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/demo',{})
        self.assertEqual(error.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/demo',{},dict(Origin='https://foreign.example',**{'X-Aurora':'studio'}))
        self.assertEqual(error.exception.code,403)
    def test_board_api(self):
        g=self.studio.snapshot()['watched'][0]
        with self.request('/api/board',dict(id=g['id'],ply=0,variation=[dict(color='B',point='D4')]),{'X-Aurora':'studio'}) as response:board=json.load(response)
        self.assertEqual(board['stones'],[[3,15,'B']])
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/board',dict(id=g['id'],ply=0,variation=[dict(color='B',point='D4'),dict(color='W',point='D4')]),{'X-Aurora':'studio'})
        self.assertEqual(error.exception.code,400)
    def test_persistent_profiles_and_fallback(self):
        session_id=self.studio.snapshot()['session_id']
        self.studio.save_player(dict(account='testAccount',name='Nome de teste',country='Brasil',rank='3 dan',photo=''))
        p=self.studio.player('TESTACCOUNT','1k',self.studio.profiles())
        self.assertEqual(self.studio.snapshot()['session_id'],session_id)
        self.assertEqual(p['name'],'Nome de teste');self.assertEqual(p['rank'],'3 dan');self.assertEqual(p['photo'],'')
        with self.assertRaises(ValueError):self.studio.save_player(dict(account='test',photo='javascript:bad'))
    def test_league_catalog_directory_and_selection_api(self):
        with self.request('/api/leagues') as response:catalog=json.load(response)['leagues']
        self.assertEqual(len(catalog),4)
        with self.assertRaises(urllib.error.HTTPError):self.request('/api/league',dict(league_id='euroteamchamps'),{'X-Aurora':'studio'})
        self.studio.choose_league(dict(league_id='euroteamchamps'))
        with self.request('/api/directory') as response:directory=json.load(response)
        self.assertEqual(directory['league_id'],'euroteamchamps');self.assertTrue(directory['teams'])
        with self.assertRaises(urllib.error.HTTPError):self.request('/api/league',dict(league_id='unknown'),{'X-Aurora':'studio'})
        self.studio.choose_league(dict(league_id='latinamericanleague'))
    def test_ai_isolation_headers_and_wasm(self):
        with self.request('/') as response:
            self.assertEqual(response.headers['Cross-Origin-Opener-Policy'],'same-origin')
            self.assertEqual(response.headers['Cross-Origin-Embedder-Policy'],'require-corp')
        with self.request('/vendor/katago/katago.wasm') as response:
            self.assertEqual(response.headers['Content-Type'],'application/wasm')
            self.assertGreater(int(response.headers['Content-Length']),1000000)
            self.assertEqual(response.read(4),b'\x00asm')

    def test_static_and_traversal(self):
        with self.request('/') as response:self.assertIn('Aurora',response.read().decode())
        with self.assertRaises(urllib.error.HTTPError):self.request('/../app.py')

if __name__=='__main__':unittest.main()
