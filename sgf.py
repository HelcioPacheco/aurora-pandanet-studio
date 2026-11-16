"""Bounded SGF reader. Keeps the first game/main variation; never executes content."""
import re,math
from board import LETTERS,reconstruct

def read_sgf(raw):
 if isinstance(raw,bytes):raw=raw.decode('utf-8-sig',errors='replace')
 if len(raw)>2_000_000:raise ValueError('SGF muito grande.')
 i=0
 def spaces():
  nonlocal i
  while i<len(raw) and raw[i].isspace():i+=1
 def value():
  nonlocal i
  if i>=len(raw) or raw[i]!='[':raise ValueError('SGF inválido.')
  i+=1;out=[]
  while i<len(raw):
   c=raw[i];i+=1
   if c==']':return ''.join(out)
   if c=='\\':
    if i>=len(raw):break
    c=raw[i];i+=1
    if c=='\r':
     if i<len(raw) and raw[i]=='\n':i+=1
     continue
    if c=='\n':continue
   out.append(c)
  raise ValueError('SGF incompleto.')
 def tree(depth=0):
  nonlocal i
  if depth>100:raise ValueError('SGF com muitas variantes.')
  spaces()
  if i>=len(raw) or raw[i]!='(':raise ValueError('SGF inválido.')
  i+=1;nodes=[];spaces()
  while i<len(raw) and raw[i]==';':
   i+=1;props={};spaces()
   while i<len(raw) and raw[i].isalpha():
    start=i
    while i<len(raw) and raw[i].isalpha():i+=1
    key=raw[start:i].upper();spaces();values=[]
    while i<len(raw) and raw[i]=='[':values.append(value());spaces()
    if not values:raise ValueError('Propriedade SGF inválida.')
    props.setdefault(key,[]).extend(values)
   nodes.append(props)
   if len(nodes)>5000:raise ValueError('SGF com muitos lances.')
  first=True
  while i<len(raw) and raw[i]=='(':
   child=tree(depth+1)
   if first:nodes.extend(child);first=False
   spaces()
  if i>=len(raw) or raw[i]!=')':raise ValueError('SGF incompleto.')
  i+=1;return nodes
 nodes=tree()
 if not nodes:raise ValueError('SGF vazio.')
 root=nodes[0];one=lambda key,default='':root.get(key,[default])[0]
 if one('GM','1')!='1':raise ValueError('Este arquivo não é uma partida de Go.')
 try:size=int(one('SZ','19'));handicap=int(one('HA','0'))
 except ValueError:raise ValueError('Tamanho de tabuleiro inválido.')
 if not 2<=size<=25:raise ValueError('Tamanho de tabuleiro não suportado.')
 def point(text):
  if not text or text=='tt' and size<=19:return 'PASS'
  if not re.fullmatch('[a-y]{2}',text):raise ValueError('Coordenada SGF inválida.')
  x,y=map(lambda c:ord(c)-97,text)
  if x>=size or y>=size:raise ValueError('Coordenada SGF fora do tabuleiro.')
  return LETTERS[x]+str(size-y)
 setup=[]
 for prop,c in [('AB','B'),('AW','W')]:
  for p in root.get(prop,[]):
   q=point(p)
   if q=='PASS':raise ValueError('Posição inicial inválida.')
   setup.append([ord(p[0])-97,ord(p[1])-97,c])
 moves=[]
 for n,node in enumerate(nodes):
  if n and any(k in node for k in ('AB','AW','AE')):raise ValueError('SGF com edição de posição durante a partida não suportado.')
  if 'B' in node and 'W' in node:raise ValueError('Lance SGF ambíguo.')
  for c in ('B','W'):
   if c in node:moves.append(dict(color=c,point=point(node[c][0]),number=len(moves)+1))
 try:komi=float(one('KM')) if one('KM') else None
 except ValueError:raise ValueError('Komi SGF inválido.')
 if komi is not None and not math.isfinite(komi):raise ValueError('Komi SGF inválido.')
 game=dict(komi=komi,rules=one('RU'),white=one('PW'),black=one('PB'),white_rank=one('WR'),black_rank=one('BR'),date=one('DT'),size=size,handicap=handicap,moves=moves,result=one('RE'),setup=setup,next_color=one('PL') or ('W' if handicap>=2 else 'B'),status='recorded',clocks={},recorded=True)
 if not game['white'] or not game['black']:raise ValueError('SGF sem identificação dos jogadores.')
 game['board']=reconstruct(moves,size,handicap=handicap,setup=setup or None,next_color=game['next_color'])
 return game
