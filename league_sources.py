"""Read-only import of published Pandanet league rosters; no network on render."""
import re,time,json
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,unquote
from urllib.request import Request,urlopen
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor,as_completed
BASE='https://pandanet-igs.com'
LEAGUES=[
 dict(id='latinamericanleague',name='PGLATC · Latin America',national=True,room_names=['LatinAmericanTeamChamp']),
 dict(id='euroteamchamps',name='PGETC · Europe',national=True,room_names=['EuropeanTeamChamp','EuroTeamChamps']),
 dict(id='PYGETC',name='PYGETC · European Youth',national=True,room_names=['EuropeanTeamChamp','EuroTeamChamps']),
 dict(id='agacityleague',name='AGA City League',national=False,room_names=['AGA City League','AGA City League(Manual)']),
]
def leagues_for_room(name):
 """A room can host several competitions; aliases name the same server room."""
 key=' '.join(str(name).split()).casefold()
 return [league for league in LEAGUES if any(' '.join(room.split()).casefold()==key for room in league['room_names'])]

COUNTRIES={'Uruguay':'Uruguai','Brazil':'Brasil','Mexico':'México','Dominican':'República Dominicana','Dominican Republic':'República Dominicana','Colombia':'Colômbia','Ecuador':'Equador','Haiti':'Haiti','Panama':'Panamá','El Salvador':'El Salvador','Austria':'Áustria','Belgium':'Bélgica','Croatia':'Croácia','Cyprus':'Chipre','Czechia':'Chéquia','Denmark':'Dinamarca','Finland':'Finlândia','France':'França','Georgia':'Geórgia','Germany':'Alemanha','Greece':'Grécia','Hungary':'Hungria','Iceland':'Islândia','Ireland':'Irlanda','Italy':'Itália','Kazakhstan':'Cazaquistão','Kyrgyzstan':'Quirguistão','Lithuania':'Lituânia','Morocco':'Marrocos','Netherlands':'Países Baixos','Norway':'Noruega','Poland':'Polônia','Portugal':'Portugal','Romania':'Romênia','Serbia':'Sérvia','Slovakia':'Eslováquia','Slovenia':'Eslovênia','South Africa':'África do Sul','Spain':'Espanha','Sweden':'Suécia','Switzerland':'Suíça','Turkey':'Turquia','Ukraine':'Ucrânia','United Kingdom':'Reino Unido','UK':'Reino Unido','Bulgaria':'Bulgária'}
class Node:
 def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
 def text(self):return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split())
 def find(self,tag=None,cls=None,id=None):
  result=[]
  for c in self.children:
   if not isinstance(c,Node):continue
   if (not tag or c.tag==tag) and (not cls or cls in c.attrs.get('class','').split()) and (not id or c.attrs.get('id')==id):result.append(c)
   result.extend(c.find(tag,cls,id))
  return result
class Tree(HTMLParser):
 def __init__(self,raw):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root];self.feed(raw)
 def handle_starttag(self,tag,attrs):
  node=Node(tag,attrs);self.stack[-1].children.append(node)
  if tag not in ('img','br','hr','meta','link','input','source','wbr','area','base','embed','param','col'):self.stack.append(node)
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):self.stack[-1].children.append(data)
def fetch(url):
 if urlparse(url).scheme!='https' or urlparse(url).hostname!='pandanet-igs.com':raise ValueError('Origem de liga inválida.')
 for attempt in range(2):
  try:
   with urlopen(Request(url,headers={'User-Agent':'AuroraPandanetStudio/0.2 (public roster reader)'}),timeout=25) as response:
    if urlparse(response.url).hostname!='pandanet-igs.com':raise ValueError('Redirecionamento fora do Pandanet.')
    raw=response.read(4_000_001)
    if len(raw)>4_000_000:raise ValueError('Página excede o limite de importação.')
    return raw.decode('utf-8'),response.url
  except OSError:
   if attempt:raise
   time.sleep(.5)
def discover(raw,league):
 tree=Tree(raw).root
 titles=tree.find(cls='current-season-right-panel-title')
 if not titles:raise ValueError('Temporada atual não identificada na página oficial.')
 season_name=titles[0].text();links=tree.find('a');pattern=r'^/communities/'+re.escape(league['id'])+r'/teams/(\d+)/[^/]+$'
 ids=[re.match(pattern,a.attrs.get('href','')) for a in links];ids=[m.group(1) for m in ids if m]
 if not ids:raise ValueError('Não foi possível identificar a temporada das equipes.')
 season=max(set(ids),key=ids.count)
 return season,season_name
def team_links(raw,league,season):
 pattern=r'^/communities/'+re.escape(league['id'])+r'/teams/'+re.escape(str(season))+r'/([^/]+)$';result={}
 for a in Tree(raw).root.find('a'):
  path=a.attrs.get('href','');m=re.match(pattern,path)
  if m:result[urljoin(BASE,path)]=dict(code=unquote(m.group(1)),name=a.text(),url=urljoin(BASE,path))
 return list(result.values())
def parse_team(raw,team,league):
 tree=Tree(raw).root;main=tree.find(id='container-main-content');scope=main[0] if main else tree
 headings=scope.find('h1');name=headings[0].text() if headings else team['name'];players=[];warnings=[]
 for block in scope.find(cls='player_profile'):
  headers=block.find('h4')
  if not headers:continue
  title=headers[0].text();anchor=headers[0].find('a');source_id=anchor[0].attrs.get('name','') if anchor else ''
  order=re.match(r'^(\d+):\s*',title);person_name=re.sub(r'^\d+:\s*','',title);person_name=re.sub(r'\s*\((Captain|Trainer|Coach)\)\s*',' ',person_name,flags=re.I).strip()
  values={}
  for li in block.find('li'):
   text=li.text();label,separator,value=text.partition(':')
   if separator:values[label.strip().lower()]=value.strip()
  account=values.get('pandanet account','').strip();accounts=[]
  # Do not invent aliases by splitting free text; ambiguous accounts remain visible for review.
  if re.fullmatch(r'[A-Za-z0-9_-]{1,50}',account):accounts=[account]
  elif account:warnings.append('Conta não reconhecida: '+person_name+' ('+account+')')
  photos=block.find('img');photo=urljoin(BASE,photos[0].attrs.get('src','')) if photos else ''
  if photo and urlparse(photo).scheme!='https':photo=''
  if not person_name:continue
  players.append(dict(source_id=source_id,name=person_name,accounts=accounts,account_raw=account,rank=values.get('rank',''),photo=photo,captain=bool(re.search(r'\bCaptain\b',title,re.I)),trainer=bool(re.search(r'\b(?:Trainer|Coach)\b',title,re.I)),order=int(order.group(1)) if order else 0,source_url=team['url']+('#'+source_id if source_id else '')))
 if not players:
  if not headings or name.casefold()!=team['name'].casefold():raise ValueError('Página de equipe não reconhecida: '+team['name'])
  warnings.append(name+': nenhum jogador publicado pela fonte.')
 return dict(**team,country=COUNTRIES.get(name,name) if league['national'] else '',players=players,warnings=warnings)
def import_league(league,progress=lambda text:None):
 home=BASE+'/communities/'+league['id'];progress('Identificando a temporada de '+league['name']+'…');raw,_=fetch(home);season,name=discover(raw,league)
 url=home+'/teams/'+season;index,_=fetch(url);teams=team_links(index,league,season)
 if not teams:raise ValueError('Lista de equipes vazia; cadastro anterior preservado.')
 results=[];errors=[]
 def load(team):raw,_=fetch(team['url']);return parse_team(raw,team,league)
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(load,t):t for t in teams}
  for future in as_completed(futures):
   try:results.append(future.result())
   except Exception as error:errors.append(futures[future]['name']+': '+str(error))
   progress(f"{league['name']}: {len(results)+len(errors)} de {len(teams)} equipes")
 # Never publish a partially replaced roster.
 if errors:raise ValueError('Importação incompleta; cadastro anterior preservado. '+'; '.join(errors)[:1200])
 return dict(league_id=league['id'],season_id=season,season_name=name,source_url=url,imported_at=datetime.now(timezone.utc).isoformat(),teams=sorted(results,key=lambda t:t['name']),warnings=[w for t in results for w in t['warnings']])
if __name__=='__main__':
 from pathlib import Path
 import sys
 out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
 for league in LEAGUES:
  try:
   result=import_league(league,lambda message:print(message,flush=True));(out/(league['id']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print('Concluído:',league['name'],len(result['teams']),sum(len(t['players']) for t in result['teams']),flush=True)
  except Exception as error:print('ERRO:',league['id'],error,flush=True)

def seasons_for_year(league,year):
 """Only observed season links whose label covers the requested calendar year."""
 raw,_=fetch(BASE+'/communities/'+league['id']+'/seasons');result=[]
 for a in Tree(raw).root.find('a'):
  href=a.attrs.get('href','');label=a.text();years=[int(y) for y in re.findall(r'\b(?:19|20)\d{2}\b',label)]
  if href.startswith('/communities/'+league['id']+'/seasons/') and year in years:
   page,_=fetch(urljoin(BASE,href));ids=[]
   main=Tree(page).root.find(id='container-main-content')
   if not main:raise ValueError('Página histórica sem conteúdo reconhecido.')
   pattern=r'^/communities/'+re.escape(league['id'])+r'/teams/(\d+)/'
   for link in main[0].find('a'):
    m=re.match(pattern,link.attrs.get('href',''))
    if m:ids.append(m.group(1))
   if len(set(ids))>1:raise ValueError('Temporada histórica ambígua; cadastro anterior preservado.')
   if ids:result.append((ids[0],label))
 return list(dict.fromkeys(result))

def import_season(league,season,name):
 url=BASE+'/communities/'+league['id']+'/teams/'+str(season);raw,_=fetch(url);teams=team_links(raw,league,season)
 if not teams:raise ValueError('Temporada sem equipes publicadas.')
 def load(team):raw,_=fetch(team['url']);return parse_team(raw,team,league)
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(load,teams))
 return dict(league_id=league['id'],season_id=str(season),season_name=name,source_url=url,imported_at=datetime.now(timezone.utc).isoformat(),teams=results,warnings=[w for t in results for w in t['warnings']])
