import unittest
from board import play,reconstruct,handicap_points,IllegalMove

class BoardTests(unittest.TestCase):
    def test_capture(self):
        board={(1,1):'W',(0,1):'B',(1,0):'B',(2,1):'B'}
        result=play(board,'B','B1',3)
        self.assertNotIn((1,1),result);self.assertIn((1,1),board)
    def test_suicide(self):
        board={(0,1):'B',(1,0):'B',(2,1):'B',(1,2):'B'}
        with self.assertRaises(IllegalMove):play(board,'W','B2',3)
    def test_pass_and_variation_do_not_change_source(self):
        moves=[dict(color='B',point='D4'),dict(color='W',point='Pass'),dict(color='B',point='Q16')]
        full=reconstruct(moves)
        analysis=reconstruct(moves,ply=1,variation=[dict(color='W',point='Q4')])
        self.assertEqual(len(full['stones']),2);self.assertEqual(len(analysis['stones']),2)
        self.assertIn([15,15,'W'],analysis['stones']);self.assertNotIn([15,15,'W'],full['stones'])
        self.assertEqual(len(moves),3)
    def test_handicap(self):
        for n in range(2,10):self.assertEqual(len(set(handicap_points(n,19))),n)
        result=reconstruct([dict(color='B',point='Handicap',extra=['2']),dict(color='W',point='Q4')],handicap=2)
        self.assertEqual(len(result['stones']),3)
    def test_ko(self):
        previous={(0,0):'B'}
        with self.assertRaises(IllegalMove):play({},'B','A3',3,previous)
    def test_reconstruct_recorded_games(self):
        import json
        from pathlib import Path
        games=json.loads(Path(__file__).with_name('demo.json').read_text())
        self.assertEqual(len(games),4)
        for g in games:
            for ply in [0,1,len(g['moves'])//2,len(g['moves'])]:
                result=reconstruct(g['moves'],g['size'],ply=ply,handicap=g.get('handicap',0))
                self.assertTrue(all(0<=s[0]<g['size'] for s in result['stones']))

if __name__=='__main__':unittest.main()
