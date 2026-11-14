import datetime as dt,unittest
from unittest.mock import patch
import comparison_response as c

E1={'product_id':'14535','product':'20kg Ideal Adult Dog Food','retailer':'Animals First','price':'540.00','url':'https://animalsfirst.co.za/product/a/','checked_sast':'2026-11-14T13:32:00+02:00'}
E2={'product_id':'30273','product':'IDEAL ADULT DOG FOOD 20KG','retailer':'Turf Pet Hyper','price':'450.00','url':'https://turfhyper.co.za/product/a/','checked_sast':'2026-11-14T13:32:01+02:00'}
class Tests(unittest.TestCase):
 def test_request_matches_exact_pair_only(self):
  pairs=[(14535,E1['product'],30273,E2['product'])]
  self.assertEqual(c.match_request('Please compare 20kg Ideal Adult Dog Food at Animals First and Turf Hyper?',pairs),'14535-30273')
  for q in ['Compare 20kg Ideal Adult Dog Food at Animals First and Pick n Pay?', 'Compare Ideal Dog Food at Animals First and Turf Hyper?', 'Compare 20kg Ideal Adult Dog Food at Animals First and Turf Hyper including delivery?']:
   self.assertIsNone(c.match_request(q,pairs))
 def test_verified_comparison_has_scope_and_dates(self):
  with patch.object(c,'product_research',side_effect=[E1,E2]):e=c.research('14535-30273')
  item=c.build(e)
  self.assertIn('R540.00',item['script']);self.assertIn('R450.00',item['script'])
  self.assertIn('two stores before delivery',item['script']);self.assertIn('13:32 SAST',item['caption'])
 def test_different_product_is_rejected(self):
  with patch.object(c,'product_research',side_effect=[E1,dict(E2,product='IDEAL PUPPY DOG FOOD 20KG')]):
   with self.assertRaises(ValueError):c.research('14535-30273')
if __name__=='__main__':unittest.main()
