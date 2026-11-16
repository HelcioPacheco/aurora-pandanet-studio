import io,json,unittest
from unittest.mock import patch,MagicMock
import app
class LauncherTests(unittest.TestCase):
 def response(self,version):
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(dict(app='Aurora Pandanet Studio',version=version)).encode();return response
 def test_old_server_is_not_reused(self):
  server=MagicMock();server.server_port=8766;server.serve_forever.side_effect=KeyboardInterrupt
  with patch('sys.argv',['app.py','--open']),patch.object(app,'ThreadingHTTPServer',side_effect=[OSError('occupied'),server]) as make,patch('urllib.request.urlopen',return_value=self.response('0.1.4')),patch.object(app,'Studio'),patch.object(app.webbrowser,'open') as opened,patch('sys.stdout',new=io.StringIO()):
   app.main();self.assertEqual(make.call_args_list[1].args[0],('127.0.0.1',8766));opened.assert_called_once_with('http://127.0.0.1:8766')
 def test_same_version_is_reused(self):
  with patch('sys.argv',['app.py','--open']),patch.object(app,'ThreadingHTTPServer',side_effect=OSError('occupied')),patch('urllib.request.urlopen',return_value=self.response(app.APP_VERSION)),patch.object(app,'Studio') as studio,patch.object(app.webbrowser,'open') as opened,patch('sys.stdout',new=io.StringIO()):
   app.main();studio.assert_not_called();opened.assert_called_once_with('http://127.0.0.1:8765')
