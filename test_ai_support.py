import io,socket,unittest
from unittest.mock import patch,MagicMock
from sgf import read_sgf
from photo_service import public_photo_url,PhotoCache
class AISupportTests(unittest.TestCase):
 def test_sgf_preserves_actual_komi_and_rules(self):
  g=read_sgf('(;GM[1]SZ[19]PB[A]PW[B]KM[0]RU[AGA];B[dd])')
  self.assertEqual(g['komi'],0);self.assertEqual(g['rules'],'AGA')
  self.assertIsNone(read_sgf('(;PB[A]PW[B])')['komi'])
  for value in ('NaN','inf','abc'):
   with self.assertRaises(ValueError):read_sgf('(;PB[A]PW[B]KM['+value+'])')
 def test_photo_rejects_private_and_non_https(self):
  for url in ('http://example.com/a.png','https://user:secret@example.com/a.png','https://example.com:444/a.png'):
   with self.assertRaises(ValueError):public_photo_url(url)
  with patch('photo_service.socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]):
   with self.assertRaises(ValueError):public_photo_url('https://example.com/a.png')
 def test_photo_magic_and_cache(self):
  response=MagicMock();response.url='https://example.com/a.png';response.read.return_value=b'\x89PNG\r\n\x1a\nimage';response.__enter__.return_value=response
  opener=MagicMock();opener.open.return_value=response
  with patch('photo_service.public_photo_url',side_effect=lambda u:u),patch('photo_service.build_opener',return_value=opener):
   c=PhotoCache();self.assertEqual(c.get(response.url)[0],'image/png');c.get(response.url);self.assertEqual(opener.open.call_count,1)
   response.read.return_value=b'<svg></svg>'
   with self.assertRaises(ValueError):c.get('https://example.com/b.svg')
   response.read.return_value=b'x'*2_000_001
   with self.assertRaises(ValueError):c.get('https://example.com/large.png')
