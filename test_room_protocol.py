import unittest
from app import ObservationSession

class RoomProtocolTests(unittest.TestCase):
 def session(self,reply,current=51):
  ticks=[0];s=ObservationSession(clock=lambda:ticks[0]);s.room_id=current;s.status='connected';s.sent=[]
  s.send=lambda command:s.sent.append(command)
  pending=[reply]
  def receive(timeout):
   ticks[0]+=1
   text=pending.pop(0) if pending else ''
   for line in text.splitlines():s.parse(line)
   return text
  s.receive=receive
  return s
 def test_real_pandanet_leaving_confirmation_sets_main_room(self):
  s=self.session('9 You are leaving game room #51\r\n1 5\r\n');s.games={7:dict(id=7)}
  s.join(0);self.assertEqual(s.room_id,0);self.assertEqual(s.games,{});self.assertEqual(s.sent,['join 0']);self.assertFalse(s._busy)
 def test_other_players_leaving_does_not_confirm_our_room_change(self):
  s=self.session('9 otherPlayer left this room\r\n1 5\r\n')
  with self.assertRaises(TimeoutError):s.join(0)
  self.assertEqual(s.room_id,51)
 def test_numbered_entry_must_match_requested_room(self):
  s=self.session('9 Welcome to the game room #99\r\n1 5\r\n')
  s.join(99);self.assertEqual(s.room_id,99)

 def test_already_in_main_room_is_idempotent(self):
  s=self.session('1 5\r\n',current=0);s.games={70:dict(id=70)}
  s.join(0);self.assertEqual(s.room_id,0);self.assertEqual(s.games,{70:dict(id=70)});self.assertEqual(s.sent,[])
 def test_command_matching_does_not_parse_toggle_target_as_room_number(self):
  s=self.session('9 Set client to True\r\n1 5\r\n')
  self.assertIn('Set client',s.command('toggle client true'));self.assertEqual(s.sent,['toggle client true'])
 def test_a_different_room_number_does_not_confirm_entry(self):
  s=self.session('9 Welcome to the game room #990\r\n1 5\r\n')
  with self.assertRaises(TimeoutError):s.join(99)
  self.assertEqual(s.room_id,51)
