"""Read-only HTTPS access to Net Social Plaza, isolated from the live IGS worker.
Cookies, session URLs and archive handles live only in memory and never reach UI.
"""
import re,time,secrets,threading,http.cookiejar
from urllib.request import build_opener,HTTPCookieProcessor,HTTPRedirectHandler,Request
from urllib.parse import urlparse,urljoin,urlencode,parse_qs
from league_sources import Tree,Node

class ArchiveError(ValueError):pass

def account_name(value):
 value=str(value).strip()
 if not re.fullmatch(r'[A-Za-z0-9_-]{1,50}',value):raise ArchiveError('Conta Pandanet inválida.')
 return value

def safe_url(value,base='https://sns.pandanet.co.jp/'):
 value=urljoin(base,value);p=urlparse(value)
 if p.scheme!='https' or p.hostname not in ('sns.pandanet.co.jp','my.pandanet.co.jp') or p.port not in (None,443) or p.username:raise ArchiveError('Endereço fora do serviço oficial.')
 return value
class OfficialRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  safe_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def cells(row):return [n for n in row.children if isinstance(n,Node) and n.tag in ('td','th')]

def parse_public_profile(raw,base,own=False):
 tree=Tree(raw).root;result={}
 for row in tree.find('tr'):
  cs=cells(row)
  if len(cs)<2:continue
  label=cs[0].text().strip(':： ').casefold();value=cs[1].text()
  # An account owner can see private fields; never import those into a transmission.
  if own and 'Visible to all' not in row.text():continue
  if label=='country' and value and value not in ('Other','Not visible'):result['country']=value.replace('Visible to all','').strip()
  if label in ('real name','name') and value and value!='Not visible':result['name']=value.replace('Visible to all','').strip()
 for img in tree.find('img'):
  src=img.attrs.get('src','')
  if re.search(r'(?:^|/)photo/150/',src) and not re.search(r'/(?:no_?image|default|16)\.',src,re.I):
   try:result['photo']=safe_url(src,base)
   except ArchiveError:pass
   break
 return result

def parse_archive(raw,base):
 tree=Tree(raw).root;records=[]
 for row in tree.find('tr'):
  cs=cells(row)
  if len(cs)!=10:continue
  links=[a for a in cs[8].find('a') if a.text()=='SGF']
  if len(links)!=1:continue
  vals=[c.text() for c in cs]
  if not re.match(r'\d{4}/\d{2}/\d{2}',vals[1]):continue
  def player(text):
   m=re.fullmatch(r'(\S+)\s+(.+)',text)
   return dict(account=m.group(1),rank=m.group(2)) if m else dict(account=text,rank='')
  records.append(dict(date=vals[1],white=player(vals[2]),black=player(vals[3]),size=vals[4],handicap=vals[5],komi=vals[6],result=vals[7],_url=safe_url(links[0].attrs['href'],base)))
 pages=[int(m.group(1)) for a in tree.find('a') for m in [re.search(r"ShowPage\(\s*['\"]?(\d+)",a.attrs.get('href',''),re.I)] if m]
 forms=[f for f in tree.find('form') if f.attrs.get('name')=='theForm']
 form={i.attrs.get('name'):i.attrs.get('value','') for i in forms[0].find('input')} if forms else {}
 return records,max(pages or [1]),form

class SocialClient:
 def __init__(self,credentials=lambda:None):
  self.credentials=credentials;self.lock=threading.RLock();self.reset()
 def reset(self):
  with self.lock:
   self.jar=http.cookiejar.CookieJar();self.opener=build_opener(OfficialRedirect(),HTTPCookieProcessor(self.jar));self.user='';self.home='';self.archive_url='';self.profile_cache={};self.archive_targets={};self.handles={};self.page_forms={};self.cache={}
 def request(self,url,data=None):
  url=safe_url(url)
  try:
   req=Request(url,data=urlencode(data).encode() if data is not None else None,headers={'User-Agent':'AuroraPandanetStudio/0.3','Accept-Language':'en'})
   with self.opener.open(req,timeout=20) as response:
    safe_url(response.url);raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ArchiveError('Resposta do Pandanet muito grande.')
    charset=response.headers.get_content_charset() or ('utf-8' if 'sns.' in response.url else 'cp932')
    return raw.decode(charset,errors='replace'),response.url
  except ArchiveError:raise
  except Exception:raise ArchiveError('Não foi possível consultar o site Pandanet. Tente novamente.') from None
 def login(self,username=None,password=None):
  with self.lock:
   if username is None:
    credentials=self.credentials()
    if not credentials:raise ArchiveError('Entre no arquivo Pandanet com sua conta para consultar o site.')
    username,password=credentials
   username=account_name(username)
   if not password:raise ArchiveError('Informe a senha da conta Pandanet.')
   self.reset()
   raw,url=self.request('https://my.pandanet.co.jp/cgi-bin/cgi.exe?MH',{'UserID':username,'Password':password});password=None
   for _ in range(4):
    tree=Tree(raw).root
    archive=next((a.attrs.get('href','') for a in tree.find('a') if a.text()=='Search match results and game records' and 'pg=SearchResult' in a.attrs.get('href','')),None)
    if archive:
     self.user=username;self.home=url;self.archive_url=safe_url(archive,url);return dict(connected=True,account=username)
    target=next((m.attrs.get('content','').split('=',1)[-1].strip(" '\"") for m in tree.find('meta') if m.attrs.get('http-equiv','').lower()=='refresh'),None)
    if not target:
     m=re.search(r'(?:location.href|location.replace)\s*(?:=|\()\s*[\"\']([^\"\']+)',raw);target=m.group(1) if m else None
    if not target:break
    raw,url=self.request(safe_url(target,url))
   self.reset();raise ArchiveError('Login no arquivo recusado. Confira usuário e senha.')
 def logout(self):
  with self.lock:
   if self.user:
    try:self.request('https://sns.pandanet.co.jp/logout.php')
    except ArchiveError:pass
   self.reset();return dict(connected=False)
 def ensure(self):
  if not self.user:self.login()
 def profile(self,account,force=False):
  account=account_name(account)
  with self.lock:
   self.ensure();key=account.lower();cached=self.profile_cache.get(key)
   if cached and not force and time.monotonic()-cached[0]<900:return dict(cached[1])
   own=key==self.user.lower();url='https://sns.pandanet.co.jp/'+('prof_show.php' if own else 'myfriend.php?'+urlencode({'id':account}))
   raw,base=self.request(url);profile=parse_public_profile(raw,base,own)
   # Archive links are observed, never reconstructed from opaque account hashes.
   archive=next((safe_url(a.attrs['href'],base) for a in Tree(raw).root.find('a') if 'pg=SearchResult' in a.attrs.get('href','') and parse_qs(urlparse(a.attrs['href']).query).get('MyName',[''])[0].lower()==key),None)
   if archive:self.archive_targets[key]=archive
   profile.update(account=account,source_url='https://sns.pandanet.co.jp/myfriend.php?'+urlencode({'id':account}))
   self.profile_cache[key]=(time.monotonic(),profile);return dict(profile)
 def search(self,query):
  query=str(query).strip()
  if not query or len(query)>80:raise ArchiveError('Informe um nome de usuário válido.')
  with self.lock:
   self.ensure();raw,base=self.request('https://sns.pandanet.co.jp/prof_findlist.php?'+urlencode({'id':query,'fuzzy':'on','country1':'','country2':'','country3':'','class_from':'','class_to':''}))
   results={}
   for a in Tree(raw).root.find('a'):
    href=a.attrs.get('href','');q=parse_qs(urlparse(urljoin(base,href)).query)
    if 'myfriend.php' in href and q.get('id') and q['id'][0]!='admin':
     account=q['id'][0]
     try:account_name(account)
     except ArchiveError:continue
     results[account.lower()]=dict(account=account,name=account,photo='')
   # The site excludes the currently logged-in account from member search.
   if query.lower() in self.user.lower():results[self.user.lower()]=dict(account=self.user,name=self.user,photo='')
   return list(results.values())[:40]
 def games(self,account,page=1,force=False):
  account=account_name(account);page=int(page)
  if not 1<=page<=1000:raise ArchiveError('Página inválida.')
  with self.lock:
   self.ensure();key=(account.lower(),page);cached=self.cache.get(key)
   if cached and not force and time.monotonic()-cached[0]<120:return cached[1]
   if account.lower()==self.user.lower():url=self.archive_url
   else:
    self.profile(account);url=self.archive_targets.get(account.lower())
    if not url:raise ArchiveError('O site não disponibilizou um arquivo público para esse jogador.')
   if page>1:
    if key[0] not in self.page_forms:self.games(account,1)
    form=dict(self.page_forms[key[0]]);form.update(pg='SearchResult',PageNo=str(page));raw,base=self.request('https://my.pandanet.co.jp/cgi-bin/cgi.exe?MH',form)
   else:raw,base=self.request(url)
   records,pages,form=parse_archive(raw,base)
   if not records and 'Login' in Tree(raw).root.text():self.reset();raise ArchiveError('A sessão do arquivo expirou. Entre novamente.')
   self.page_forms[key[0]]=form
   public=[]
   for game in records:
    if account.lower() not in (game['white']['account'].lower(),game['black']['account'].lower()):continue
    token=secrets.token_urlsafe(18);self.handles[token]=(game['_url'],account)
    public.append({**{k:v for k,v in game.items() if not k.startswith('_')},'handle':token})
   if len(self.handles)>3000:
    self.handles={t:self.handles[t] for t in [g['handle'] for g in public]};self.cache.clear()
   result=dict(account=account,games=public,page=page,pages=max(page,pages),connected=True);self.cache[key]=(time.monotonic(),result);return result
 def sgf(self,handle):
  with self.lock:
   if handle not in self.handles:raise ArchiveError('Partida expirada. Atualize a lista e tente novamente.')
   url,account=self.handles[handle];raw,_=self.request(url)
   from sgf import read_sgf
   game=read_sgf(raw)
   if account.lower() not in (game['white'].lower(),game['black'].lower()):raise ArchiveError('O registro recebido pertence a outro jogador.')
   return game
