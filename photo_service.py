"""Bounded, credential-free public photo cache for isolated browser pages."""
import ipaddress,socket,threading,time
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler

def public_photo_url(url):
 p=urlparse(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Foto HTTPS inválida.')
 addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):raise ValueError('Endereço de foto não público.')
 return url
class PublicRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  public_photo_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)
class PhotoCache:
 def __init__(self):self.cache={};self.lock=threading.Lock()
 def get(self,url):
  with self.lock:
   hit=self.cache.get(url)
   if hit and time.monotonic()-hit[0]<3600:return hit[1:]
  public_photo_url(url)
  req=Request(url,headers={'User-Agent':'Aurora-Pandanet-Studio/1.0','Accept':'image/png,image/jpeg,image/webp,image/gif'})
  with build_opener(PublicRedirect()).open(req,timeout=6) as response:
   public_photo_url(response.url);data=response.read(2_000_001)
  if len(data)>2_000_000:raise ValueError('Foto muito grande.')
  kind='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else 'image/gif' if data.startswith((b'GIF87a',b'GIF89a')) else 'image/webp' if data[:4]==b'RIFF' and data[8:12]==b'WEBP' else None
  if not kind:raise ValueError('Formato de foto não suportado.')
  with self.lock:
   if len(self.cache)>=128:self.cache.pop(next(iter(self.cache)))
   self.cache[url]=(time.monotonic(),kind,data)
  return kind,data
