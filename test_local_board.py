"""Cross-check the browser engine against the existing Python engine."""
import json,subprocess,unittest,shutil
from pathlib import Path
from board import reconstruct
ROOT=Path(__file__).parent
class LocalBoardTests(unittest.TestCase):
 def test_all_recorded_positions_and_variations(self):
  node=shutil.which('node') or str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
  games=json.loads((ROOT/'demo.json').read_text());cases=[]
  for g in games:
   for ply in range(len(g['moves'])+1):cases.append(dict(g=g,ply=ply,variation=[]))
   cases.append(dict(g=g,ply=0,variation=[dict(color='B',point='D4'),dict(color='W',point='Pass')]))
  for h in range(2,10):cases.append(dict(g=dict(id=900+h,size=19,handicap=h,moves=[dict(color='B',point='Handicap',extra=[str(h)]),dict(color='W',point='Pass')]),ply=2,variation=[]))
  cases.append(dict(g=dict(id=9901,size=9,handicap=2,setup=[[1,1,'B'],[6,7,'B']],next_color='W',moves=[dict(color='W',point='D4')]),ply=1,variation=[]))
  cases.append(dict(g=dict(id=9902,size=9,setup=[[1,1,'W']],next_color='B',moves=[dict(color='B',point='D4')]),ply=0,variation=[]))
  js="const engine=require(process.argv[1]);let input='';process.stdin.on('data',s=>input+=s);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(input).map(c=>engine.reconstruct(c.g,c.ply,c.variation)))));"
  result=subprocess.run([node,'-e',js,str((ROOT/'static/local-board.js').resolve())],input=json.dumps(cases),text=True,capture_output=True,check=True)
  actual=json.loads(result.stdout)
  for c,a in zip(cases,actual):
   g=c['g'];expected=reconstruct(g['moves'],g['size'],c['ply'],c['variation'],g.get('handicap',0),setup=g.get('setup'),next_color=g.get('next_color'));a['stones'].sort();expected['stones'].sort();self.assertEqual(a,expected)
  self.assertEqual(len(actual),len(cases))
