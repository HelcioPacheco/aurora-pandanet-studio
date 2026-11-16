"""Explicit country aliases. Unknown values never receive an inferred flag."""
import unicodedata
ROWS='''AR|Argentina
AT|Austria|Áustria
AU|Australia|Austrália
BE|Belgium|Bélgica
BG|Bulgaria|Bulgária
BR|Brazil|Brasil
CA|Canada|Canadá
CH|Switzerland|Suíça
CL|Chile
CN|China
CO|Colombia|Colômbia
CR|Costa Rica
CY|Cyprus|Chipre
CZ|Czechia|Czech Republic|Chéquia
DE|Germany|Alemanha
DK|Denmark|Dinamarca
DO|Dominican|Dominican Republic|República Dominicana
EC|Ecuador|Equador
EE|Estonia|Estônia
ES|Spain|Espanha
FI|Finland|Finlândia
FR|France|França
GB|UK|United Kingdom|Reino Unido
GE|Georgia|Geórgia
GR|Greece|Grécia
GT|Guatemala
HR|Croatia|Croácia
HT|Haiti
HU|Hungary|Hungria
ID|Indonesia|Indonésia
IE|Ireland|Irlanda
IL|Israel
IS|Iceland|Islândia
IT|Italy|Itália
JP|Japan|Japão
KG|Kyrgyzstan|Quirguistão
KR|Korea|South Korea|Coreia do Sul
KZ|Kazakhstan|Cazaquistão
LT|Lithuania|Lituânia
LU|Luxembourg|Luxemburgo
LV|Latvia|Letônia
MA|Morocco|Marrocos
MX|Mexico|México
MY|Malaysia|Malásia
NL|Netherlands|Países Baixos
NO|Norway|Noruega
NZ|New Zealand|Nova Zelândia
PA|Panama|Panamá
PE|Peru
PH|Philippines|Filipinas
PL|Poland|Polônia
PT|Portugal
RO|Romania|Romênia
RS|Serbia|Sérvia
RU|Russia|Rússia
SE|Sweden|Suécia
SG|Singapore|Singapura
SI|Slovenia|Eslovênia
SK|Slovakia|Eslováquia
SV|El Salvador
TH|Thailand|Tailândia
TR|Turkey|Türkiye|Turquia
TW|C.Taipei|Chinese Taipei|Taiwan
UA|Ukraine|Ucrânia
US|USA|United States|Estados Unidos
UY|Uruguay|Uruguai
VE|Venezuela
VN|Viet Nam|Vietnam|Vietnã
ZA|South Africa|África do Sul'''
def normalized(value):return ''.join(c for c in unicodedata.normalize('NFKD',str(value)) if not unicodedata.combining(c)).casefold().strip()
ALIASES={normalized(alias):row.split('|')[0] for row in ROWS.splitlines() for alias in row.split('|')}
def country_code(value):return ALIASES.get(normalized(value),'')
